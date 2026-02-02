"""
Unit tests for Metrología Auto-Transition feature.

Tests:
- should_trigger_metrologia() detection logic
- FW-only spools (ARM-only unions)
- Mixed spools (FW + SOLD-required unions)
- State machine integration via StateService
- Metadata event logging
- API response with metrologia_triggered flag
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from backend.services.occupation_service import OccupationService
from backend.services.state_service import StateService
from backend.models.union import Union
from backend.models.enums import EventoTipo
from backend.exceptions import SpoolNoEncontradoError


class TestShouldTriggerMetrologia:
    """Tests for should_trigger_metrologia() detection logic."""

    def test_trigger_with_all_fw_unions_arm_completed(self):
        """Should trigger when all FW unions have ARM_FECHA_FIN != NULL."""
        # Setup mocks
        occupation_service = self._create_occupation_service()

        # Mock unions: All FW, all ARM'd
        unions = [
            Union(
                id="OT-123+1",
                tag_spool="TEST-01",
                ot="123",
                n_union=1,
                dn_union=4.0,
                tipo_union="FW",  # ARM-only union
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # COMPLETED
                arm_worker="MR(93)",
                sol_fecha_inicio=None,
                sol_fecha_fin=None,
                sol_worker=None,
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por=None,
                fecha_modificacion=None
            ),
            Union(
                id="OT-123+2",
                tag_spool="TEST-01",
                ot="123",
                n_union=2,
                dn_union=4.0,
                tipo_union="FW",  # ARM-only union
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # COMPLETED
                arm_worker="MR(93)",
                sol_fecha_inicio=None,
                sol_fecha_fin=None,
                sol_worker=None,
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por=None,
                fecha_modificacion=None
            )
        ]

        occupation_service.union_repository.get_by_spool.return_value = unions

        # Act
        result = occupation_service.should_trigger_metrologia("TEST-01")

        # Assert
        assert result is True
        occupation_service.union_repository.get_by_spool.assert_called_once_with("TEST-01")

    def test_trigger_with_all_sold_required_unions_completed(self):
        """Should trigger when all SOLD-required unions have SOL_FECHA_FIN != NULL."""
        # Setup mocks
        occupation_service = self._create_occupation_service()

        # Mock unions: All BW (SOLD-required), all SOLD'd
        unions = [
            Union(
                id="OT-123+1",
                tag_spool="TEST-01",
                ot="123",
                n_union=1,
                dn_union=6.0,
                tipo_union="BW",  # SOLD-required union
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM completed
                arm_worker="MR(93)",
                sol_fecha_inicio=datetime(2026, 2, 1),
                sol_fecha_fin=datetime(2026, 2, 1),  # SOLD COMPLETED
                sol_worker="JP(94)",
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por="JP(94)",
                fecha_modificacion=datetime(2026, 2, 1)
            ),
            Union(
                id="OT-123+2",
                tag_spool="TEST-01",
                ot="123",
                n_union=2,
                dn_union=8.0,
                tipo_union="BR",  # SOLD-required union
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM completed
                arm_worker="MR(93)",
                sol_fecha_inicio=datetime(2026, 2, 1),
                sol_fecha_fin=datetime(2026, 2, 1),  # SOLD COMPLETED
                sol_worker="JP(94)",
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por="JP(94)",
                fecha_modificacion=datetime(2026, 2, 1)
            )
        ]

        occupation_service.union_repository.get_by_spool.return_value = unions

        # Act
        result = occupation_service.should_trigger_metrologia("TEST-01")

        # Assert
        assert result is True

    def test_trigger_with_mixed_spool_all_complete(self):
        """Should trigger when mixed spool (FW + BW) has all work complete."""
        # Setup mocks
        occupation_service = self._create_occupation_service()

        # Mock unions: Mix of FW (ARM-only) and BW (SOLD-required), all complete
        unions = [
            Union(
                id="OT-123+1",
                tag_spool="TEST-01",
                ot="123",
                n_union=1,
                dn_union=4.0,
                tipo_union="FW",  # ARM-only
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM COMPLETED
                arm_worker="MR(93)",
                sol_fecha_inicio=None,
                sol_fecha_fin=None,  # No SOLD needed for FW
                sol_worker=None,
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por=None,
                fecha_modificacion=None
            ),
            Union(
                id="OT-123+2",
                tag_spool="TEST-01",
                ot="123",
                n_union=2,
                dn_union=6.0,
                tipo_union="BW",  # SOLD-required
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM completed
                arm_worker="MR(93)",
                sol_fecha_inicio=datetime(2026, 2, 1),
                sol_fecha_fin=datetime(2026, 2, 1),  # SOLD COMPLETED
                sol_worker="JP(94)",
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por="JP(94)",
                fecha_modificacion=datetime(2026, 2, 1)
            )
        ]

        occupation_service.union_repository.get_by_spool.return_value = unions

        # Act
        result = occupation_service.should_trigger_metrologia("TEST-01")

        # Assert
        assert result is True

    def test_no_trigger_when_fw_union_arm_incomplete(self):
        """Should NOT trigger when FW union has ARM_FECHA_FIN = NULL."""
        # Setup mocks
        occupation_service = self._create_occupation_service()

        # Mock unions: FW with ARM incomplete
        unions = [
            Union(
                id="OT-123+1",
                tag_spool="TEST-01",
                ot="123",
                n_union=1,
                dn_union=4.0,
                tipo_union="FW",
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=None,  # ARM NOT COMPLETE
                arm_worker="MR(93)",
                sol_fecha_inicio=None,
                sol_fecha_fin=None,
                sol_worker=None,
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por=None,
                fecha_modificacion=None
            )
        ]

        occupation_service.union_repository.get_by_spool.return_value = unions

        # Act
        result = occupation_service.should_trigger_metrologia("TEST-01")

        # Assert
        assert result is False

    def test_no_trigger_when_sold_required_union_sold_incomplete(self):
        """Should NOT trigger when SOLD-required union has SOL_FECHA_FIN = NULL."""
        # Setup mocks
        occupation_service = self._create_occupation_service()

        # Mock unions: BW with ARM complete but SOLD incomplete
        unions = [
            Union(
                id="OT-123+1",
                tag_spool="TEST-01",
                ot="123",
                n_union=1,
                dn_union=6.0,
                tipo_union="BW",  # SOLD-required
                arm_fecha_inicio=datetime(2026, 2, 1),
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM complete
                arm_worker="MR(93)",
                sol_fecha_inicio=datetime(2026, 2, 1),
                sol_fecha_fin=None,  # SOLD NOT COMPLETE
                sol_worker="JP(94)",
                ndt_fecha=None,
                ndt_status=None,
                version="v1",
                creado_por="MR(93)",
                fecha_creacion=datetime(2026, 2, 1),
                modificado_por="JP(94)",
                fecha_modificacion=datetime(2026, 2, 1)
            )
        ]

        occupation_service.union_repository.get_by_spool.return_value = unions

        # Act
        result = occupation_service.should_trigger_metrologia("TEST-01")

        # Assert
        assert result is False

    def test_no_trigger_when_no_unions_found(self):
        """Should NOT trigger when no unions found for spool."""
        # Setup mocks
        occupation_service = self._create_occupation_service()

        # Mock empty unions list
        occupation_service.union_repository.get_by_spool.return_value = []

        # Act
        result = occupation_service.should_trigger_metrologia("TEST-01")

        # Assert
        assert result is False

    def test_raises_error_when_union_repository_not_configured(self):
        """Should raise ValueError when UnionRepository not configured."""
        # Setup mocks WITHOUT union_repository
        occupation_service = OccupationService(
            redis_lock_service=Mock(),
            sheets_repository=Mock(),
            metadata_repository=Mock(),
            conflict_service=Mock(),
            redis_event_service=Mock(),
            union_repository=None  # NOT configured
        )

        # Act & Assert
        with pytest.raises(ValueError, match="UnionRepository not configured"):
            occupation_service.should_trigger_metrologia("TEST-01")

    def _create_occupation_service(self):
        """Helper to create OccupationService with mocked dependencies."""
        return OccupationService(
            redis_lock_service=Mock(),
            sheets_repository=Mock(),
            metadata_repository=Mock(),
            conflict_service=Mock(),
            redis_event_service=Mock(),
            union_repository=Mock()
        )


class TestStateMachinseIntegration:
    """Tests for StateService.trigger_metrologia_transition()."""

    @pytest.mark.asyncio
    async def test_trigger_metrologia_transition_success(self):
        """Should successfully transition to metrología queue."""
        # Setup mocks
        sheets_repo = Mock()
        metadata_repo = Mock()
        redis_event_service = AsyncMock()
        occupation_service = Mock()

        # Mock spool exists
        spool = MagicMock()
        spool.tag_spool = "TEST-01"
        sheets_repo.get_spool_by_tag.return_value = spool

        # Mock find_row_by_column_value
        sheets_repo.find_row_by_column_value.return_value = 10

        # Create StateService
        state_service = StateService(
            occupation_service=occupation_service,
            sheets_repository=sheets_repo,
            metadata_repository=metadata_repo,
            redis_event_service=redis_event_service
        )

        # Mock MetrologiaStateMachine (imported inside function)
        with patch('backend.domain.state_machines.metrologia_machine.MetrologiaStateMachine') as MockMetrologiaMachine:
            mock_machine = Mock()
            mock_machine.activate_initial_state = AsyncMock()
            mock_machine.get_state_id = Mock(return_value="pendiente")  # Non-async method
            MockMetrologiaMachine.return_value = mock_machine

            # Act
            result = await state_service.trigger_metrologia_transition("TEST-01")

            # Assert
            assert result == "pendiente"  # Metrología initial state
            sheets_repo.update_cell_by_column_name.assert_called_once()
            redis_event_service.publish_spool_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_metrologia_transition_spool_not_found(self):
        """Should raise SpoolNoEncontradoError when spool doesn't exist."""
        # Setup mocks
        sheets_repo = Mock()
        sheets_repo.get_spool_by_tag.return_value = None  # Spool not found

        state_service = StateService(
            occupation_service=Mock(),
            sheets_repository=sheets_repo,
            metadata_repository=Mock(),
            redis_event_service=AsyncMock()
        )

        # Act & Assert
        with pytest.raises(SpoolNoEncontradoError):
            await state_service.trigger_metrologia_transition("TEST-01")

    @pytest.mark.asyncio
    async def test_trigger_metrologia_transition_already_in_queue(self):
        """Should skip transition if already in non-pendiente state."""
        # Setup mocks
        sheets_repo = Mock()
        metadata_repo = Mock()
        redis_event_service = AsyncMock()

        spool = MagicMock()
        spool.tag_spool = "TEST-01"
        sheets_repo.get_spool_by_tag.return_value = spool

        # Mock find_row_by_column_value
        sheets_repo.find_row_by_column_value.return_value = 10

        state_service = StateService(
            occupation_service=Mock(),
            sheets_repository=sheets_repo,
            metadata_repository=metadata_repo,
            redis_event_service=redis_event_service
        )

        # Mock MetrologiaStateMachine already in aprobado state
        with patch('backend.domain.state_machines.metrologia_machine.MetrologiaStateMachine') as MockMetrologiaMachine:
            mock_machine = AsyncMock()
            mock_machine.activate_initial_state = AsyncMock()
            mock_machine.get_state_id.return_value = "aprobado"  # Already approved
            MockMetrologiaMachine.return_value = mock_machine

            # Act
            result = await state_service.trigger_metrologia_transition("TEST-01")

            # Assert
            # Should return None (transition skipped)
            assert result is None


class TestMetrologiaAutoTriggerInFinalizar:
    """Tests for metrología auto-trigger integration in finalizar_spool()."""

    @pytest.mark.asyncio
    async def test_finalizar_triggers_metrologia_on_completar(self):
        """Should trigger metrología when action_taken is COMPLETAR and all work complete."""
        # This test would require full integration test with finalizar_spool()
        # Simplified mock-based test here

        # Setup
        occupation_service = self._create_occupation_service_with_mocks()

        # Mock should_trigger_metrologia returns True
        occupation_service.should_trigger_metrologia = Mock(return_value=True)

        # Mock StateService module import
        with patch('backend.services.state_service.StateService') as MockStateService:
            mock_state_service_instance = AsyncMock()
            mock_state_service_instance.trigger_metrologia_transition = AsyncMock(return_value="pendiente")
            MockStateService.return_value = mock_state_service_instance

            # Mock MetrologiaStateMachine to avoid import errors
            with patch('backend.domain.state_machines.metrologia_machine.MetrologiaStateMachine'):
                # Mock other dependencies for finalizar
                occupation_service.union_repository.get_disponibles_arm_by_ot.return_value = [
                    Mock(id="OT-123+1"),
                    Mock(id="OT-123+2")
                ]
                occupation_service.union_repository.batch_update_arm.return_value = 2

                # Create request
                from backend.models.occupation import FinalizarRequest
                from backend.models.enums import ActionType

                request = FinalizarRequest(
                    tag_spool="TEST-01",
                    worker_id=93,
                    worker_nombre="MR(93)",
                    operacion=ActionType.ARM,
                    selected_unions=["OT-123+1", "OT-123+2"]
                )

                # Act
                response = await occupation_service.finalizar_spool(request)

                # Assert
                assert response.success is True
                assert response.action_taken == "COMPLETAR"
                assert response.metrologia_triggered is True
                assert response.new_state == "pendiente"
                assert "Listo para metrología" in response.message

    @pytest.mark.asyncio
    async def test_finalizar_no_trigger_on_pausar(self):
        """Should NOT trigger metrología when action_taken is PAUSAR."""
        # Setup
        occupation_service = self._create_occupation_service_with_mocks()

        # Mock partial selection (PAUSAR)
        occupation_service.union_repository.get_disponibles_arm_by_ot.return_value = [
            Mock(id="OT-123+1"),
            Mock(id="OT-123+2"),
            Mock(id="OT-123+3")  # 3 available
        ]
        occupation_service.union_repository.batch_update_arm.return_value = 2

        # Create request (only 2 of 3 unions selected)
        from backend.models.occupation import FinalizarRequest
        from backend.models.enums import ActionType

        request = FinalizarRequest(
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.ARM,
            selected_unions=["OT-123+1", "OT-123+2"]  # Partial
        )

        # Act
        response = await occupation_service.finalizar_spool(request)

        # Assert
        assert response.success is True
        assert response.action_taken == "PAUSAR"
        assert response.metrologia_triggered is None  # Not triggered
        assert response.new_state is None

    def _create_occupation_service_with_mocks(self):
        """Helper to create fully mocked OccupationService."""
        redis_lock_service = AsyncMock()
        sheets_repository = Mock()
        metadata_repository = Mock()
        conflict_service = AsyncMock()
        redis_event_service = AsyncMock()
        union_repository = Mock()

        # Mock lock ownership
        redis_lock_service.get_lock_owner.return_value = (93, "lock-token-123")
        redis_lock_service.release_lock.return_value = True

        # Mock spool
        spool = MagicMock()
        spool.tag_spool = "TEST-01"
        spool.ot = "123"
        spool.fecha_materiales = "01-01-2026"
        sheets_repository.get_spool_by_tag.return_value = spool

        # Mock conflict service
        conflict_service.update_with_retry.return_value = "new-version"

        occupation_service = OccupationService(
            redis_lock_service=redis_lock_service,
            sheets_repository=sheets_repository,
            metadata_repository=metadata_repository,
            conflict_service=conflict_service,
            redis_event_service=redis_event_service,
            union_repository=union_repository
        )

        return occupation_service
