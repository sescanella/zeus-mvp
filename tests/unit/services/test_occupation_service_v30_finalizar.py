"""
Test v3.0 spool support in FINALIZAR operation.

v3.0 spools (legacy spools without union tracking) should use simplified
COMPLETAR logic that bypasses all union-related code.

Also tests cancellation (selected_unions=[]) which now runs BEFORE the v3.0
check, making it version-agnostic (works for both v3.0 and v4.0 spools).
"""

import pytest
import json
from datetime import date
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from backend.services.occupation_service import OccupationService
from backend.models.occupation import FinalizarRequest
from backend.models.enums import ActionType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_spool():
    """Base v3.0 spool mock (total_uniones=None)."""
    spool = Mock()
    spool.tag_spool = "OT-001-v30"
    spool.ot = "001"
    spool.total_uniones = None  # v3.0 indicator
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"
    spool.fecha_armado = None
    spool.fecha_soldadura = None
    return spool


@pytest.fixture
def mock_sheets_repository(mock_spool):
    """Mock SheetsRepository for v3.0 spool tests."""
    repo = Mock()
    repo.get_spool_by_tag.return_value = mock_spool
    repo.find_row_by_column_value.return_value = 10
    repo._index_to_column_letter.return_value = "G"
    repo.batch_update_by_column_name.return_value = None
    return repo


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    repo = Mock()
    repo.log_event.return_value = None
    return repo


@pytest.fixture
def mock_conflict_service():
    """Mock ConflictService with async update_with_retry."""
    service = Mock()
    service.update_with_retry = AsyncMock(return_value="new-version")
    return service


@pytest.fixture
def occupation_service(mock_sheets_repository, mock_metadata_repository, mock_conflict_service):
    """Create OccupationService with mocked dependencies."""
    return OccupationService(
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=mock_conflict_service,
        union_repository=None,  # v3.0 doesn't need union repo
        validation_service=None,
        union_service=None
    )


# ============================================================================
# v3.0 COMPLETAR TESTS (using action_override="COMPLETAR" to bypass cancellation)
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_v30_spool_uses_simplified_completar(
    occupation_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    Test that v3.0 spools use simplified COMPLETAR logic (no union processing).

    v3.0 spools should:
    - Skip all union-related code
    - Directly update Fecha_Armado/Soldadura
    - Clear Ocupado_Por and Fecha_Ocupacion
    - Log COMPLETAR event
    - Return COMPLETAR action

    NOTE: Uses action_override="COMPLETAR" because selected_unions=[] now
    triggers cancellation before v3.0 detection (by design).
    """
    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[],
        action_override="COMPLETAR"
    )

    with patch('backend.core.column_map_cache.ColumnMapCache') as mock_cache:
        mock_cache.get_or_build.return_value = {"tagspool": 6}

        result = await occupation_service.finalizar_spool(request)

    # Verify response
    assert result.success is True
    assert result.tag_spool == "OT-001-v30"
    assert result.action_taken == "COMPLETAR"
    assert result.unions_processed == 0
    assert "v3.0" in result.message.lower()

    # Verify Sheets update called with correct data
    mock_sheets_repository.batch_update_by_column_name.assert_called_once()
    call_args = mock_sheets_repository.batch_update_by_column_name.call_args
    updates = call_args[1]["updates"]

    # Extract column updates
    update_dict = {u["column_name"]: u["value"] for u in updates}

    # Verify occupation cleared
    assert update_dict["Ocupado_Por"] == ""
    assert update_dict["Fecha_Ocupacion"] == ""

    # Verify fecha updated (ARM)
    assert "Fecha_Armado" in update_dict
    assert update_dict["Armador"] == "MR(93)"

    # Verify Estado_Detalle updated
    assert "ARM completado" in update_dict["Estado_Detalle"]

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()
    call_args = mock_metadata_repository.log_event.call_args
    assert call_args[1]["evento_tipo"] == "COMPLETAR_SPOOL"
    assert call_args[1]["accion"] == "COMPLETAR"

    # Verify metadata JSON contains v3.0 marker
    metadata_json = json.loads(call_args[1]["metadata_json"])
    assert metadata_json["spool_version"] == "v3.0"


@pytest.mark.asyncio
async def test_finalizar_v30_sold_updates_correct_columns(
    occupation_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """Test v3.0 SOLD operation updates Fecha_Soldadura (not Fecha_Armado)."""
    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=45,
        worker_nombre="JP(45)",
        operacion=ActionType.SOLD,
        selected_unions=[],
        action_override="COMPLETAR"
    )

    with patch('backend.core.column_map_cache.ColumnMapCache') as mock_cache:
        mock_cache.get_or_build.return_value = {"tagspool": 6}

        result = await occupation_service.finalizar_spool(request)

    # Verify Sheets update
    call_args = mock_sheets_repository.batch_update_by_column_name.call_args
    updates = call_args[1]["updates"]
    update_dict = {u["column_name"]: u["value"] for u in updates}

    # Verify SOLD columns updated (not ARM)
    assert "Fecha_Soldadura" in update_dict
    assert update_dict["Soldador"] == "JP(45)"
    assert "SOLD completado" in update_dict["Estado_Detalle"]

    # Verify ARM columns NOT updated
    assert "Fecha_Armado" not in update_dict
    assert "Armador" not in update_dict


@pytest.mark.asyncio
async def test_finalizar_v30_no_union_repository_calls(
    occupation_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    Test that v3.0 COMPLETAR path NEVER calls union_repository methods.

    This is the core fix - v3.0 spools should bypass all union logic entirely.
    """
    # Add union_repository mock to verify it's never called
    occupation_service.union_repository = Mock()

    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[],
        action_override="COMPLETAR"
    )

    with patch('backend.core.column_map_cache.ColumnMapCache') as mock_cache:
        mock_cache.get_or_build.return_value = {"tagspool": 6}

        result = await occupation_service.finalizar_spool(request)

    # Verify union_repository methods NEVER called
    occupation_service.union_repository.get_disponibles_arm_by_ot.assert_not_called()
    occupation_service.union_repository.get_disponibles_sold_by_ot.assert_not_called()
    occupation_service.union_repository.batch_update_arm_full.assert_not_called()
    occupation_service.union_repository.batch_update_sold_full.assert_not_called()
    occupation_service.union_repository.get_by_ids.assert_not_called()

    # Verify result is still successful
    assert result.success is True
    assert result.action_taken == "COMPLETAR"


@pytest.mark.asyncio
async def test_finalizar_v30_always_completar_never_pausar(
    occupation_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    Test that v3.0 spools use COMPLETAR when action_override="COMPLETAR".

    v3.0 spools are all-or-nothing (no partial completion tracking).
    """
    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[],
        action_override="COMPLETAR"
    )

    with patch('backend.core.column_map_cache.ColumnMapCache') as mock_cache:
        mock_cache.get_or_build.return_value = {"tagspool": 6}

        result = await occupation_service.finalizar_spool(request)

    # Verify COMPLETAR (not PAUSAR or CANCELADO)
    assert result.action_taken == "COMPLETAR"

    # Verify Estado_Detalle says "completado" not "pausado"
    call_args = mock_sheets_repository.batch_update_by_column_name.call_args
    updates = call_args[1]["updates"]
    update_dict = {u["column_name"]: u["value"] for u in updates}

    assert "completado" in update_dict["Estado_Detalle"].lower()
    assert "pausado" not in update_dict["Estado_Detalle"].lower()


# ============================================================================
# v3.0 CANCELLATION TESTS (selected_unions=[] without action_override)
# ============================================================================

@pytest.mark.asyncio
async def test_v30_cancel_selected_unions_empty_returns_cancelado(
    occupation_service,
    mock_conflict_service,
):
    """
    v3.0 spool with selected_unions=[] returns CANCELADO.

    After the reorder fix, the cancellation check runs BEFORE the v3.0
    detection, so v3.0 spools can now properly cancel instead of always
    going through COMPLETAR.
    """
    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
    )

    result = await occupation_service.finalizar_spool(request)

    assert result.success is True
    assert result.tag_spool == "OT-001-v30"
    assert result.action_taken == "CANCELADO"
    assert result.unions_processed == 0


@pytest.mark.asyncio
async def test_v30_cancel_does_not_write_fecha_armado(
    occupation_service,
    mock_conflict_service,
    mock_spool,
):
    """
    v3.0 cancellation with fecha_armado=None does NOT write Fecha_Armado.

    Cancellation should only clear occupation fields and conditionally
    clear Armador — it must never set a completion date.
    """
    mock_spool.fecha_armado = None  # Never completed ARM

    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
    )

    result = await occupation_service.finalizar_spool(request)

    assert result.action_taken == "CANCELADO"

    # Verify update_with_retry was called and inspect the updates dict
    mock_conflict_service.update_with_retry.assert_awaited_once()
    call_kwargs = mock_conflict_service.update_with_retry.call_args[1]
    updates = call_kwargs["updates"]

    # Must clear Ocupado_Por
    assert updates["Ocupado_Por"] == ""

    # Must NOT contain Fecha_Armado (cancellation never writes dates)
    assert "Fecha_Armado" not in updates


@pytest.mark.asyncio
async def test_v30_cancel_clears_armador_when_fecha_armado_empty(
    occupation_service,
    mock_conflict_service,
    mock_spool,
):
    """
    v3.0 cancellation clears Armador when Fecha_Armado is empty.

    If Fecha_Armado is None, it means Armador was set by INICIAR (not by
    a previous COMPLETAR), so it should be reverted to "".
    """
    mock_spool.fecha_armado = None

    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
    )

    result = await occupation_service.finalizar_spool(request)

    assert result.action_taken == "CANCELADO"

    call_kwargs = mock_conflict_service.update_with_retry.call_args[1]
    updates = call_kwargs["updates"]

    # Armador should be cleared since Fecha_Armado is empty
    assert updates["Armador"] == ""


@pytest.mark.asyncio
async def test_v30_cancel_does_not_clear_armador_when_fecha_armado_has_value(
    occupation_service,
    mock_conflict_service,
    mock_spool,
):
    """
    v3.0 cancellation does NOT clear Armador when Fecha_Armado has a value.

    If Fecha_Armado is set, a previous worker completed ARM — current
    cancellation should not erase that completed-by attribution.
    """
    mock_spool.fecha_armado = "23-03-2026"

    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
    )

    result = await occupation_service.finalizar_spool(request)

    assert result.action_taken == "CANCELADO"

    call_kwargs = mock_conflict_service.update_with_retry.call_args[1]
    updates = call_kwargs["updates"]

    # Armador must NOT be in updates (preserve previous completed-by)
    assert "Armador" not in updates


@pytest.mark.asyncio
async def test_v30_cancel_rebuilds_estado_detalle_correctly(
    occupation_service,
    mock_conflict_service,
    mock_spool,
):
    """
    v3.0 cancellation rebuilds Estado_Detalle to reflect post-cancellation state.

    With both fecha_armado=None and fecha_soldadura=None, the spool should
    show "Disponible - ARM pendiente, SOLD pendiente".
    """
    mock_spool.fecha_armado = None
    mock_spool.fecha_soldadura = None

    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
    )

    result = await occupation_service.finalizar_spool(request)

    assert result.action_taken == "CANCELADO"

    call_kwargs = mock_conflict_service.update_with_retry.call_args[1]
    updates = call_kwargs["updates"]

    estado = updates["Estado_Detalle"]
    assert "Disponible" in estado
    assert "ARM pendiente" in estado
    assert "SOLD pendiente" in estado
