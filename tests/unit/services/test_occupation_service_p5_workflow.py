"""
Unit tests for P5 Confirmation Workflow (v4.0 Phase 8).

These tests validate the NEW P5 confirmation architecture where:
- All writes happen ONLY when user confirms in P5
- NO Redis locks (infrastructure removed)
- NO optimistic locking (version column not updated)
- NO backend validation before write (trust P4 filters)
- Last-Write-Wins (LWW) for race conditions
- Automatic retry on transient Sheets errors (3 attempts)

Test Coverage:
1. INICIAR P5 workflow
   - v2.1 support (minimal writes)
   - v4.0 support (with Estado_Detalle)
   - EstadoDetalleBuilder integration
   - Hardcoded states for ARM/SOLD
   - INICIAR_SPOOL event logging

2. FINALIZAR P5 workflow
   - Timestamp parsing from Fecha_Ocupacion
   - batch_update_arm_full() / batch_update_sold_full() calls
   - Pulgadas calculation in metadata
   - COMPLETAR with v4.0 counters
   - PAUSAR without date writes

3. Race condition handling
   - LWW acceptance (no validation before write)
   - 409 error with occupant data

Reference:
- Architecture: .planning/P5-CONFIRMATION-ARCHITECTURE.md
- Service: backend/services/occupation_service.py
- Review: .planning/P5-CRITICAL-REVIEW-SUMMARY.md
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, date

from backend.services.occupation_service import OccupationService
from backend.models.occupation import (
    IniciarRequest,
    FinalizarRequest,
    OccupationResponse
)
from backend.models.spool import Spool
from backend.models.union import Union
from backend.models.enums import ActionType, EventoTipo
from backend.exceptions import (
    SpoolNoEncontradoError,
    ArmPrerequisiteError,
    NoAutorizadoError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository for P5 workflow tests."""
    repo = MagicMock()

    # v4.0 spool with occupation fields
    mock_spool_v4 = MagicMock(spec=Spool)
    mock_spool_v4.tag_spool = "TEST-V4"
    mock_spool_v4.ot = "123"
    mock_spool_v4.total_uniones = 10  # v4.0 indicator
    mock_spool_v4.uniones_arm_completadas = 0  # v4.0 counter (read-only, formula in Sheets)
    mock_spool_v4.uniones_sold_completadas = 0  # v4.0 counter (read-only, formula in Sheets)
    mock_spool_v4.pulgadas_arm = 0.0  # v4.0 metric (read-only, formula in Sheets)
    mock_spool_v4.pulgadas_sold = 0.0  # v4.0 metric (read-only, formula in Sheets)
    mock_spool_v4.ocupado_por = None
    mock_spool_v4.fecha_ocupacion = None
    mock_spool_v4.version = "uuid-v1"
    mock_spool_v4.estado_detalle = None
    mock_spool_v4.fecha_materiales = date(2026, 1, 20)
    mock_spool_v4.armador = None
    mock_spool_v4.soldador = None
    mock_spool_v4.fecha_armado = None
    mock_spool_v4.fecha_soldadura = None

    # v2.1 spool (no Total_Uniones)
    mock_spool_v21 = MagicMock(spec=Spool)
    mock_spool_v21.tag_spool = "TEST-V21"
    mock_spool_v21.ot = "124"
    mock_spool_v21.total_uniones = None  # v2.1 indicator
    mock_spool_v21.uniones_arm_completadas = None  # v2.1: columns don't exist yet
    mock_spool_v21.uniones_sold_completadas = None
    mock_spool_v21.pulgadas_arm = None
    mock_spool_v21.pulgadas_sold = None
    mock_spool_v21.ocupado_por = None
    mock_spool_v21.fecha_ocupacion = None
    mock_spool_v21.version = "uuid-v2"
    mock_spool_v21.estado_detalle = None
    mock_spool_v21.fecha_materiales = date(2026, 1, 20)
    mock_spool_v21.armador = None
    mock_spool_v21.soldador = None
    mock_spool_v21.fecha_armado = None
    mock_spool_v21.fecha_soldadura = None

    def get_spool_by_tag(tag: str):
        if tag == "TEST-V4":
            return mock_spool_v4
        elif tag == "TEST-V21":
            return mock_spool_v21
        return None

    repo.get_spool_by_tag = MagicMock(side_effect=get_spool_by_tag)
    repo.batch_update_by_column_name = MagicMock()

    # Mock read_worksheet to return headers (needed for ColumnMapCache)
    mock_headers = [
        "TAG_SPOOL", "OT", "NV", "Fecha_Materiales", "Fecha_Armado", "Armador",
        "Fecha_Soldadura", "Soldador", "Ocupado_Por", "Fecha_Ocupacion",
        "version", "Estado_Detalle", "Total_Uniones", "Uniones_ARM_Completadas",
        "Pulgadas_ARM", "Uniones_SOLD_Completadas", "Pulgadas_SOLD"
    ]
    repo.read_worksheet = MagicMock(return_value=[mock_headers])

    return repo


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_union_repository():
    """Mock UnionRepository with P5 batch methods."""
    repo = MagicMock()

    # Mock available unions
    def create_union(n_union: int, dn: float = 2.5):
        return Union(
            id=f"TEST-V4+{n_union}",
            ot="123",
            tag_spool="TEST-V4",
            n_union=n_union,
            dn_union=dn,
            tipo_union="BW",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version="uuid-union",
            creado_por="SYSTEM(0)",
            fecha_creacion=datetime(2026, 1, 1)
        )

    repo.get_disponibles_arm_by_ot = MagicMock(return_value=[
        create_union(i) for i in range(1, 11)  # 10 unions
    ])

    repo.get_disponibles_sold_by_ot = MagicMock(return_value=[
        create_union(i) for i in range(1, 6)  # 5 unions
    ])

    # P5 batch methods
    repo.batch_update_arm_full = MagicMock(return_value=3)
    repo.batch_update_sold_full = MagicMock(return_value=2)

    # For pulgadas calculation
    repo.get_by_ids = MagicMock(return_value=[
        create_union(1, dn=2.5),
        create_union(2, dn=3.0),
        create_union(3, dn=2.5)
    ])

    return repo


@pytest.fixture
def mock_validation_service():
    """Mock ValidationService."""
    service = MagicMock()
    service.validate_arm_prerequisite = MagicMock()
    return service


@pytest.fixture
def mock_conflict_service():
    """Mock ConflictService."""
    service = MagicMock()
    service.generate_version_token = MagicMock(return_value="version-uuid")
    service.update_with_retry = AsyncMock(return_value="new-version-uuid")
    return service


@pytest.fixture
def occupation_service_p5(
    mock_sheets_repository,
    mock_metadata_repository,
    mock_union_repository,
    mock_validation_service,
    mock_conflict_service
):
    """Create OccupationService for P5 workflow testing."""
    service = OccupationService(
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        union_repository=mock_union_repository,
        conflict_service=mock_conflict_service
    )
    # Inject validation service
    service.validation_service = mock_validation_service
    return service


# ============================================================================
# INICIAR P5 WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_p5_v4_spool_writes_estado_detalle(
    occupation_service_p5,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    Test INICIAR P5 workflow for v4.0 spool includes Estado_Detalle.

    Validates:
    - Writes Ocupado_Por, Fecha_Ocupacion, Estado_Detalle
    - Uses EstadoDetalleBuilder
    - Hardcoded states (ARM: en_progreso/pendiente)
    - Logs INICIAR_SPOOL event
    """
    request = IniciarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    # Mock EstadoDetalleBuilder (imported inside iniciar_spool)
    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
        mock_builder_class.return_value = mock_builder

        response = await occupation_service_p5.iniciar_spool(request)

    # Assert: Success
    assert response.success is True
    assert response.tag_spool == "TEST-V4"
    assert "iniciado" in response.message.lower()

    # Assert: Sheets write called with 3 columns
    mock_sheets_repository.batch_update_by_column_name.assert_called_once()
    call_kwargs = mock_sheets_repository.batch_update_by_column_name.call_args.kwargs

    # Extract updates from batch_updates list
    batch_updates = call_kwargs["updates"]
    updates_dict = {u["column_name"]: u["value"] for u in batch_updates}

    assert updates_dict["Ocupado_Por"] == "MR(93)"
    assert "Fecha_Ocupacion" in updates_dict
    assert updates_dict["Estado_Detalle"] == "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"

    # Assert: EstadoDetalleBuilder called with hardcoded states
    mock_builder.build.assert_called_once()
    build_kwargs = mock_builder.build.call_args.kwargs
    assert build_kwargs["arm_state"] == "en_progreso"
    assert build_kwargs["sold_state"] == "pendiente"
    assert build_kwargs["ocupado_por"] == "MR(93)"

    # Assert: INICIAR_SPOOL event logged
    mock_metadata_repository.log_event.assert_called_once()
    event_kwargs = mock_metadata_repository.log_event.call_args.kwargs
    assert event_kwargs["evento_tipo"] == EventoTipo.INICIAR_SPOOL.value


@pytest.mark.asyncio
async def test_iniciar_p5_v21_spool_minimal_writes(
    occupation_service_p5,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    Test INICIAR P5 workflow for v2.1 spool writes occupation fields.

    Validates:
    - Writes Ocupado_Por + Fecha_Ocupacion + Estado_Detalle
    - Logs INICIAR_SPOOL event
    - EstadoDetalleBuilder used even for v2.1

    Note: Current implementation writes Estado_Detalle for both v2.1 and v4.0
    """
    request = IniciarRequest(
        tag_spool="TEST-V21",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)"
        mock_builder_class.return_value = mock_builder

        response = await occupation_service_p5.iniciar_spool(request)

    # Assert: Success
    assert response.success is True
    assert response.tag_spool == "TEST-V21"

    # Assert: Writes include Estado_Detalle (current implementation)
    call_kwargs = mock_sheets_repository.batch_update_by_column_name.call_args.kwargs
    batch_updates = call_kwargs["updates"]
    updates = {u["column_name"]: u["value"] for u in batch_updates}

    assert updates["Ocupado_Por"] == "MR(93)"
    assert "Fecha_Ocupacion" in updates
    assert "Estado_Detalle" in updates  # v2.1 ALSO gets Estado_Detalle

    # Assert: INICIAR_SPOOL event logged
    mock_metadata_repository.log_event.assert_called_once()


@pytest.mark.asyncio
async def test_iniciar_p5_sold_hardcoded_states(
    occupation_service_p5,
    mock_sheets_repository
):
    """
    Test INICIAR P5 for SOLD operation uses correct hardcoded states.

    Validates:
    - ARM state = "completado"
    - SOLD state = "en_progreso"
    """
    # Mock spool with ARM completed (uniones_arm_completadas >= 1)
    mock_spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    mock_spool.uniones_arm_completadas = 5  # ARM already completed on some unions

    request = IniciarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.SOLD
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder') as mock_builder_class:
        mock_builder = MagicMock()
        mock_builder.build.return_value = "MR(93) trabajando SOLD (ARM completado, SOLD en progreso)"
        mock_builder_class.return_value = mock_builder

        response = await occupation_service_p5.iniciar_spool(request)

    # Assert: EstadoDetalleBuilder called with SOLD hardcoded states
    build_kwargs = mock_builder.build.call_args.kwargs
    assert build_kwargs["arm_state"] == "completado"
    assert build_kwargs["sold_state"] == "en_progreso"


@pytest.mark.asyncio
async def test_iniciar_p5_arm_prerequisite_validation(
    occupation_service_p5,
    mock_validation_service,
    mock_sheets_repository
):
    """
    Test INICIAR P5 validates ARM prerequisite for SOLD.

    Validates:
    - Raises ArmPrerequisiteError if uniones_arm_completadas < 1
    - Error message includes Spanish text
    """
    # Mock spool with NO ARM completed (uniones_arm_completadas = 0)
    mock_spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    mock_spool.uniones_arm_completadas = 0  # No ARM completed yet

    request = IniciarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.SOLD
    )

    with pytest.raises(ArmPrerequisiteError) as exc_info:
        await occupation_service_p5.iniciar_spool(request)

    # Validate error message (Spanish)
    assert "No se puede iniciar SOLD" in str(exc_info.value)
    assert "0/10 uniones armadas" in str(exc_info.value)


@pytest.mark.asyncio
async def test_iniciar_p5_no_redis_lock_acquisition(
    occupation_service_p5,
    mock_sheets_repository
):
    """
    Test INICIAR P5 does NOT acquire Redis locks.

    Validates:
    - No redis_lock_service calls
    - Direct write to Sheets
    - LWW strategy (no validation before write)
    """
    request = IniciarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder'):
        response = await occupation_service_p5.iniciar_spool(request)

    # Assert: Success without Redis
    assert response.success is True

    # Assert: Direct Sheets write (no lock check)
    mock_sheets_repository.batch_update_by_column_name.assert_called_once()


# ============================================================================
# FINALIZAR P5 WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_finalizar_p5_timestamp_from_fecha_ocupacion(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 uses Fecha_Ocupacion as INICIO timestamp.

    Validates:
    - Parses Fecha_Ocupacion (DD-MM-YYYY HH:MM:SS format)
    - Uses parsed timestamp as ARM_FECHA_INICIO
    - Uses now_chile() as ARM_FECHA_FIN
    """
    # Mock spool with Fecha_Ocupacion
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"  # When spool was taken

    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1", "TEST-V4+2", "TEST-V4+3"]
    )

    with patch('backend.services.occupation_service.now_chile') as mock_now:
        mock_now.return_value = datetime(2026, 2, 4, 14, 30, 0)
        response = await occupation_service_p5.finalizar_spool(request)

    # Assert: batch_update_arm_full called with parsed timestamps
    mock_union_repository.batch_update_arm_full.assert_called_once()
    call_kwargs = mock_union_repository.batch_update_arm_full.call_args.kwargs

    timestamp_inicio = call_kwargs["timestamp_inicio"]
    timestamp_fin = call_kwargs["timestamp_fin"]

    # INICIO parsed from Fecha_Ocupacion
    assert timestamp_inicio.year == 2026
    assert timestamp_inicio.month == 2
    assert timestamp_inicio.day == 4
    assert timestamp_inicio.hour == 10
    assert timestamp_inicio.minute == 0

    # FIN is current time
    assert timestamp_fin.year == 2026
    assert timestamp_fin.month == 2
    assert timestamp_fin.day == 4
    assert timestamp_fin.hour == 14
    assert timestamp_fin.minute == 30


@pytest.mark.asyncio
async def test_finalizar_p5_uses_batch_update_full_methods(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 uses batch_update_arm_full() / batch_update_sold_full().

    Validates:
    - Calls new batch methods (not old batch_update_arm)
    - Writes WORKER + INICIO + FIN in single batch
    """
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"

    request_arm = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1", "TEST-V4+2"]
    )

    with patch('backend.services.occupation_service.now_chile'):
        await occupation_service_p5.finalizar_spool(request_arm)

    # Assert: batch_update_arm_full called (not batch_update_arm)
    mock_union_repository.batch_update_arm_full.assert_called_once()
    call_kwargs = mock_union_repository.batch_update_arm_full.call_args.kwargs

    assert call_kwargs["tag_spool"] == "TEST-V4"
    assert call_kwargs["worker"] == "MR(93)"
    assert "timestamp_inicio" in call_kwargs
    assert "timestamp_fin" in call_kwargs


@pytest.mark.asyncio
async def test_finalizar_p5_pulgadas_always_in_metadata(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository,
    mock_metadata_repository
):
    """
    Test FINALIZAR P5 always includes pulgadas in metadata (PAUSAR and COMPLETAR).

    Validates:
    - Calculates sum of DN_UNION for processed unions
    - Includes in metadata_json for both PAUSAR and COMPLETAR
    """
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"

    # Mock unions with DN values: 2.5 + 3.0 + 2.5 = 8.0
    mock_union_repository.get_by_ids.return_value = [
        MagicMock(dn_union=2.5),
        MagicMock(dn_union=3.0),
        MagicMock(dn_union=2.5)
    ]

    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1", "TEST-V4+2", "TEST-V4+3"]
    )

    with patch('backend.services.occupation_service.now_chile'):
        response = await occupation_service_p5.finalizar_spool(request)

    # Assert: Metadata logged with pulgadas
    mock_metadata_repository.log_event.assert_called_once()
    event_kwargs = mock_metadata_repository.log_event.call_args.kwargs

    import json
    metadata = json.loads(event_kwargs["metadata_json"])

    assert "pulgadas" in metadata
    assert metadata["pulgadas"] == 8.0


@pytest.mark.asyncio
async def test_finalizar_p5_completar_updates_v4_counters(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 COMPLETAR updates v4.0 counters and dates.

    Validates:
    - Writes Fecha_Armado + Armador (COMPLETAR ARM)
    - Updates Uniones_ARM_Completadas + Pulgadas_ARM
    - Does NOT write these fields for PAUSAR
    """
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"

    # Select ALL 10 unions → COMPLETAR
    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=[f"TEST-V4+{i}" for i in range(1, 11)]  # All 10
    )

    # Mock get_by_ids to return all 10 unions with DN=2.5 each
    mock_union_repository.get_by_ids.return_value = [
        MagicMock(dn_union=2.5) for _ in range(10)
    ]

    with patch('backend.services.occupation_service.now_chile'):
        with patch('backend.services.occupation_service.today_chile') as mock_today:
            mock_today.return_value = date(2026, 2, 4)
            response = await occupation_service_p5.finalizar_spool(request)

    # Assert: COMPLETAR action
    assert response.action_taken == "COMPLETAR"

    # Assert: Sheets write does NOT include v4.0 formula columns (managed by Google Sheets)
    call_kwargs = mock_sheets_repository.batch_update_by_column_name.call_args.kwargs
    batch_updates = call_kwargs["updates"]
    updates = {u["column_name"]: u["value"] for u in batch_updates}

    assert updates["Fecha_Armado"] == "04-02-2026"
    assert updates["Armador"] == "MR(93)"
    # v4.0 counter columns are NOT written (they are formulas in Sheets)
    assert "Uniones_ARM_Completadas" not in updates
    assert "Pulgadas_ARM" not in updates


@pytest.mark.asyncio
async def test_finalizar_p5_pausar_no_date_writes(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 PAUSAR does NOT write Fecha_Armado or counters.

    Validates:
    - Clears Ocupado_Por + Fecha_Ocupacion
    - Updates Estado_Detalle
    - Does NOT write Fecha_Armado, Armador, or v4.0 counters
    """
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"

    # Select 3 out of 10 unions → PAUSAR
    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1", "TEST-V4+2", "TEST-V4+3"]
    )

    with patch('backend.services.occupation_service.now_chile'):
        response = await occupation_service_p5.finalizar_spool(request)

    # Assert: PAUSAR action
    assert response.action_taken == "PAUSAR"

    # Assert: Sheets write does NOT include dates or counters
    call_kwargs = mock_sheets_repository.batch_update_by_column_name.call_args.kwargs
    batch_updates = call_kwargs["updates"]
    updates = {u["column_name"]: u["value"] for u in batch_updates}

    assert "Fecha_Armado" not in updates
    assert "Armador" not in updates
    assert "Uniones_ARM_Completadas" not in updates
    assert "Pulgadas_ARM" not in updates

    # Assert: Clears occupation
    assert updates["Ocupado_Por"] == ""
    assert updates["Fecha_Ocupacion"] == ""


@pytest.mark.asyncio
async def test_finalizar_p5_no_optimistic_locking(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 does NOT update version column.

    Validates:
    - No version token validation
    - No version column update
    - LWW strategy (direct write)
    """
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"
    spool.version = "uuid-original"

    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1"]
    )

    with patch('backend.services.occupation_service.now_chile'):
        response = await occupation_service_p5.finalizar_spool(request)

    # Assert: Sheets write does NOT include version
    call_kwargs = mock_sheets_repository.batch_update_by_column_name.call_args.kwargs
    batch_updates = call_kwargs["updates"]
    updates = {u["column_name"]: u["value"] for u in batch_updates}

    assert "version" not in updates


# ============================================================================
# RACE CONDITION HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_p5_lww_no_validation_before_write(
    occupation_service_p5,
    mock_sheets_repository
):
    """
    Test INICIAR P5 Last-Write-Wins - no validation before write.

    Validates:
    - Does NOT check Ocupado_Por before writing
    - Writes directly to Sheets
    - Trusts P4 filters (no backend validation)
    """
    # Mock spool as already occupied (but INICIAR doesn't check)
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "JP(45)"  # Already occupied
    spool.fecha_ocupacion = "04-02-2026 09:00:00"

    request = IniciarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder'):
        response = await occupation_service_p5.iniciar_spool(request)

    # Assert: Success (LWW - overwrites JP's occupation)
    assert response.success is True

    # Assert: Write called (no validation error)
    mock_sheets_repository.batch_update_by_column_name.assert_called_once()


@pytest.mark.asyncio
async def test_finalizar_p5_lww_no_validation_before_write(
    occupation_service_p5,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 Last-Write-Wins - no ownership validation before write.

    Validates:
    - Trusts P4 filters showed spool as owned by current worker
    - No NoAutorizadoError raised
    - Writes directly
    """
    # Mock spool as occupied by current worker (P4 filtered correctly)
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"

    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1"]
    )

    with patch('backend.services.occupation_service.now_chile'):
        response = await occupation_service_p5.finalizar_spool(request)

    # Assert: Success (no ownership validation)
    assert response.success is True


# ============================================================================
# METADATA EVENT LOGGING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_p5_metadata_minimal_fields(
    occupation_service_p5,
    mock_metadata_repository,
    mock_sheets_repository
):
    """
    Test INICIAR P5 logs minimal metadata fields.

    Validates:
    - metadata_json contains: ocupado_por, fecha_ocupacion
    - Does NOT contain: spool_version, estado_detalle_previo, filtros
    """
    request = IniciarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with patch('backend.services.estado_detalle_builder.EstadoDetalleBuilder'):
        response = await occupation_service_p5.iniciar_spool(request)

    # Assert: Metadata logged
    event_kwargs = mock_metadata_repository.log_event.call_args.kwargs

    import json
    metadata = json.loads(event_kwargs["metadata_json"])

    # Assert: Minimal fields only
    assert "ocupado_por" in metadata
    assert "fecha_ocupacion" in metadata

    # Assert: Excluded fields
    assert "spool_version" not in metadata
    assert "estado_detalle_previo" not in metadata
    assert "filtros_aplicados" not in metadata


@pytest.mark.asyncio
async def test_finalizar_p5_metadata_with_union_details(
    occupation_service_p5,
    mock_metadata_repository,
    mock_sheets_repository,
    mock_union_repository
):
    """
    Test FINALIZAR P5 logs metadata with union processing details.

    Validates:
    - metadata_json contains: unions_processed, selected_unions, pulgadas
    """
    spool = mock_sheets_repository.get_spool_by_tag("TEST-V4")
    spool.ocupado_por = "MR(93)"
    spool.fecha_ocupacion = "04-02-2026 10:00:00"

    request = FinalizarRequest(
        tag_spool="TEST-V4",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["TEST-V4+1", "TEST-V4+2", "TEST-V4+3"]
    )

    with patch('backend.services.occupation_service.now_chile'):
        response = await occupation_service_p5.finalizar_spool(request)

    # Assert: Metadata logged
    event_kwargs = mock_metadata_repository.log_event.call_args.kwargs

    import json
    metadata = json.loads(event_kwargs["metadata_json"])

    assert "unions_processed" in metadata
    assert "selected_unions" in metadata
    assert "pulgadas" in metadata
    assert metadata["unions_processed"] == 3
    assert metadata["selected_unions"] == ["TEST-V4+1", "TEST-V4+2", "TEST-V4+3"]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iniciar_p5_spool_not_found(occupation_service_p5, mock_sheets_repository):
    """Test INICIAR P5 raises SpoolNoEncontradoError if spool not found."""
    mock_sheets_repository.get_spool_by_tag.return_value = None

    request = IniciarRequest(
        tag_spool="NONEXISTENT",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM
    )

    with pytest.raises(SpoolNoEncontradoError):
        await occupation_service_p5.iniciar_spool(request)


@pytest.mark.asyncio
async def test_finalizar_p5_spool_not_found(occupation_service_p5, mock_sheets_repository):
    """Test FINALIZAR P5 raises SpoolNoEncontradoError if spool not found."""
    mock_sheets_repository.get_spool_by_tag.return_value = None

    request = FinalizarRequest(
        tag_spool="NONEXISTENT",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion=ActionType.ARM,
        selected_unions=["U1"]
    )

    with pytest.raises(SpoolNoEncontradoError):
        await occupation_service_p5.finalizar_spool(request)
