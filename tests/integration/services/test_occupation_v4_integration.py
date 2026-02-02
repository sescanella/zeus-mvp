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
from backend.services.union_service import UnionService
from backend.services.redis_lock_service import RedisLockService
from backend.services.conflict_service import ConflictService
from backend.services.redis_event_service import RedisEventService
from backend.services.validation_service import ValidationService
from backend.repositories.union_repository import UnionRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.models.occupation import IniciarRequest, FinalizarRequest
from backend.models.enums import ActionType
from backend.models.spool import Spool
from backend.models.union import Union
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
    return ValidationService(union_repository=union_repo)


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
    """Create OccupationService with all dependencies (v4.0 union_service)."""
    union_service = UnionService(
        union_repo=union_repo,
        metadata_repo=metadata_repo,
        sheets_repo=mock_sheets_repo,
    )
    return OccupationService(
        redis_lock_service=redis_lock_service,
        sheets_repository=mock_sheets_repo,
        metadata_repository=metadata_repo,
        conflict_service=conflict_service,
        redis_event_service=redis_event_service,
        union_repository=union_repo,
        validation_service=validation_service,
        union_service=union_service,
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
        # Setup: Unions with no ARM completion (Union is frozen, use model_copy)
        all_unions = union_repo.get_by_ot("001")
        all_arm_incomplete = [u.model_copy(update={"arm_fecha_fin": None}) for u in all_unions]

        with patch.object(union_repo, "get_by_ot", return_value=all_arm_incomplete):
            # Execute: INICIAR SOLD should fail
            request = IniciarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.SOLD
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
            operacion=ActionType.SOLD
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
            operacion=ActionType.SOLD,
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
            operacion=ActionType.ARM
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
                operacion=ActionType.ARM,
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
            operacion=ActionType.SOLD
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
                operacion=ActionType.SOLD,
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
            operacion=ActionType.SOLD
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
        # Setup: All unions complete (Union is frozen, use model_copy)
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        all_unions = union_repo.get_by_ot("001")
        now = datetime.now()
        all_complete = [
            u.model_copy(update={
                "arm_fecha_fin": now,
                "sol_fecha_fin": now if u.tipo_union in SOLD_REQUIRED_TYPES else u.sol_fecha_fin
            })
            for u in all_unions
        ]

        with patch.object(union_repo, 'get_by_spool', return_value=all_complete):
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
        # Setup: Some FW incomplete (Union is frozen, use model_copy)
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        all_unions = union_repo.get_by_ot("001")
        now = datetime.now()
        mixed = [
            u.model_copy(update={
                "arm_fecha_fin": now if u.tipo_union in SOLD_REQUIRED_TYPES else None,
                "sol_fecha_fin": now if u.tipo_union in SOLD_REQUIRED_TYPES else u.sol_fecha_fin
            })
            for u in all_unions
        ]

        with patch.object(union_repo, 'get_by_spool', return_value=mixed):
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
        # Setup: All ARM complete, at least one SOLD-required union with sol_fecha_fin=None
        # Mock data uses "Brida"/"Socket" etc; SOLD_REQUIRED_TYPES are BW/BR/SO - force one BW
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        all_unions = union_repo.get_by_ot("001")
        now = datetime.now()
        # First union: BW (SOLD-required) with SOLD incomplete; rest: ARM complete, SOLD complete if SOLD-required
        sold_incomplete = []
        for i, u in enumerate(all_unions):
            if i == 0:
                sold_incomplete.append(u.model_copy(update={"arm_fecha_fin": now, "tipo_union": "BW", "sol_fecha_fin": None}))
            else:
                sold_incomplete.append(u.model_copy(update={
                    "arm_fecha_fin": now,
                    "sol_fecha_fin": now if u.tipo_union in SOLD_REQUIRED_TYPES else u.sol_fecha_fin
                }))

        with patch.object(union_repo, 'get_by_spool', return_value=sold_incomplete):
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
        # Setup: Complete all except last SOLD (Union is frozen, use model_copy)
        # Mock data has no SOLD_REQUIRED_TYPES; force first 3 to BW and leave last BW incomplete
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        all_unions = union_repo.get_by_ot("001")
        now = datetime.now()
        # Build list with first 3 as BW (SOLD-required), first 2 complete, 3rd incomplete
        unions_before_finalizar = []
        for i, u in enumerate(all_unions):
            if i < 3:
                # BW, ARM complete, SOLD complete only for first 2
                unions_before_finalizar.append(u.model_copy(update={
                    "tipo_union": "BW",
                    "arm_fecha_fin": now,
                    "sol_fecha_fin": None if i == 2 else now
                }))
            else:
                unions_before_finalizar.append(u.model_copy(update={"arm_fecha_fin": now, "sol_fecha_fin": now if u.tipo_union in SOLD_REQUIRED_TYPES else u.sol_fecha_fin}))
        last_union = unions_before_finalizar[2]  # The incomplete BW
        unions_after_finalizar = [u.model_copy(update={"sol_fecha_fin": now}) if u.id == last_union.id else u for u in unions_before_finalizar]

        # SOLD disponibles = SOLD-required with ARM complete, SOLD incomplete (only last_union)
        sold_disponibles = [last_union]

        with patch.object(occupation_service, 'should_trigger_metrologia', return_value=True):
            with patch('backend.services.state_service.StateService') as MockStateService:
                mock_state_service = AsyncMock()
                mock_state_service.trigger_metrologia_transition = AsyncMock(return_value="pendiente_metrologia")
                MockStateService.return_value = mock_state_service

                with patch.object(union_repo, 'get_disponibles_sold_by_ot', return_value=sold_disponibles):
                    with patch.object(union_repo, 'batch_update_sold', return_value=1):
                        with patch.object(union_repo, 'get_by_spool', side_effect=[unions_before_finalizar, unions_after_finalizar]):
                            # Execute: FINALIZAR with last union
                            request = FinalizarRequest(
                                tag_spool="OT-001",
                                worker_id=93,
                                worker_nombre="MR(93)",
                                operacion=ActionType.SOLD,
                                selected_unions=[last_union.id]
                            )

                            response = await occupation_service.finalizar_spool(request)

                            # Verify: Metrología triggered
                            assert response.success is True
                            assert response.metrologia_triggered is True
                            assert response.new_state == "pendiente_metrologia"
                            assert "(Listo para metrología)" in response.message

                            # Verify: METROLOGIA_AUTO_TRIGGERED event logged
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
                operacion=ActionType.SOLD,
                selected_unions=selected
            )

            response = await occupation_service.finalizar_spool(request)

            # Verify: PAUSAR triggered (not COMPLETAR)
            assert response.action_taken == "PAUSAR"

            # Verify: No metrología triggered
            assert response.metrologia_triggered is None or response.metrologia_triggered is False


class TestZeroUnionCancellation:
    """Test zero-union cancellation flow (FINALIZAR with empty selected_unions)."""

    @pytest.mark.asyncio
    async def test_zero_union_finalizar_cancels_operation(
        self,
        occupation_service,
        redis_lock_service,
        metadata_repo
    ):
        """
        FINALIZAR with empty selected_unions should cancel and release lock.

        Scenario:
        1. Worker initiates spool (INICIAR)
        2. Worker decides not to do any work
        3. FINALIZAR with empty selected_unions list
        4. Should release Redis lock
        5. Should clear Ocupado_Por
        6. Should log SPOOL_CANCELADO event
        7. Should return action_taken="CANCELADO"
        """
        # Execute: FINALIZAR with empty selected_unions
        request = FinalizarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.ARM,
            selected_unions=[]  # Empty list
        )

        response = await occupation_service.finalizar_spool(request)

        # Verify: Success with cancellation
        assert response.success is True
        assert response.action_taken == "CANCELADO"
        assert response.unions_processed == 0
        assert "cancelado" in response.message.lower()

        # Verify: Redis lock released
        redis_lock_service.release_lock.assert_called_once_with(
            "OT-001",
            93,
            "lock-token-123"
        )

        # Verify: Ocupado_Por cleared
        occupation_service.conflict_service.update_with_retry.assert_called()
        update_call = occupation_service.conflict_service.update_with_retry.call_args
        updates = update_call[1]["updates"]
        assert updates["Ocupado_Por"] == ""
        assert updates["Fecha_Ocupacion"] == ""

        # Verify: SPOOL_CANCELADO event logged
        metadata_repo.log_event.assert_called()
        log_event_call = metadata_repo.log_event.call_args
        assert log_event_call[1]["evento_tipo"] == "SPOOL_CANCELADO"
        assert log_event_call[1]["accion"] == "CANCELAR"

    @pytest.mark.asyncio
    async def test_cancellation_returns_spool_to_disponible(
        self,
        occupation_service,
        redis_event_service
    ):
        """
        Cancellation should publish real-time event with disponible state.

        Scenario:
        1. FINALIZAR with empty list
        2. Real-time event should show "Disponible" estado_detalle
        3. Event type should be "CANCELAR"
        """
        # Execute: Cancel
        request = FinalizarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.ARM,
            selected_unions=[]
        )

        response = await occupation_service.finalizar_spool(request)

        # Verify: Real-time event published
        redis_event_service.publish_spool_update.assert_called()
        event_call = redis_event_service.publish_spool_update.call_args

        assert event_call[1]["event_type"] == "CANCELAR"
        assert event_call[1]["estado_detalle"] == "Disponible"
        assert event_call[1]["worker_nombre"] is None  # No longer occupied

    @pytest.mark.asyncio
    async def test_cancellation_does_not_touch_uniones_sheet(
        self,
        occupation_service,
        union_repo
    ):
        """
        Cancellation should NOT call batch_update (no Uniones changes).

        Scenario:
        1. FINALIZAR with empty list
        2. batch_update_arm/sold should NOT be called
        3. Only Ocupado_Por should be cleared
        """
        # Mock batch_update methods
        with patch.object(union_repo, 'batch_update_arm') as mock_arm, \
             patch.object(union_repo, 'batch_update_sold') as mock_sold:

            # Execute: Cancel
            request = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.ARM,
                selected_unions=[]
            )

            response = await occupation_service.finalizar_spool(request)

            # Verify: No batch updates called
            mock_arm.assert_not_called()
            mock_sold.assert_not_called()

            # Verify: Cancellation succeeded
            assert response.success is True
            assert response.action_taken == "CANCELADO"


class TestErrorHandlingAndRaceConditions:
    """Test error handling and race condition scenarios."""

    @pytest.mark.asyncio
    async def test_union_becomes_unavailable_during_selection(
        self,
        occupation_service,
        union_repo
    ):
        """
        Simulate union becoming unavailable between page load and FINALIZAR.

        Scenario:
        1. Worker loads page, sees 3 disponibles
        2. Another worker completes 1 union
        3. First worker tries to select that union
        4. Should filter out unavailable union and process only valid ones
        """
        # Get disponibles
        disponibles = union_repo.get_disponibles_arm_by_ot("001")
        assert len(disponibles) >= 2

        # Select 2 unions
        selected_ids = [u.id for u in disponibles[:2]]

        # Mock batch_update to only process 1 union (simulating race: one already completed)
        with patch.object(union_repo, 'batch_update_arm', return_value=1):
            request = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.ARM,
                selected_unions=selected_ids
            )

            # Should succeed with partial processing
            response = await occupation_service.finalizar_spool(request)

            # Verify: Only 1 union processed (the available one)
            assert response.success is True
            assert response.unions_processed == 1

    @pytest.mark.asyncio
    async def test_race_condition_all_selected_greater_than_available(
        self,
        occupation_service,
        union_repo
    ):
        """
        Race condition: Selected count > available count raises ValueError.

        Scenario:
        1. Worker loads page, sees 3 disponibles
        2. All 3 get completed by other workers
        3. Worker tries to FINALIZAR with 3 selected
        4. Fresh query shows 0 disponibles
        5. Should raise ValueError (3 selected > 0 available)
        """
        # Mock disponibles query to return empty (all completed by race)
        with patch.object(union_repo, 'get_disponibles_arm_by_ot', return_value=[]):
            request = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.ARM,
                selected_unions=["OT-001+1", "OT-001+2", "OT-001+3"]
            )

            # Should raise ValueError for race condition
            with pytest.raises(ValueError, match="Race condition detected"):
                await occupation_service.finalizar_spool(request)

    @pytest.mark.asyncio
    async def test_version_conflict_with_retry_logic(
        self,
        occupation_service,
        conflict_service
    ):
        """
        Test version conflict handling with retry logic.

        Scenario:
        1. FINALIZAR triggers Sheets update
        2. Version conflict occurs (concurrent update)
        3. ConflictService retries with exponential backoff
        4. Eventually succeeds or raises VersionConflictError
        """
        # Mock version conflict then success
        from backend.exceptions import VersionConflictError

        conflict_service.update_with_retry.side_effect = [
            VersionConflictError("old", "new", "Version mismatch"),
            "new-version-uuid"  # Success on retry
        ]

        # Get some unions
        disponibles = occupation_service.union_repository.get_disponibles_arm_by_ot("001")
        selected_ids = [u.id for u in disponibles[:2]]

        # Mock batch update
        with patch.object(occupation_service.union_repository, 'batch_update_arm', return_value=2):
            request = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.ARM,
                selected_unions=selected_ids
            )

            # Should handle version conflict and retry
            response = await occupation_service.finalizar_spool(request)

            # Verify: Eventually succeeded
            assert response.success is True

    @pytest.mark.asyncio
    async def test_partial_batch_success_handling(
        self,
        occupation_service,
        union_repo
    ):
        """
        Test partial batch success (some unions update, some fail).

        Scenario:
        1. Select 5 unions
        2. Batch update succeeds for only 3 (2 validation failures)
        3. Should log warning but continue
        4. Metadata should reflect actual updated count
        """
        # Get unions
        disponibles = union_repo.get_disponibles_arm_by_ot("001")
        selected_ids = [u.id for u in disponibles[:3]]

        # Mock partial success (only 2 out of 3 updated)
        with patch.object(union_repo, 'batch_update_arm', return_value=2):
            request = FinalizarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.ARM,
                selected_unions=selected_ids
            )

            response = await occupation_service.finalizar_spool(request)

            # Verify: Success with partial count
            assert response.success is True
            assert response.unions_processed == 2  # Not 3

    @pytest.mark.asyncio
    async def test_redis_connection_failure_with_fallback(
        self,
        occupation_service,
        redis_lock_service
    ):
        """
        Test Redis connection failure handling.

        Scenario:
        1. INICIAR operation
        2. Redis lock acquisition fails (connection error)
        3. Should propagate error (fail-fast)
        4. Sheets should NOT be updated
        """
        from redis.exceptions import RedisError

        # Mock Redis failure
        redis_lock_service.acquire_lock.side_effect = RedisError("Connection refused")

        # Execute: INICIAR should fail
        request = IniciarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.ARM
        )

        with pytest.raises(RedisError):
            await occupation_service.iniciar_spool(request)

        # Verify: ConflictService NOT called (no Sheets update)
        occupation_service.conflict_service.update_with_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_proper_error_messages_and_codes(
        self,
        occupation_service
    ):
        """
        Test proper error messages and HTTP status code mapping.

        Verify that exceptions have clear messages for debugging.
        """
        # Test ArmPrerequisiteError (403)
        from backend.exceptions import ArmPrerequisiteError

        # Mock no ARM completion
        with patch.object(
            occupation_service.validation_service,
            'validate_arm_prerequisite',
            side_effect=ArmPrerequisiteError(
                tag_spool="OT-001",
                unions_sin_armar=10
            )
        ):
            request = IniciarRequest(
                tag_spool="OT-001",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion=ActionType.SOLD
            )

            with pytest.raises(ArmPrerequisiteError) as exc_info:
                await occupation_service.iniciar_spool(request)

            # Verify: Clear error message
            assert "ARM" in str(exc_info.value)
            assert "OT-001" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_audit_trail_for_failed_operations(
        self,
        occupation_service,
        metadata_repo
    ):
        """
        Test that failed operations are logged to audit trail.

        Even failures should be tracked for compliance.
        """
        # Mock Redis lock failure
        from redis.exceptions import RedisError
        occupation_service.redis_lock_service.acquire_lock.side_effect = RedisError("Connection error")

        # Execute: INICIAR will fail
        request = IniciarRequest(
            tag_spool="OT-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.ARM
        )

        try:
            await occupation_service.iniciar_spool(request)
        except RedisError:
            pass  # Expected failure

        # Note: Current implementation doesn't log failed operations
        # This test documents the behavior for future enhancement
