"""
T-021 — Tests for partial ARM/SOLD completion bug fix.

Bug: `_determine_action()` compares `selected_count` against `total_available`
(post-filtered unions "workable now"), not against `Total_Uniones` of the spool.
When an operator finishes the available batch, action becomes COMPLETAR even
though unions remain pending in the spool.

Fix: `_determine_action` must contrast against the spool's total uniones and
count unions already completed in prior sessions.

These tests must FAIL before the fix and PASS after.

Reference:
- Plan: .planning/fixes/T-021-PLAN.md (Wave 1, Plan 1.1)
- Service: backend/services/occupation_service.py:815-856
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.services.occupation_service import OccupationService
from backend.models.occupation import FinalizarRequest
from backend.models.spool import Spool
from backend.models.union import Union
from backend.models.enums import ActionType
from backend.exceptions import RaceConditionError


# ============================================================================
# Fixtures (minimal — focused on partial-completion scenarios)
# ============================================================================

@pytest.fixture
def mock_sheets_repository():
    repo = MagicMock()

    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "OT-999"
    mock_spool.ot = "999"
    mock_spool.total_uniones = 7
    mock_spool.uniones_arm_completadas = 0
    mock_spool.uniones_sold_completadas = 0
    mock_spool.fecha_materiales = "2026-01-20"
    mock_spool.fecha_ocupacion = "04-02-2026 10:00:00"
    mock_spool.ocupado_por = "MR(93)"
    mock_spool.armador = None
    mock_spool.soldador = None
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None

    repo.get_spool_by_tag = MagicMock(return_value=mock_spool)
    repo.batch_update_by_column_name = MagicMock()
    repo._index_to_column_letter = MagicMock(return_value="G")
    repo.find_row_by_column_value = MagicMock(return_value=5)
    repo.read_worksheet = MagicMock(return_value=[[
        "TAG_SPOOL", "OT", "NV", "Fecha_Materiales", "Fecha_Armado", "Armador",
        "Fecha_Soldadura", "Soldador", "Ocupado_Por", "Fecha_Ocupacion",
        "Estado_Detalle", "Total_Uniones", "Uniones_ARM_Completadas",
        "Pulgadas_ARM", "Uniones_SOLD_Completadas", "Pulgadas_SOLD"
    ]])
    return repo


@pytest.fixture
def mock_metadata_repository():
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_conflict_service():
    service = MagicMock()
    service.generate_version_token = MagicMock(return_value="version-uuid")
    service.update_with_retry = AsyncMock(return_value="new-version-uuid")
    return service


def _make_union(n, arm_done=False, sold_done=False, tipo="BW"):
    return Union(
        id=f"OT-999+{n}",
        ot="999",
        tag_spool="OT-999",
        n_union=n,
        dn_union=2.0,
        tipo_union=tipo,
        arm_fecha_inicio=None,
        arm_fecha_fin=datetime(2026, 4, 10) if arm_done else None,
        arm_worker="NR(94)" if arm_done else None,
        sol_fecha_inicio=None,
        sol_fecha_fin=datetime(2026, 4, 10) if sold_done else None,
        sol_worker="FF(129)" if sold_done else None,
        ndt_fecha=None,
        ndt_status=None,
        version="v1",
    )


@pytest.fixture
def mock_union_repository():
    repo = MagicMock()
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[])
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=[])
    repo.get_by_ot = MagicMock(return_value=[])
    repo.get_by_spool = MagicMock(return_value=[])
    repo.batch_update_arm = MagicMock(return_value=0)
    repo.batch_update_sold = MagicMock(return_value=0)
    repo.batch_update_arm_full = MagicMock(return_value=0)
    repo.batch_update_sold_full = MagicMock(return_value=0)
    repo.get_by_ids = MagicMock(return_value=[])
    repo.get_total_uniones = MagicMock(return_value=7)
    repo.calculate_metrics = MagicMock(return_value={
        "arm_completadas": 0,
        "sold_completadas": 0,
        "pulgadas_arm": 0.0,
        "pulgadas_sold": 0.0,
    })
    repo._find_spool_row = MagicMock(return_value=5)
    return repo


@pytest.fixture
def service(mock_sheets_repository, mock_metadata_repository,
            mock_conflict_service, mock_union_repository):
    return OccupationService(
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=mock_conflict_service,
        union_repository=mock_union_repository,
    )


# ============================================================================
# Plan 1.1 — _determine_action contrasts against Total_Uniones of the spool
# ============================================================================
#
# After the fix, _determine_action accepts a 4th parameter:
#     total_uniones_spool: int
# and considers already-completed unions.
#
# Calling convention post-fix:
#     _determine_action(selected_count, total_available, operacion,
#                      total_uniones_spool, ya_completadas)
# COMPLETAR iff  ya_completadas + selected_count == total_uniones_spool
# (for SOLD: total_uniones_spool is count of SOLD-required types; see Plan 2.1)


def test_sold_2_of_7_unions_should_pausar_not_completar(service):
    """
    Reproduces production bug: operator completes 2 of 7 unions (all of the
    available batch), which today returns COMPLETAR. Must return PAUSAR.
    """
    result = service._determine_action(
        selected_count=2,
        total_available=2,       # only 2 available "right now" (filtered)
        operacion="SOLD",
        total_uniones_spool=7,   # actual total SOLD-required unions of the spool
        ya_completadas=0,
    )
    assert result == "PAUSAR", (
        "2 of 7 unions soldered must be PAUSAR, not COMPLETAR. "
        "This is the T-021 production bug."
    )


def test_arm_3_of_7_unions_should_pausar_not_completar(service):
    """Analogous bug for ARM."""
    result = service._determine_action(
        selected_count=3,
        total_available=3,
        operacion="ARM",
        total_uniones_spool=7,
        ya_completadas=0,
    )
    assert result == "PAUSAR"


def test_sold_7_of_7_returns_completar(service):
    """Happy path — all unions finalized in one session."""
    result = service._determine_action(
        selected_count=7,
        total_available=7,
        operacion="SOLD",
        total_uniones_spool=7,
        ya_completadas=0,
    )
    assert result == "COMPLETAR"


def test_sold_completes_across_two_sessions(service):
    """
    Session 1: 3 of 7 -> PAUSAR. Session 2: final 4 -> COMPLETAR.
    ya_completadas=3 + selected=4 == total=7 -> COMPLETAR.
    """
    result = service._determine_action(
        selected_count=4,
        total_available=4,
        operacion="SOLD",
        total_uniones_spool=7,
        ya_completadas=3,
    )
    assert result == "COMPLETAR"


def test_arm_partial_across_sessions_still_pausar(service):
    """ya_completadas=2 + selected=3 = 5 < total=7 -> PAUSAR."""
    result = service._determine_action(
        selected_count=3,
        total_available=5,
        operacion="ARM",
        total_uniones_spool=7,
        ya_completadas=2,
    )
    assert result == "PAUSAR"


def test_legacy_spool_total_uniones_zero_falls_back_to_old_rule(service):
    """
    Spool v3.0 legacy (Total_Uniones=0 and no Uniones rows) must keep
    the pre-fix behavior: selected == total_available -> COMPLETAR.
    No regression for legacy spools.
    """
    result = service._determine_action(
        selected_count=5,
        total_available=5,
        operacion="SOLD",
        total_uniones_spool=0,   # legacy indicator
        ya_completadas=0,
    )
    assert result == "COMPLETAR"


def test_race_condition_still_raises(service):
    """Selecting more than available must still raise RaceConditionError."""
    with pytest.raises(RaceConditionError):
        service._determine_action(
            selected_count=15,
            total_available=10,
            operacion="ARM",
            total_uniones_spool=10,
            ya_completadas=0,
        )


def test_completar_guard_rejects_out_of_sync_counters(service):
    """
    Defensive guard: if selected + ya_completadas > total_uniones_spool,
    something is wrong with the data. Must raise (or PAUSAR safely).
    After the fix, the function must refuse to return COMPLETAR in this
    contradictory scenario.
    """
    with pytest.raises(RaceConditionError):
        service._determine_action(
            selected_count=5,
            total_available=5,
            operacion="SOLD",
            total_uniones_spool=7,
            ya_completadas=4,   # 4 already done + 5 selected = 9 > 7 total
        )


# ============================================================================
# T-240 + T-241 — Reconciliation tests (Fecha_Armado/Soldadura backfill)
# ============================================================================
#
# Bug: when a worker pauses or completes a spool whose unions are already
# all ARM-complete (or SOLD-complete), Operaciones.Fecha_{Armado,Soldadura}
# stay empty. PROD evidence on MK-1344-GW-27133-009 (T-240) and
# MK-1344-TW-27121-004 (T-241).
#
# Fix: defense-in-depth helper `_reconcile_completion_columns` reads Uniones
# directly and backfills the v2.1 columns when all relevant unions are done.
# Date and worker come from the union with max(*_FECHA_FIN) for accuracy.
#
# These tests must FAIL before the fix and PASS after.
# Reference: docs/plan T-240+T-241 reconcile Fecha_Armado/Soldadura.

class TestT240T241Reconciliation:
    """Tests for T-240 (ARM) and T-241 (SOLD) reconciliation."""

    def _extract_keyed_updates(self, mock_sheets_repo):
        """Helper: pull last batch_update_by_column_name into a flat dict."""
        call_args = mock_sheets_repo.batch_update_by_column_name.call_args
        if call_args is None:
            return {}
        updates = call_args[1]["updates"] if "updates" in call_args[1] else call_args[0][1]
        return {u["column_name"]: u["value"] for u in updates}

    @pytest.mark.asyncio
    async def test_path_a_pausar_override_with_all_arm_complete_writes_fecha_armado(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        T-240 Path A: action_override=PAUSAR on a spool whose 5 unions are
        already ARM-complete from a prior session must trigger reconcile
        and write Fecha_Armado + Armador. Reproduces MK-1344-GW-27133-009.
        """
        all_complete = [_make_union(i, arm_done=True) for i in range(1, 6)]
        mock_union_repository.get_by_spool = MagicMock(return_value=all_complete)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = None  # the bug

        request = FinalizarRequest(
            tag_spool="OT-999", worker_id=93, worker_nombre="MR(93)",
            operacion="ARM", selected_unions=[], action_override="PAUSAR",
        )
        result = await service.finalizar_spool(request)

        keyed = self._extract_keyed_updates(mock_sheets_repository)
        assert keyed.get("Fecha_Armado") == "10-04-2026"
        assert keyed.get("Armador") == "NR(94)"
        assert result.action_taken == "COMPLETAR"

    @pytest.mark.asyncio
    async def test_path_a_pausar_override_with_partial_arm_does_not_reconcile(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        T-021 invariant regression: action_override=PAUSAR on a genuinely
        partial spool (2 of 5 ARM done) must NOT write Fecha_Armado.
        Action stays PAUSAR.
        """
        partial = [
            _make_union(1, arm_done=True),
            _make_union(2, arm_done=True),
            _make_union(3, arm_done=False),
            _make_union(4, arm_done=False),
            _make_union(5, arm_done=False),
        ]
        mock_union_repository.get_by_spool = MagicMock(return_value=partial)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = None

        request = FinalizarRequest(
            tag_spool="OT-999", worker_id=93, worker_nombre="MR(93)",
            operacion="ARM", selected_unions=[], action_override="PAUSAR",
        )
        result = await service.finalizar_spool(request)

        keyed = self._extract_keyed_updates(mock_sheets_repository)
        assert "Fecha_Armado" not in keyed
        assert "Armador" not in keyed
        assert result.action_taken == "PAUSAR"

    @pytest.mark.asyncio
    async def test_t241_sold_reconciliation_excludes_fw_unions(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        T-241: SOLD reconciliation must use SOLD_REQUIRED_TYPES filter.
        Spool with 3 BW (all SOLD-done) + 2 FW (no SOLD). Fecha_Soldadura
        must be written despite FW.sol_fecha_fin being None.
        """
        unions = [
            _make_union(1, arm_done=True, sold_done=True, tipo="BW"),
            _make_union(2, arm_done=True, sold_done=True, tipo="BW"),
            _make_union(3, arm_done=True, sold_done=True, tipo="BW"),
            _make_union(4, arm_done=True, sold_done=False, tipo="FW"),
            _make_union(5, arm_done=True, sold_done=False, tipo="FW"),
        ]
        mock_union_repository.get_by_spool = MagicMock(return_value=unions)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = "2026-04-09"  # already done
        mock_spool.fecha_soldadura = None       # the bug

        request = FinalizarRequest(
            tag_spool="OT-999", worker_id=129, worker_nombre="FF(129)",
            operacion="SOLD", selected_unions=[], action_override="PAUSAR",
        )
        result = await service.finalizar_spool(request)

        keyed = self._extract_keyed_updates(mock_sheets_repository)
        assert keyed.get("Fecha_Soldadura") == "10-04-2026"
        assert keyed.get("Soldador") == "FF(129)"
        assert result.action_taken == "COMPLETAR"

    @pytest.mark.asyncio
    async def test_reconciliation_idempotent_when_fecha_already_populated(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        Idempotency: spool with Fecha_Armado already set (e.g. populated by
        a prior happy-path COMPLETAR) must NOT have it re-written by
        reconciliation. Preserves the original audit timestamp.
        """
        from datetime import date
        all_complete = [_make_union(i, arm_done=True) for i in range(1, 6)]
        mock_union_repository.get_by_spool = MagicMock(return_value=all_complete)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = date(2026, 3, 15)  # already set, earlier date

        request = FinalizarRequest(
            tag_spool="OT-999", worker_id=93, worker_nombre="MR(93)",
            operacion="ARM", selected_unions=[], action_override="PAUSAR",
        )
        await service.finalizar_spool(request)

        keyed = self._extract_keyed_updates(mock_sheets_repository)
        # Reconciliation no-op: Fecha_Armado not in updates (preserved)
        assert "Fecha_Armado" not in keyed
        assert "Armador" not in keyed

    @pytest.mark.asyncio
    async def test_reconciliation_uses_max_fecha_fin_not_today(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        Date attribution: Fecha_Armado must equal max(ARM_FECHA_FIN), NOT
        today_chile(). Two unions with different finish dates — pick the
        latest. Worker comes from the union tied to that latest date.
        """
        unions = [
            Union(
                id="OT-999+1", ot="999", tag_spool="OT-999", n_union=1,
                dn_union=2.0, tipo_union="BW",
                arm_fecha_inicio=None,
                arm_fecha_fin=datetime(2026, 4, 5),  # earlier
                arm_worker="NR(94)",
                sol_fecha_inicio=None, sol_fecha_fin=None, sol_worker=None,
                ndt_fecha=None, ndt_status=None, version="v1",
            ),
            Union(
                id="OT-999+2", ot="999", tag_spool="OT-999", n_union=2,
                dn_union=2.0, tipo_union="BW",
                arm_fecha_inicio=None,
                arm_fecha_fin=datetime(2026, 4, 12),  # latest — wins
                arm_worker="JP(95)",
                sol_fecha_inicio=None, sol_fecha_fin=None, sol_worker=None,
                ndt_fecha=None, ndt_status=None, version="v1",
            ),
        ]
        mock_union_repository.get_by_spool = MagicMock(return_value=unions)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = None

        request = FinalizarRequest(
            tag_spool="OT-999", worker_id=93, worker_nombre="MR(93)",
            operacion="ARM", selected_unions=[], action_override="PAUSAR",
        )
        await service.finalizar_spool(request)

        keyed = self._extract_keyed_updates(mock_sheets_repository)
        assert keyed.get("Fecha_Armado") == "12-04-2026"  # max, not today
        assert keyed.get("Armador") == "JP(95)"           # worker of latest

    @pytest.mark.asyncio
    async def test_reconciliation_fallback_worker_when_arm_worker_empty(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        Edge case: union has ARM_FECHA_FIN populated but ARM_WORKER is empty
        (legacy/corrupt row). Fall back to the worker who clicked PAUSAR.
        """
        unions = [
            Union(
                id="OT-999+1", ot="999", tag_spool="OT-999", n_union=1,
                dn_union=2.0, tipo_union="BW",
                arm_fecha_inicio=None,
                arm_fecha_fin=datetime(2026, 4, 12),
                arm_worker=None,  # empty — corrupt
                sol_fecha_inicio=None, sol_fecha_fin=None, sol_worker=None,
                ndt_fecha=None, ndt_status=None, version="v1",
            ),
        ]
        mock_union_repository.get_by_spool = MagicMock(return_value=unions)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = None

        request = FinalizarRequest(
            tag_spool="OT-999", worker_id=93, worker_nombre="MR(93)",
            operacion="ARM", selected_unions=[], action_override="PAUSAR",
        )
        await service.finalizar_spool(request)

        keyed = self._extract_keyed_updates(mock_sheets_repository)
        assert keyed.get("Armador") == "MR(93)"  # fallback to clicker

    def test_reconcile_helper_returns_empty_when_union_repo_unavailable(
        self, mock_sheets_repository, mock_metadata_repository, mock_conflict_service
    ):
        """
        Helper is robust to missing union_repository — returns {} and the
        caller (Path A or B) treats it as no-op.
        """
        service_no_unions = OccupationService(
            sheets_repository=mock_sheets_repository,
            metadata_repository=mock_metadata_repository,
            conflict_service=mock_conflict_service,
            union_repository=None,
        )
        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_armado = None

        result = service_no_unions._reconcile_completion_columns(
            spool=mock_spool, operacion="ARM", fallback_worker="MR(93)",
        )
        assert result == {}

    def test_reconcile_helper_returns_empty_for_unknown_operacion(
        self, service, mock_sheets_repository
    ):
        """Unknown operacion (not ARM/SOLD) returns {} silently."""
        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        result = service._reconcile_completion_columns(
            spool=mock_spool, operacion="REPARACION", fallback_worker="MR(93)",
        )
        assert result == {}

    def test_reconcile_helper_returns_empty_for_sold_with_only_fw_unions(
        self, service, mock_sheets_repository, mock_union_repository
    ):
        """
        SOLD reconciliation on a spool whose only unions are FW (no SOLD
        required at all) must return {} — Fecha_Soldadura should NEVER be
        set on such a spool.
        """
        fw_only = [
            _make_union(1, arm_done=True, sold_done=False, tipo="FW"),
            _make_union(2, arm_done=True, sold_done=False, tipo="FW"),
        ]
        mock_union_repository.get_by_spool = MagicMock(return_value=fw_only)

        mock_spool = mock_sheets_repository.get_spool_by_tag.return_value
        mock_spool.fecha_soldadura = None

        result = service._reconcile_completion_columns(
            spool=mock_spool, operacion="SOLD", fallback_worker="FF(129)",
        )
        assert result == {}
