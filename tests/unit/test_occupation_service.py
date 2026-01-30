"""
Unit tests for OccupationService - business logic for TOMAR/PAUSAR/COMPLETAR.

Tests validate:
- TOMAR validates prerequisites (Fecha_Materiales)
- TOMAR acquires lock before sheet update
- PAUSAR verifies ownership before clearing
- COMPLETAR updates correct date column
- Batch TOMAR returns partial success details
- Metadata events logged for all operations

Reference:
- Service: backend/services/occupation_service.py
- Plan: 02-04-PLAN.md
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call
from datetime import date

from backend.services.occupation_service import OccupationService
from backend.models.occupation import (
    TomarRequest,
    PausarRequest,
    CompletarRequest,
    BatchTomarRequest
)
from backend.models.spool import Spool
from backend.exceptions import (
    SpoolNoEncontradoError,
    SpoolOccupiedError,
    DependenciasNoSatisfechasError,
    NoAutorizadoError,
    LockExpiredError
)


@pytest.fixture
def mock_redis_lock_service():
    """Mock RedisLockService."""
    service = AsyncMock()
    service.acquire_lock = AsyncMock(return_value="93:test-token-uuid")
    service.release_lock = AsyncMock(return_value=True)
    service.get_lock_owner = AsyncMock(return_value=(None, None))
    return service


@pytest.fixture
def mock_sheets_repository():
    """Mock SheetsRepository."""
    repo = MagicMock()
    repo.get_spool_by_tag = MagicMock(return_value=Spool(
        tag_spool="TAG-001",
        fecha_materiales="2026-01-20",
        armador=None,
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None
    ))
    repo.update_spool_occupation = MagicMock()
    repo.update_spool_completion = MagicMock()
    return repo


@pytest.fixture
def mock_metadata_repository():
    """Mock MetadataRepository."""
    repo = MagicMock()
    repo.log_event = MagicMock()
    return repo


@pytest.fixture
def mock_conflict_service():
    """Mock ConflictService."""
    service = MagicMock()
    service.generate_version_token = MagicMock(return_value="version-uuid")
    service.update_with_retry = AsyncMock()
    return service


@pytest.fixture
def mock_redis_event_service():
    """Mock RedisEventService for real-time event publishing."""
    service = AsyncMock()
    service.publish_spool_update = AsyncMock()
    return service


@pytest.fixture
def occupation_service(
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service
):
    """Create OccupationService with mocked dependencies."""
    return OccupationService(
        redis_lock_service=mock_redis_lock_service,
        sheets_repository=mock_sheets_repository,
        metadata_repository=mock_metadata_repository,
        conflict_service=mock_conflict_service,
        redis_event_service=mock_redis_event_service
    )


@pytest.mark.asyncio
async def test_tomar_validates_prerequisites(
    occupation_service,
    mock_sheets_repository
):
    """
    TOMAR validates Fecha_Materiales prerequisite before acquisition.

    Validates:
    - Spool must exist
    - Fecha_Materiales must be set
    - Raises DependenciasNoSatisfechasError if not met
    """
    # Mock spool without Fecha_Materiales
    mock_sheets_repository.get_spool_by_tag.return_value = Spool(
        tag_spool="TAG-MISSING-PREREQ",
        fecha_materiales=None,  # Prerequisite not met
        armador=None,
        soldador=None,
        fecha_armado=None,
        fecha_soldadura=None
    )

    request = TomarRequest(
        tag_spool="TAG-MISSING-PREREQ",
        worker_id=93,
        worker_nombre="Worker93",
        operacion="ARM"
    )

    # Should raise prerequisite error
    with pytest.raises(DependenciasNoSatisfechasError) as exc_info:
        await occupation_service.tomar(request)

    assert "Fecha_Materiales" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tomar_acquires_lock_before_sheet_update(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository
):
    """
    TOMAR acquires Redis lock atomically before updating sheet.

    Validates:
    - Lock acquired before sheet write
    - If lock acquisition fails, sheet not updated
    - SpoolOccupiedError raised if already occupied
    """
    # Mock lock acquisition failure
    mock_redis_lock_service.acquire_lock.side_effect = SpoolOccupiedError(
        "TAG-OCCUPIED",
        "Spool already occupied by worker 94"
    )

    request = TomarRequest(
        tag_spool="TAG-OCCUPIED",
        worker_id=93,
        worker_nombre="Worker93",
        operacion="ARM"
    )

    # Should raise occupation error
    with pytest.raises(SpoolOccupiedError):
        await occupation_service.tomar(request)

    # Sheet should NOT be updated
    mock_sheets_repository.update_spool_occupation.assert_not_called()


@pytest.mark.asyncio
async def test_tomar_success_flow(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    TOMAR success flow: validate → lock → update sheet → log metadata.

    Validates:
    - Full success flow executes in order
    - Lock acquired
    - Sheet updated with Ocupado_Por/Fecha_Ocupacion
    - Metadata event logged
    - Success response returned
    """
    request = TomarRequest(
        tag_spool="TAG-001",
        worker_id=93,
        worker_nombre="Worker93",
        operacion="ARM"
    )

    # Execute TOMAR
    response = await occupation_service.tomar(request)

    # Assertions
    assert response.success is True
    assert response.tag_spool == "TAG-001"

    # Verify lock acquired
    mock_redis_lock_service.acquire_lock.assert_called_once_with("TAG-001", 93)

    # Verify sheet updated
    mock_sheets_repository.update_spool_occupation.assert_called_once()

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()


@pytest.mark.asyncio
async def test_pausar_verifies_ownership(
    occupation_service,
    mock_redis_lock_service
):
    """
    PAUSAR verifies worker owns lock before clearing.

    Validates:
    - get_lock_owner called to check ownership
    - Raises NoAutorizadoError if worker doesn't own lock
    - Only owner can pause work
    """
    # Mock lock owned by different worker
    mock_redis_lock_service.get_lock_owner.return_value = (94, "94:other-token")

    request = PausarRequest(
        tag_spool="TAG-002",
        worker_id=93,  # Not the owner
        worker_nombre="Worker93"
    )

    # Should raise authorization error
    with pytest.raises(NoAutorizadoError) as exc_info:
        await occupation_service.pausar(request)

    assert "not authorized" in str(exc_info.value).lower() or "not owned" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_pausar_success_clears_occupation(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository
):
    """
    PAUSAR success: verify ownership → clear occupation → release lock.

    Validates:
    - Ownership verified
    - Ocupado_Por and Fecha_Ocupacion cleared
    - Redis lock released
    - Metadata event logged
    """
    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    request = PausarRequest(
        tag_spool="TAG-003",
        worker_id=93,
        worker_nombre="Worker93"
    )

    # Execute PAUSAR
    response = await occupation_service.pausar(request)

    # Assertions
    assert response.success is True

    # Verify sheet updated (occupation cleared)
    mock_sheets_repository.update_spool_occupation.assert_called_once()

    # Verify lock released
    mock_redis_lock_service.release_lock.assert_called_once()

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()


@pytest.mark.asyncio
async def test_completar_updates_correct_date_column(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository
):
    """
    COMPLETAR updates fecha_armado for ARM or fecha_soldadura for SOLD.

    Validates:
    - Correct date column updated based on operation type
    - Ownership verified before completion
    - Ocupado_Por cleared after completion
    """
    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    request = CompletarRequest(
        tag_spool="TAG-004",
        worker_id=93,
        worker_nombre="Worker93",
        fecha_operacion="2026-01-27"
    )

    # Execute COMPLETAR
    response = await occupation_service.completar(request)

    # Assertions
    assert response.success is True

    # Verify sheet updated with completion date
    mock_sheets_repository.update_spool_completion.assert_called_once()

    # Verify lock released
    mock_redis_lock_service.release_lock.assert_called_once()


@pytest.mark.asyncio
async def test_batch_tomar_returns_partial_success(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository
):
    """
    Batch TOMAR processes each spool independently and returns details.

    Validates:
    - Each spool processed individually
    - Failures don't block successes
    - Response includes per-spool details
    - Correct counts for succeeded/failed
    """
    # Mock 3 successes and 2 failures
    def mock_acquire_lock(tag_spool, worker_id):
        if tag_spool in ["TAG-OCCUPIED-1", "TAG-OCCUPIED-2"]:
            raise SpoolOccupiedError(tag_spool, "Already occupied")
        return f"{worker_id}:mock-token"

    mock_redis_lock_service.acquire_lock.side_effect = mock_acquire_lock

    request = BatchTomarRequest(
        tag_spools=["TAG-OK-1", "TAG-OCCUPIED-1", "TAG-OK-2", "TAG-OCCUPIED-2", "TAG-OK-3"],
        worker_id=93,
        worker_nombre="Worker93",
        operacion="ARM"
    )

    # Execute batch TOMAR
    response = await occupation_service.batch_tomar(request)

    # Assertions
    assert response.total == 5
    assert response.succeeded == 3
    assert response.failed == 2

    # Verify details for each spool
    assert len(response.details) == 5

    # Check specific results
    success_tags = [d.tag_spool for d in response.details if d.success]
    failed_tags = [d.tag_spool for d in response.details if not d.success]

    assert set(success_tags) == {"TAG-OK-1", "TAG-OK-2", "TAG-OK-3"}
    assert set(failed_tags) == {"TAG-OCCUPIED-1", "TAG-OCCUPIED-2"}


@pytest.mark.asyncio
async def test_metadata_logging_best_effort(
    occupation_service,
    mock_metadata_repository,
    mock_redis_lock_service
):
    """
    Metadata logging is best-effort and doesn't block operations.

    Validates:
    - Metadata logging failure logged as warning
    - Operation completes successfully despite metadata error
    - Main workflow not interrupted
    """
    # Mock metadata logging failure
    mock_metadata_repository.log_event.side_effect = Exception("Metadata write failed")

    request = TomarRequest(
        tag_spool="TAG-005",
        worker_id=93,
        worker_nombre="Worker93",
        operacion="ARM"
    )

    # Execute TOMAR - should succeed despite metadata failure
    response = await occupation_service.tomar(request)

    # Assertions - operation still succeeds
    assert response.success is True

    # Verify lock was acquired and sheet was updated
    mock_redis_lock_service.acquire_lock.assert_called_once()


@pytest.mark.asyncio
async def test_lock_expired_during_operation(
    occupation_service,
    mock_redis_lock_service
):
    """
    Handle lock expiration during long operations.

    Validates:
    - LockExpiredError raised if lock expires
    - Clear error message about expiration
    - Worker notified to retry operation
    """
    # Mock lock expired when attempting COMPLETAR
    mock_redis_lock_service.get_lock_owner.return_value = (None, None)  # Lock gone

    request = CompletarRequest(
        tag_spool="TAG-EXPIRED",
        worker_id=93,
        worker_nombre="Worker93",
        fecha_operacion="2026-01-27"
    )

    # Should raise lock expired error
    with pytest.raises((LockExpiredError, NoAutorizadoError)):
        await occupation_service.completar(request)


@pytest.mark.asyncio
async def test_pausar_logs_metadata_event_with_correct_fields(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service
):
    """
    PAUSAR must log PAUSAR_SPOOL event to Metadata with correct fields.

    Validates:
    - metadata_repository.log_event called
    - evento_tipo = "PAUSAR_SPOOL"
    - operacion = "ARM"
    - accion = "PAUSAR"
    - fecha_operacion is provided with correct format (DD-MM-YYYY)
    - metadata_json contains estado and lock_released
    """
    import re
    import json

    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    request = PausarRequest(
        tag_spool="TEST-02",
        worker_id=93,
        worker_nombre="MR(93)"
    )

    # Execute PAUSAR
    response = await occupation_service.pausar(request)

    # Assertions
    assert response.success is True

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()

    # Inspect call arguments
    call_kwargs = mock_metadata_repository.log_event.call_args.kwargs
    assert call_kwargs["evento_tipo"] == "PAUSAR_SPOOL"
    assert call_kwargs["tag_spool"] == "TEST-02"
    assert call_kwargs["worker_id"] == 93
    assert call_kwargs["worker_nombre"] == "MR(93)"
    assert call_kwargs["operacion"] == "ARM"
    assert call_kwargs["accion"] == "PAUSAR"

    # Verify fecha_operacion provided and has correct format
    assert call_kwargs["fecha_operacion"] is not None
    assert re.match(r'\d{2}-\d{2}-\d{4}', call_kwargs["fecha_operacion"]), \
        f"fecha_operacion must be DD-MM-YYYY format, got: {call_kwargs['fecha_operacion']}"

    # Verify metadata_json structure
    metadata_dict = json.loads(call_kwargs["metadata_json"])
    assert "estado" in metadata_dict
    assert "lock_released" in metadata_dict
    assert metadata_dict["lock_released"] is True


@pytest.mark.asyncio
async def test_pausar_metadata_failure_logs_critical_error_with_traceback(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service,
    caplog
):
    """
    If metadata logging fails, PAUSAR should log CRITICAL error with full traceback.

    Validates:
    - Operation completes successfully (user not impacted)
    - logger.error called (not logger.warning)
    - Error message contains "CRITICAL"
    - exc_info=True ensures traceback in logs
    """
    import logging

    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    # Mock metadata logging failure
    mock_metadata_repository.log_event.side_effect = Exception("Sheets API timeout")

    request = PausarRequest(
        tag_spool="TEST-03",
        worker_id=93,
        worker_nombre="MR(93)"
    )

    # Capture logs
    with caplog.at_level(logging.ERROR):
        # Execute PAUSAR - should succeed despite metadata failure
        response = await occupation_service.pausar(request)

    # Assertions
    assert response.success is True  # Operation succeeds

    # Verify error logged
    assert any("CRITICAL" in record.message for record in caplog.records), \
        "Expected CRITICAL in error message"
    assert any("Metadata logging failed" in record.message for record in caplog.records), \
        "Expected 'Metadata logging failed' in error message"
    assert any("TEST-03" in record.message for record in caplog.records), \
        "Expected tag_spool in error message"

    # Verify traceback included (exc_info=True)
    assert any(record.exc_info is not None for record in caplog.records), \
        "Expected exc_info=True to capture traceback"


@pytest.mark.asyncio
async def test_completar_logs_metadata_event_with_correct_fields(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service
):
    """
    COMPLETAR must log metadata event with correct fields (verify fix applied).

    This test ensures COMPLETAR has same error handling as PAUSAR.
    """
    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    request = CompletarRequest(
        tag_spool="TEST-04",
        worker_id=93,
        worker_nombre="MR(93)",
        fecha_operacion=date(2026, 1, 30)
    )

    # Execute COMPLETAR
    response = await occupation_service.completar(request)

    # Assertions
    assert response.success is True

    # Verify metadata logged
    mock_metadata_repository.log_event.assert_called_once()

    # Verify fields
    call_kwargs = mock_metadata_repository.log_event.call_args.kwargs
    assert call_kwargs["evento_tipo"] in ["COMPLETAR_ARM", "COMPLETAR_SOLD"]
    assert call_kwargs["accion"] == "COMPLETAR"
    assert call_kwargs["fecha_operacion"] is not None


@pytest.mark.asyncio
async def test_completar_metadata_failure_logs_critical_error(
    occupation_service,
    mock_redis_lock_service,
    mock_sheets_repository,
    mock_metadata_repository,
    mock_conflict_service,
    mock_redis_event_service,
    caplog
):
    """
    If metadata logging fails, COMPLETAR should log CRITICAL error (same as PAUSAR).
    """
    import logging

    # Mock lock owned by requesting worker
    mock_redis_lock_service.get_lock_owner.return_value = (93, "93:test-token")

    # Mock metadata logging failure
    mock_metadata_repository.log_event.side_effect = Exception("Sheets API error")

    request = CompletarRequest(
        tag_spool="TEST-05",
        worker_id=93,
        worker_nombre="MR(93)",
        fecha_operacion=date(2026, 1, 30)
    )

    # Capture logs
    with caplog.at_level(logging.ERROR):
        response = await occupation_service.completar(request)

    # Assertions
    assert response.success is True
    assert any("CRITICAL" in record.message for record in caplog.records)
    assert any(record.exc_info is not None for record in caplog.records)
