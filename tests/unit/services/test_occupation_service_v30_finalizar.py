"""
Test v3.0 spool support in FINALIZAR operation.

v3.0 spools (legacy spools without union tracking) should use simplified
COMPLETAR logic that bypasses all union-related code.
"""

import pytest
import json
from datetime import date
from unittest.mock import Mock, MagicMock, patch

from backend.services.occupation_service import OccupationService
from backend.models.occupation import FinalizarRequest
from backend.models.enums import ActionType


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository for v3.0 spool tests."""
    repo = Mock()

    # Mock spool data (v3.0 = total_uniones is None)
    mock_spool = Mock()
    mock_spool.tag_spool = "OT-001-v30"
    mock_spool.ot = "001"
    mock_spool.total_uniones = None  # v3.0 indicator
    mock_spool.ocupado_por = "MR(93)"
    mock_spool.fecha_ocupacion = "04-02-2026 10:00:00"

    repo.get_spool_by_tag.return_value = mock_spool
    repo.find_row_by_column_value.return_value = 10  # Mock row number
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
def occupation_service(mock_sheets_repository, mock_metadata_repository):
    """Create OccupationService with mocked dependencies."""
    conflict_service = Mock()

    return OccupationService(
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=conflict_service,
        union_repository=None,  # v3.0 doesn't need union repo
        validation_service=None,
        union_service=None
    )


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
    """
    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]  # Empty for v3.0 (no unions)
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
    assert call_args[1]["evento_tipo"] == "COMPLETAR_ARM"
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
        selected_unions=[]
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
    Test that v3.0 path NEVER calls union_repository methods.

    This is the core fix - v3.0 spools should bypass all union logic entirely.
    """
    # Add union_repository mock to verify it's never called
    occupation_service.union_repository = Mock()

    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
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
    Test that v3.0 spools ALWAYS use COMPLETAR (never PAUSAR).

    v3.0 spools are all-or-nothing (no partial completion tracking).
    """
    request = FinalizarRequest(
        tag_spool="OT-001-v30",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[]
    )

    with patch('backend.core.column_map_cache.ColumnMapCache') as mock_cache:
        mock_cache.get_or_build.return_value = {"tagspool": 6}

        result = await occupation_service.finalizar_spool(request)

    # Verify always COMPLETAR (never PAUSAR or CANCELADO)
    assert result.action_taken == "COMPLETAR"

    # Verify Estado_Detalle says "completado" not "pausado"
    call_args = mock_sheets_repository.batch_update_by_column_name.call_args
    updates = call_args[1]["updates"]
    update_dict = {u["column_name"]: u["value"] for u in updates}

    assert "completado" in update_dict["Estado_Detalle"].lower()
    assert "pausado" not in update_dict["Estado_Detalle"].lower()
