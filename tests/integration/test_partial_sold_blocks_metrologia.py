"""
T-021 — Integration tests: partial SOLD/ARM must NOT leak into METROLOGIA.

Validates:
1. finalizar_spool on a partial SOLD batch does NOT write Fecha_Soldadura.
2. finalizar_spool on a complete SOLD batch DOES write Fecha_Soldadura.
3. SOLDCompletionFilter rejects v4.0 spools with partial counters even when
   Fecha_Soldadura is incorrectly set (the corrupt-production-data scenario).

These tests must FAIL before the Wave 2 fix and PASS after.

Reference:
- Plan: .planning/fixes/T-021-PLAN.md (Wave 1, Plan 1.2)
- Service: backend/services/occupation_service.py (finalizar_spool)
- Filter: backend/services/filters/common_filters.py (SOLDCompletionFilter)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from backend.services.occupation_service import OccupationService
from backend.services.filters.common_filters import SOLDCompletionFilter
from backend.models.occupation import FinalizarRequest
from backend.models.spool import Spool
from backend.models.union import Union
from backend.models.enums import ActionType


# ============================================================================
# Helpers / fixtures
# ============================================================================

def _make_union(n, arm_done=False, sold_done=False, tipo="BW"):
    return Union(
        id=f"OT-777+{n}",
        ot="777",
        tag_spool="SP-777",
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
def partial_spool():
    """
    Spool with 7 unions: 2 are ARM+SOLD done, 5 are untouched.
    Represents the production scenario (MK-1923-TW-17422-004).
    """
    spool = MagicMock(spec=Spool)
    spool.tag_spool = "SP-777"
    spool.ot = "777"
    spool.total_uniones = 7
    spool.uniones_arm_completadas = 2
    spool.uniones_sold_completadas = 0   # before this finalize call
    spool.fecha_materiales = "2026-01-20"
    spool.fecha_ocupacion = "10-04-2026 08:00:00"
    spool.ocupado_por = "FF(129)"
    spool.armador = "NR(94)"
    spool.soldador = None
    spool.fecha_armado = None
    spool.fecha_soldadura = None
    return spool


@pytest.fixture
def mock_sheets(partial_spool):
    repo = MagicMock()
    repo.get_spool_by_tag = MagicMock(return_value=partial_spool)
    repo.batch_update_by_column_name = MagicMock()
    repo._index_to_column_letter = MagicMock(return_value="G")
    repo.find_row_by_column_value = MagicMock(return_value=42)
    repo.read_worksheet = MagicMock(return_value=[[
        "TAG_SPOOL", "OT", "NV", "Fecha_Materiales", "Fecha_Armado", "Armador",
        "Fecha_Soldadura", "Soldador", "Ocupado_Por", "Fecha_Ocupacion",
        "Estado_Detalle", "Total_Uniones", "Uniones_ARM_Completadas",
        "Pulgadas_ARM", "Uniones_SOLD_Completadas", "Pulgadas_SOLD"
    ]])
    # Allow _get_spreadsheet chain to work (skip actual Sheets calls)
    mock_sheet = MagicMock()
    mock_sheet.worksheet = MagicMock(return_value=MagicMock())
    repo._get_spreadsheet = MagicMock(return_value=mock_sheet)
    return repo


@pytest.fixture
def mock_metadata():
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_conflict():
    service = MagicMock()
    service.generate_version_token = MagicMock(return_value="v-token")
    service.update_with_retry = AsyncMock(return_value="v-new")
    return service


@pytest.fixture
def mock_unions_partial_scenario():
    """
    UnionRepository mock matching the partial scenario:
    - 2 unions already ARM+SOLD (ids 1, 2)
    - 5 unions still need ARM then SOLD (ids 3-7)
    get_disponibles_sold_by_ot returns empty (no ARM-complete unions available
    beyond the 2 already soldered). But legacy_sold_mode does NOT kick in
    because fecha_armado is None.
    """
    repo = MagicMock()
    all_unions = [
        _make_union(1, arm_done=True, sold_done=True, tipo="BW"),
        _make_union(2, arm_done=True, sold_done=True, tipo="BW"),
        _make_union(3, tipo="BW"),
        _make_union(4, tipo="BW"),
        _make_union(5, tipo="BW"),
        _make_union(6, tipo="BW"),
        _make_union(7, tipo="BW"),
    ]
    # A new session where operator soldered 2 more (ids 3, 4) — so disponibles
    # for SOLD at finalize time: 2 unions (3, 4) are ARM complete; total is 7.
    soldering_now = [_make_union(3, arm_done=True, tipo="BW"),
                     _make_union(4, arm_done=True, tipo="BW")]
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[
        _make_union(5, tipo="BW"), _make_union(6, tipo="BW"), _make_union(7, tipo="BW")
    ])
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=soldering_now)
    repo.get_by_ot = MagicMock(return_value=all_unions)
    repo.get_by_spool = MagicMock(return_value=all_unions)
    repo.get_by_ids = MagicMock(return_value=soldering_now)
    repo.batch_update_sold_full = MagicMock(return_value=2)
    repo.batch_update_arm_full = MagicMock(return_value=0)
    repo.get_total_uniones = MagicMock(return_value=7)
    # After the finalize, counters would be: arm=4 (2 + 2 new-arm-done), sold=2
    repo.calculate_metrics = MagicMock(return_value={
        "arm_completadas": 4,
        "sold_completadas": 2,
        "pulgadas_arm": 8.0,
        "pulgadas_sold": 4.0,
    })
    repo._find_spool_row = MagicMock(return_value=42)
    return repo


@pytest.fixture
def service(mock_sheets, mock_metadata, mock_conflict, mock_unions_partial_scenario):
    return OccupationService(
        sheets_repository=mock_sheets,
        metadata_repository=mock_metadata,
        conflict_service=mock_conflict,
        union_repository=mock_unions_partial_scenario,
    )


# ============================================================================
# Plan 1.2 — finalize_spool does not write Fecha_Soldadura on partial work
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_sold_partial_does_not_write_fecha_soldadura(
    service, mock_sheets
):
    """
    Operator completes 2 new SOLD unions on a 7-union spool (existing 0 sold
    before this batch). total=7, selected=2, ya=0 → PAUSAR.
    Must NOT write Fecha_Soldadura / Soldador to Operaciones.
    """
    request = FinalizarRequest(
        tag_spool="SP-777",
        worker_id=129,
        worker_nombre="FF(129)",
        operacion=ActionType.SOLD,
        selected_unions=["OT-777+3", "OT-777+4"],
    )

    response = await service.finalizar_spool(request)

    assert response.action_taken == "PAUSAR", (
        "2-of-7 SOLD must PAUSAR (T-021 fix). "
        f"Got action_taken={response.action_taken}"
    )

    # Inspect every batch_update_by_column_name call for forbidden fields
    all_updates = []
    for call in mock_sheets.batch_update_by_column_name.call_args_list:
        updates = call.kwargs.get("updates") or (
            call.args[1] if len(call.args) > 1 else []
        )
        all_updates.extend(updates)

    written_columns = {u["column_name"] for u in all_updates}
    assert "Fecha_Soldadura" not in written_columns, (
        "Fecha_Soldadura must NOT be written on partial SOLD (T-021)."
    )
    assert "Soldador" not in written_columns, (
        "Soldador must NOT be written on partial SOLD (T-021)."
    )


@pytest.mark.asyncio
async def test_finalizar_sold_all_unions_writes_fecha_soldadura(
    mock_sheets, mock_metadata, mock_conflict
):
    """
    Happy path: 5 remaining unions finalized; 2 already sold + 5 = 7 = total.
    Must write Fecha_Soldadura and Soldador (COMPLETAR path).
    """
    # Spool state entering this call: 2 already sold
    spool = MagicMock(spec=Spool)
    spool.tag_spool = "SP-777"
    spool.ot = "777"
    spool.total_uniones = 7
    spool.uniones_arm_completadas = 7
    spool.uniones_sold_completadas = 2
    spool.fecha_materiales = "2026-01-20"
    spool.fecha_ocupacion = "11-04-2026 08:00:00"
    spool.ocupado_por = "FF(129)"
    spool.armador = "NR(94)"
    spool.soldador = None
    spool.fecha_armado = "11-04-2026"
    spool.fecha_soldadura = None
    mock_sheets.get_spool_by_tag = MagicMock(return_value=spool)

    remaining = [_make_union(i, arm_done=True, tipo="BW") for i in range(3, 8)]
    repo = MagicMock()
    repo.get_disponibles_sold_by_ot = MagicMock(return_value=remaining)
    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[])
    repo.get_by_ot = MagicMock(return_value=[
        _make_union(1, arm_done=True, sold_done=True, tipo="BW"),
        _make_union(2, arm_done=True, sold_done=True, tipo="BW"),
        *remaining
    ])
    repo.get_by_spool = MagicMock(return_value=repo.get_by_ot.return_value)
    repo.get_by_ids = MagicMock(return_value=remaining)
    repo.batch_update_sold_full = MagicMock(return_value=5)
    repo.get_total_uniones = MagicMock(return_value=7)
    repo.calculate_metrics = MagicMock(return_value={
        "arm_completadas": 7, "sold_completadas": 7,
        "pulgadas_arm": 14.0, "pulgadas_sold": 14.0,
    })
    repo._find_spool_row = MagicMock(return_value=42)

    service = OccupationService(
        sheets_repository=mock_sheets,
        metadata_repository=mock_metadata,
        conflict_service=mock_conflict,
        union_repository=repo,
    )

    request = FinalizarRequest(
        tag_spool="SP-777",
        worker_id=129,
        worker_nombre="FF(129)",
        operacion=ActionType.SOLD,
        selected_unions=[f"OT-777+{i}" for i in range(3, 8)],
    )

    response = await service.finalizar_spool(request)
    assert response.action_taken == "COMPLETAR"

    all_updates = []
    for call in mock_sheets.batch_update_by_column_name.call_args_list:
        updates = call.kwargs.get("updates") or (
            call.args[1] if len(call.args) > 1 else []
        )
        all_updates.extend(updates)
    written_columns = {u["column_name"] for u in all_updates}
    assert "Fecha_Soldadura" in written_columns
    assert "Soldador" in written_columns


# ============================================================================
# Plan 1.2 — SOLDCompletionFilter behaviour
# ============================================================================

def test_sold_completion_filter_rejects_2_of_7_spool_without_fecha():
    """
    v4.0 spool with partial counters and no Fecha_Soldadura: reject.
    This is expected behavior pre-fix and must remain post-fix.
    """
    spool = Spool(
        tag_spool="SP-CLEAN",
        ot="777",
        total_uniones=7,
        uniones_sold_completadas=2,
        fecha_soldadura=None,
    )
    result = SOLDCompletionFilter().apply(spool)
    assert result.passed is False


def test_sold_completion_filter_rejects_stale_fecha_soldadura():
    """
    Corrupt production scenario (MK-1923-TW-17422-004): v4.0 spool has
    Fecha_Soldadura wrongly written while counters say 2/7. Filter must
    REJECT regardless of Fecha_Soldadura — contadores are source of truth
    in v4.0.
    """
    spool = Spool(
        tag_spool="MK-1923-TW-17422-004",
        ot="17422",
        total_uniones=7,
        uniones_sold_completadas=2,
        fecha_soldadura="2026-04-10",   # ← corrupt: should not have been written
    )
    result = SOLDCompletionFilter().apply(spool)
    assert result.passed is False, (
        f"Filter must reject partial v4.0 spool despite stale Fecha_Soldadura. "
        f"Reason: {result.reason}"
    )


def test_sold_completion_filter_accepts_full_v40():
    """v4.0 spool with 7/7 counters passes."""
    spool = Spool(
        tag_spool="SP-OK",
        ot="777",
        total_uniones=7,
        uniones_sold_completadas=7,
        fecha_soldadura="2026-04-10",
    )
    result = SOLDCompletionFilter().apply(spool)
    assert result.passed is True


def test_sold_completion_filter_v30_still_uses_fecha_soldadura():
    """v3.0 spool (Total_Uniones=0) falls back to Fecha_Soldadura — no regression."""
    spool = Spool(
        tag_spool="SP-LEGACY",
        ot="001",
        total_uniones=0,
        uniones_sold_completadas=0,
        fecha_soldadura="2026-04-10",
    )
    result = SOLDCompletionFilter().apply(spool)
    assert result.passed is True
