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
