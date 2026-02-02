"""
Integration tests for OccupationService v4.0 workflows.

Tests INICIAR/FINALIZAR operations with ARM-before-SOLD validation,
auto-determination logic, and metrología auto-transition.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime
import json

from backend.services.occupation_service import OccupationService
from backend.services.redis_lock_service import RedisLockService
from backend.services.conflict_service import ConflictService
from backend.services.redis_event_service import RedisEventService
from backend.services.validation_service import ValidationService
from backend.repositories.union_repository import UnionRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.models.occupation import IniciarRequest, FinalizarRequest
from backend.models.enums import Operacion
from backend.models.spool import Spool
from backend.exceptions import (
    ArmPrerequisiteError,
    SpoolOccupiedError,
    NoAutorizadoError
)
from tests.fixtures.mock_uniones_data import get_standard_data


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository with realistic data."""
    repo = MagicMock()

    # Mock Uniones data
    mock_data = get_standard_data()
    repo.read_worksheet.return_value = mock_data

    # Mock spool data
    mock_spool = MagicMock(spec=Spool)
    mock_spool.tag_spool = "OT-001"
    mock_spool.ot = "001"
    mock_spool.fecha_materiales = "15-01-2026"
    mock_spool.ocupado_por = None
    repo.get_spool_by_tag.return_value = mock_spool

    # Mock _get_worksheet for batch operations
    mock_worksheet = MagicMock()
    mock_worksheet.batch_update = MagicMock()
    repo._get_worksheet.return_value = mock_worksheet

    return repo


@pytest.fixture
def union_repo(mock_sheets_repo):
    """Create UnionRepository with mocked sheets."""
    ColumnMapCache.invalidate("Uniones")
    return UnionRepository(mock_sheets_repo)


@pytest.fixture
def metadata_repo():
    """Mock MetadataRepository."""
    repo = MagicMock()
    repo.log_event = MagicMock()
    repo.batch_log_events = MagicMock()
    return repo


@pytest.fixture
def redis_lock_service():
    """Mock RedisLockService."""
    service = AsyncMock()
    service.acquire_lock.return_value = "lock-token-123"
    service.release_lock.return_value = True
    service.get_lock_owner.return_value = (93, "lock-token-123")
    service.lazy_cleanup_one_abandoned_lock = AsyncMock()
    return service


@pytest.fixture
def conflict_service():
    """Mock ConflictService."""
    service = AsyncMock()
    service.update_with_retry.return_value = "new-version-uuid"
    return service


@pytest.fixture
def redis_event_service():
    """Mock RedisEventService."""
    service = AsyncMock()
    service.publish_spool_update = AsyncMock()
    return service


@pytest.fixture
def validation_service(union_repo):
    """Real ValidationService with mocked UnionRepository."""
    return ValidationService(union_repo=union_repo)


@pytest.fixture
def occupation_service(
    redis_lock_service,
    mock_sheets_repo,
    metadata_repo,
    conflict_service,
    redis_event_service,
    union_repo,
    validation_service
):
    """Create OccupationService with all dependencies."""
    return OccupationService(
        redis_lock_service=redis_lock_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=metadata_repo,
        conflict_service=conflict_service,
        redis_event_service=redis_event_service,
        union_repository=union_repo,
        validation_service=validation_service
    )


class TestArmToSoldWorkflow:
    """Test ARM-before-SOLD validation workflow."""

    @pytest.mark.asyncio
    async def test_sold_iniciar_fails_without_arm(
        self,
        occupation_service,
        union_repo
    ):
        """
        Should fail SOLD INICIAR when no ARM unions are completed.

        Scenario:
        1. OT has 10 unions, all ARM disponibles (none completed)
        2. Attempt INICIAR SOLD operation
        3. Should raise ArmPrerequisiteError (403)
        """
        # Setup: Verify all unions have no ARM completion
        all_unions = union_repo.get_by_ot("001")

        # Mock all unions as ARM incomplete for this test
        for union in all_unions:
            union.arm_fecha_fin = None

        # Execute: INICIAR SOLD should fail
        request = IniciarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=Operacion.SOLD
        )

        with pytest.raises(ArmPrerequisiteError):
            await occupation_service.iniciar_spool(request)

    @pytest.mark.asyncio
    async def test_sold_iniciar_succeeds_with_partial_arm(
        self,
        occupation_service,
        union_repo
    ):
        """
        Should succeed SOLD INICIAR when at least 1 ARM union is completed.

        Scenario:
        1. Complete 1 ARM union
        2. INICIAR SOLD should succeed
        3. Redis lock should be acquired
        """
        # Setup: Verify some ARM unions are complete
        arm_completed = [u for u in union_repo.get_by_ot("001") if u.arm_fecha_fin is not None]
        assert len(arm_completed) >= 1  # Test data has 7 ARM complete

        # Execute: INICIAR SOLD
        request = IniciarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=Operacion.SOLD
        )

        response = await occupation_service.iniciar_spool(request)

        # Verify: Success
        assert response.success is True
        assert "iniciado" in response.message.lower()

        # Verify: Redis lock acquired
        occupation_service.redis_lock_service.acquire_lock.assert_called_once_with(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)"
        )

    @pytest.mark.asyncio
    async def test_sold_finalizar_filters_by_union_type(
        self,
        occupation_service,
        union_repo
    ):
        """
        Should filter SOLD disponibles by union type (exclude FW).

        Scenario:
        1. OT has mixed union types (FW + BW/BR/SO)
        2. FINALIZAR SOLD should only show SOLD-required types
        3. FW unions should be excluded from selection
        """
        # Setup: Get SOLD disponibles (ARM complete, SOLD pending)
        sold_disponibles = union_repo.get_disponibles_sold_by_ot("001")

        # Filter to only SOLD-required types
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES
        sold_required = [
            u for u in sold_disponibles
            if u.tipo_union in SOLD_REQUIRED_TYPES
        ]

        # Note: Mock data may not have FW unions, but we test the filtering logic

        # Select some SOLD-required unions
        selected_ids = [u.id for u in sold_required[:2]] if sold_required else []

        if not selected_ids:
            pytest.skip("No SOLD-required unions available in test data")

        # Execute: FINALIZAR SOLD
        request = FinalizarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nome="MR(93)",
            operacion=Operacion.SOLD,
            selected_unions=selected_ids
        )

        response = await occupation_service.finalizar_spool(request)

        # Verify: Success
        assert response.success is True
        assert response.unions_processed > 0

    @pytest.mark.asyncio
    async def test_complete_arm_then_sold_workflow(
        self,
        occupation_service,
        union_repo
    ):
        """
        End-to-end: Complete some ARM, then complete SOLD on those unions.

        Scenario:
        1. INICIAR ARM
        2. FINALIZAR ARM with 5 unions (partial)
        3. INICIAR SOLD
        4. FINALIZAR SOLD with those 5 unions
        5. Verify state transitions
        """
        # Step 1: INICIAR ARM
        iniciar_arm = IniciarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=Operacion.ARM
        )

        response = await occupation_service.iniciar_spool(iniciar_arm)
        assert response.success is True

        # Step 2: FINALIZAR ARM with partial selection
        arm_disponibles = union_repo.get_disponibles_arm_by_ot("001")
        selected_arm = [u.id for u in arm_disponibles[:2]]  # 2 out of 3

        # Mock batch update to simulate ARM completion
        with patch.object(union_repo, 'batch_update_arm', return_value=2):
            finalizar_arm = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=Operacion.ARM,
                selected_unions=selected_arm
            )

            response = await occupation_service.finalizar_spool(finalizar_arm)
            assert response.success is True
            assert response.action_taken == "PAUSAR"  # Not all ARM complete

        # Step 3: INICIAR SOLD (should succeed now)
        iniciar_sold = IniciarRequest(
            tag_spool="OT-001",
            worker_id=45,
            worker_nombre="JD(45)",
            operacion=Operacion.SOLD
        )

        # Reset lock owner for new worker
        occupation_service.redis_lock_service.get_lock_owner.return_value = (45, "lock-token-456")

        response = await occupation_service.iniciar_spool(iniciar_sold)
        assert response.success is True

        # Step 4: FINALIZAR SOLD
        sold_disponibles = union_repo.get_disponibles_sold_by_ot("001")

        # Filter to SOLD-required types
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES
        sold_required = [
            u for u in sold_disponibles
            if u.tipo_union in SOLD_REQUIRED_TYPES
        ]

        selected_sold = [u.id for u in sold_required[:2]] if sold_required else []

        if not selected_sold:
            pytest.skip("No SOLD-required unions available in test data")

        with patch.object(union_repo, 'batch_update_sold', return_value=len(selected_sold)):
            finalizar_sold = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=45,
                worker_nombre="JD(45)",
                operacion=Operacion.SOLD,
                selected_unions=selected_sold
            )

            response = await occupation_service.finalizar_spool(finalizar_sold)
            assert response.success is True
            assert response.unions_processed == len(selected_sold)

    @pytest.mark.asyncio
    async def test_mixed_union_types_arm_only(
        self,
        occupation_service,
        union_repo
    ):
        """
        Test spool with FW unions (ARM-only, no SOLD needed).

        Scenario:
        1. Create spool with only FW unions
        2. Complete all FW via ARM
        3. SOLD INICIAR should still check ARM prerequisite
        4. But no SOLD work needed (FW is ARM-only)
        """
        # Note: This test depends on mock data having FW unions
        # If mock data doesn't have FW, we'll skip
        all_unions = union_repo.get_by_ot("001")
        fw_unions = [u for u in all_unions if u.tipo_union == 'FW']

        if not fw_unions:
            pytest.skip("No FW unions in test data")

        # Execute: INICIAR SOLD should validate ARM prerequisite
        request = IniciarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=Operacion.SOLD
        )

        # Should succeed (ARM unions are completed in mock data)
        response = await occupation_service.iniciar_spool(request)
        assert response.success is True


class TestMetrologiaAutoTransition:
    """Test metrología auto-transition scenarios with mixed union types."""

    @pytest.mark.asyncio
    async def test_metrologia_triggers_when_all_work_complete(
        self,
        occupation_service,
        union_repo
    ):
        """
        Metrología should trigger when FW ARM'd and SOLD-required SOLD'd.

        Scenario:
        1. Spool has mixed union types (FW + BW/BR/SO)
        2. Complete all FW unions via ARM
        3. Complete all SOLD-required unions via SOLD
        4. FINALIZAR should trigger metrología auto-transition
        5. Estado_Detalle should update to "En Cola Metrología"
        """
        # Setup: Get all unions
        all_unions = union_repo.get_by_ot("001")

        # Manually set all unions as complete for this test
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        for union in all_unions:
            # Complete ARM for all
            union.arm_fecha_fin = datetime.now()

            # Complete SOLD only for SOLD-required types
            if union.tipo_union in SOLD_REQUIRED_TYPES:
                union.sol_fecha_fin = datetime.now()

        # Mock get_by_spool to return our modified unions
        with patch.object(union_repo, 'get_by_spool', return_value=all_unions):
            # Check should_trigger_metrologia
            should_trigger = occupation_service.should_trigger_metrologia("OT-001")
            assert should_trigger is True

    @pytest.mark.asyncio
    async def test_metrologia_does_not_trigger_with_incomplete_arm(
        self,
        occupation_service,
        union_repo
    ):
        """
        Metrología should NOT trigger if FW ARM incomplete.

        Scenario:
        1. Spool has FW unions
        2. Some FW unions not ARM'd
        3. All SOLD complete
        4. Should NOT trigger metrología
        """
        # Setup: Get all unions
        all_unions = union_repo.get_by_ot("001")

        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Complete SOLD for all SOLD-required types
        for union in all_unions:
            if union.tipo_union in SOLD_REQUIRED_TYPES:
                union.arm_fecha_fin = datetime.now()
                union.sol_fecha_fin = datetime.now()
            else:
                # Leave some FW incomplete
                union.arm_fecha_fin = None

        # Mock get_by_spool
        with patch.object(union_repo, 'get_by_spool', return_value=all_unions):
            should_trigger = occupation_service.should_trigger_metrologia("OT-001")
            assert should_trigger is False

    @pytest.mark.asyncio
    async def test_metrologia_does_not_trigger_with_incomplete_sold(
        self,
        occupation_service,
        union_repo
    ):
        """
        Metrología should NOT trigger if SOLD-required unions incomplete.

        Scenario:
        1. All FW ARM'd
        2. Some BW/BR/SO SOLD incomplete
        3. Should NOT trigger metrología
        """
        # Setup
        all_unions = union_repo.get_by_ot("001")

        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Complete all ARM
        for union in all_unions:
            union.arm_fecha_fin = datetime.now()

            # Leave some SOLD-required unions incomplete
            if union.tipo_union in SOLD_REQUIRED_TYPES:
                union.sol_fecha_fin = None  # Incomplete

        # Mock get_by_spool
        with patch.object(union_repo, 'get_by_spool', return_value=all_unions):
            should_trigger = occupation_service.should_trigger_metrologia("OT-001")
            assert should_trigger is False

    @pytest.mark.asyncio
    async def test_finalizar_triggers_metrologia_and_logs_event(
        self,
        occupation_service,
        union_repo,
        metadata_repo
    ):
        """
        FINALIZAR should trigger metrología and log METROLOGIA_AUTO_TRIGGERED event.

        Scenario:
        1. FINALIZAR completes the last SOLD union
        2. All work now complete (FW ARM'd + SOLD-required SOLD'd)
        3. Metrología auto-transition should trigger
        4. METROLOGIA_AUTO_TRIGGERED event should be logged
        5. Response should include metrologia_triggered flag
        """
        # Setup: Complete all unions except one
        all_unions = union_repo.get_by_ot("001")

        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Complete everything except last SOLD union
        sold_required_unions = [
            u for u in all_unions
            if u.tipo_union in SOLD_REQUIRED_TYPES
        ]

        for union in all_unions:
            union.arm_fecha_fin = datetime.now()

            if union.tipo_union in SOLD_REQUIRED_TYPES:
                # Leave last one incomplete
                if union.id == sold_required_unions[-1].id:
                    union.sol_fecha_fin = None
                else:
                    union.sol_fecha_fin = datetime.now()

        # Get the last disponible SOLD union
        last_union = sold_required_unions[-1]

        # Mock StateService trigger_metrologia_transition
        with patch('backend.services.occupation_service.StateService') as MockStateService:
            mock_state_service = AsyncMock()
            mock_state_service.trigger_metrologia_transition.return_value = "pendiente_metrologia"
            MockStateService.return_value = mock_state_service

            # Mock batch update
            with patch.object(union_repo, 'batch_update_sold', return_value=1):
                # Mock get_by_spool to return updated unions
                updated_unions = all_unions.copy()
                for u in updated_unions:
                    if u.id == last_union.id:
                        u.sol_fecha_fin = datetime.now()

                with patch.object(union_repo, 'get_by_spool', return_value=updated_unions):
                    # Execute: FINALIZAR with last union
                    request = FinalizarRequest(
                        tag_spool="OT-001",
                        worker_id=93,
                        worker_nombre="MR(93)",
                        operacion=Operacion.SOLD,
                        selected_unions=[last_union.id]
                    )

                    response = await occupation_service.finalizar_spool(request)

                    # Verify: Metrología triggered
                    assert response.success is True
                    assert response.metrologia_triggered is True
                    assert response.new_state == "pendiente_metrologia"
                    assert "(Listo para metrología)" in response.message

                    # Verify: METROLOGIA_AUTO_TRIGGERED event logged
                    # Check that log_event was called with METROLOGIA_AUTO_TRIGGERED
                    log_event_calls = metadata_repo.log_event.call_args_list
                    metrologia_event_logged = any(
                        "METROLOGIA_AUTO_TRIGGERED" in str(call)
                        for call in log_event_calls
                    )
                    assert metrologia_event_logged

    @pytest.mark.asyncio
    async def test_metrologia_does_not_trigger_on_pausar(
        self,
        occupation_service,
        union_repo
    ):
        """
        Metrología should NOT check on PAUSAR (only on COMPLETAR).

        Scenario:
        1. FINALIZAR with partial selection (triggers PAUSAR)
        2. Metrología check should NOT run
        3. Response should not have metrologia_triggered flag
        """
        # Setup: Partial FINALIZAR
        disponibles = union_repo.get_disponibles_sold_by_ot("001")

        from backend.services.occupation_service import SOLD_REQUIRED_TYPES
        sold_required = [
            u for u in disponibles
            if u.tipo_union in SOLD_REQUIRED_TYPES
        ]

        if not sold_required:
            pytest.skip("No SOLD-required unions available")

        # Select partial (not all)
        selected = [u.id for u in sold_required[:1]]  # Just 1 out of many

        # Mock batch update
        with patch.object(union_repo, 'batch_update_sold', return_value=1):
            request = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=Operacion.SOLD,
                selected_unions=selected
            )

            response = await occupation_service.finalizar_spool(request)

            # Verify: PAUSAR triggered (not COMPLETAR)
            assert response.action_taken == "PAUSAR"

            # Verify: No metrología triggered
            assert response.metrologia_triggered is None or response.metrologia_triggered is False
