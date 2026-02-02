"""
Unit tests for ValidationService v4.0 features (ARM prerequisite validation).

Tests:
- validate_arm_prerequisite with various scenarios
- INICIAR SOLD with validation failure
- SOLD disponibles filtering
- SOLD completion with mixed union types
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from backend.services.validation_service import ValidationService
from backend.exceptions import ArmPrerequisiteError
from backend.models.union import Union


class TestArmPrerequisiteValidation:
    """Test ARM prerequisite validation for SOLD operations."""

    @pytest.fixture
    def union_repository(self):
        """Mock UnionRepository."""
        return Mock()

    @pytest.fixture
    def validation_service(self, union_repository):
        """Create ValidationService with mocked dependencies."""
        return ValidationService(
            role_service=None,
            union_repository=union_repository
        )

    def test_validate_arm_prerequisite_no_unions(self, validation_service, union_repository):
        """Test validation fails when no ARM unions completed."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # No unions for this OT
        union_repository.get_by_ot.return_value = []

        # Act & Assert
        with pytest.raises(ArmPrerequisiteError) as exc_info:
            validation_service.validate_arm_prerequisite(tag_spool, ot)

        assert exc_info.value.data["tag_spool"] == tag_spool
        assert exc_info.value.data["unions_sin_armar"] == 0
        assert "Cannot start SOLD" in str(exc_info.value)

    def test_validate_arm_prerequisite_no_arm_completed(self, validation_service, union_repository):
        """Test validation fails when unions exist but none ARM-completed."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # Create unions without ARM completion (arm_fecha_fin is None)
        unions = [
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),
        ]
        union_repository.get_by_ot.return_value = unions

        # Act & Assert
        with pytest.raises(ArmPrerequisiteError) as exc_info:
            validation_service.validate_arm_prerequisite(tag_spool, ot)

        assert exc_info.value.data["tag_spool"] == tag_spool
        assert exc_info.value.data["unions_sin_armar"] == 3
        assert "Cannot start SOLD" in str(exc_info.value)

    def test_validate_arm_prerequisite_one_arm_completed(self, validation_service, union_repository):
        """Test validation passes with at least one ARM-completed union."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # Create unions with at least one ARM-completed
        unions = [
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=None),  # ARM done
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),  # ARM pending
            Mock(arm_fecha_fin=None, sol_fecha_fin=None),  # ARM pending
        ]
        union_repository.get_by_ot.return_value = unions

        # Act
        result = validation_service.validate_arm_prerequisite(tag_spool, ot)

        # Assert
        assert result["valid"] is True
        assert result["unions_armadas"] == 1

    def test_validate_arm_prerequisite_all_arm_completed(self, validation_service, union_repository):
        """Test validation passes when all unions ARM-completed."""
        # Arrange
        tag_spool = "OT-123"
        ot = "123"

        # Create unions all ARM-completed
        unions = [
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=None),
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=None),
            Mock(arm_fecha_fin=datetime(2026, 2, 1), sol_fecha_fin=datetime(2026, 2, 2)),
        ]
        union_repository.get_by_ot.return_value = unions

        # Act
        result = validation_service.validate_arm_prerequisite(tag_spool, ot)

        # Assert
        assert result["valid"] is True
        assert result["unions_armadas"] == 3

    def test_validate_arm_prerequisite_no_repository(self, validation_service):
        """Test validation fails gracefully when UnionRepository not configured."""
        # Arrange
        validation_service.union_repository = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            validation_service.validate_arm_prerequisite("OT-123", "123")

        assert "UnionRepository not configured" in str(exc_info.value)


class TestSOLDDisponiblesFiltering:
    """Test SOLD disponibles filtering to only show ARM-completed unions."""

    @pytest.fixture
    def union_repository(self):
        """Create actual UnionRepository with mocked sheets."""
        from backend.repositories.union_repository import UnionRepository
        from backend.repositories.sheets_repository import SheetsRepository

        sheets_repo = Mock(spec=SheetsRepository)
        return UnionRepository(sheets_repo)

    def test_get_disponibles_sold_filters_arm_complete(self, union_repository):
        """Test get_disponibles_sold_by_ot only returns ARM-completed unions."""
        # Arrange
        ot = "123"

        # Mock union data with mixed ARM completion
        unions = [
            Mock(
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM complete
                sol_fecha_fin=None,  # SOLD pending
                tipo_union="BW"
            ),
            Mock(
                arm_fecha_fin=None,  # ARM pending
                sol_fecha_fin=None,
                tipo_union="BW"
            ),
            Mock(
                arm_fecha_fin=datetime(2026, 2, 1),  # ARM complete
                sol_fecha_fin=datetime(2026, 2, 2),  # SOLD complete
                tipo_union="BW"
            ),
        ]

        # Mock get_by_ot to return all unions
        union_repository.get_by_ot = Mock(return_value=unions)

        # Act
        disponibles = union_repository.get_disponibles_sold_by_ot(ot)

        # Assert
        # Only first union should be returned (ARM complete, SOLD pending)
        assert len(disponibles) == 1
        assert disponibles[0].arm_fecha_fin is not None
        assert disponibles[0].sol_fecha_fin is None


class TestSOLDCompletionLogic:
    """Test SOLD completion logic with mixed union types."""

    def test_sold_completion_counts_only_required_types(self):
        """Test SOLD COMPLETAR only counts BW/BR/SO/FILL/LET unions."""
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Verify constant includes expected types
        assert 'BW' in SOLD_REQUIRED_TYPES
        assert 'BR' in SOLD_REQUIRED_TYPES
        assert 'SO' in SOLD_REQUIRED_TYPES
        assert 'FILL' in SOLD_REQUIRED_TYPES
        assert 'LET' in SOLD_REQUIRED_TYPES
        assert 'FW' not in SOLD_REQUIRED_TYPES  # FW is ARM-only

    def test_sold_disponibles_filtering_by_type(self):
        """Test filtering disponibles to SOLD-required types only."""
        from backend.services.occupation_service import SOLD_REQUIRED_TYPES

        # Simulate disponibles list with mixed types
        all_disponibles = [
            Mock(tipo_union='BW'),  # SOLD-required
            Mock(tipo_union='FW'),  # ARM-only (should filter out)
            Mock(tipo_union='BR'),  # SOLD-required
            Mock(tipo_union='FW'),  # ARM-only (should filter out)
            Mock(tipo_union='SO'),  # SOLD-required
        ]

        # Filter logic (from occupation_service.finalizar_spool)
        sold_disponibles = [
            u for u in all_disponibles
            if u.tipo_union in SOLD_REQUIRED_TYPES
        ]

        # Assert
        assert len(sold_disponibles) == 3  # Only BW, BR, SO
        assert all(u.tipo_union in SOLD_REQUIRED_TYPES for u in sold_disponibles)
        assert not any(u.tipo_union == 'FW' for u in sold_disponibles)

    def test_determine_action_with_mixed_types(self):
        """Test _determine_action with correct total for mixed types."""
        from backend.services.occupation_service import OccupationService

        # Create service (dependencies not needed for this test)
        service = OccupationService(
            redis_lock_service=Mock(),
            sheets_repository=Mock(),
            metadata_repository=Mock(),
            conflict_service=Mock(),
            redis_event_service=Mock()
        )

        # Test COMPLETAR when all SOLD-required selected
        # Total of 3 SOLD-required unions (FW excluded)
        action = service._determine_action(
            selected_count=3,
            total_available=3,
            operacion="SOLD"
        )
        assert action == "COMPLETAR"

        # Test PAUSAR when partial SOLD-required selected
        action = service._determine_action(
            selected_count=2,
            total_available=3,
            operacion="SOLD"
        )
        assert action == "PAUSAR"

    def test_determine_action_race_condition(self):
        """Test _determine_action raises ValueError on race condition."""
        from backend.services.occupation_service import OccupationService

        service = OccupationService(
            redis_lock_service=Mock(),
            sheets_repository=Mock(),
            metadata_repository=Mock(),
            conflict_service=Mock(),
            redis_event_service=Mock()
        )

        # Race condition: selected > available
        with pytest.raises(ValueError) as exc_info:
            service._determine_action(
                selected_count=5,
                total_available=3,
                operacion="SOLD"
            )

        assert "Race condition" in str(exc_info.value)


class TestIniciarSoldValidation:
    """Test INICIAR SOLD with ARM prerequisite validation."""

    @pytest.fixture
    def mocked_services(self):
        """Create mocked service dependencies."""
        from backend.repositories.sheets_repository import SheetsRepository
        from unittest.mock import AsyncMock

        redis_lock = Mock()
        redis_lock.acquire_lock = AsyncMock(return_value="lock-token-123")
        redis_lock.lazy_cleanup_one_abandoned_lock = AsyncMock()

        sheets_repo = Mock(spec=SheetsRepository)
        metadata_repo = Mock()

        conflict_service = Mock()
        conflict_service.update_with_retry = AsyncMock(return_value="version-uuid")

        redis_event = Mock()
        redis_event.publish_spool_update = AsyncMock()

        union_repo = Mock()
        validation_service = Mock()

        return {
            "redis_lock": redis_lock,
            "sheets_repo": sheets_repo,
            "metadata_repo": metadata_repo,
            "conflict_service": conflict_service,
            "redis_event": redis_event,
            "union_repo": union_repo,
            "validation_service": validation_service
        }

    @pytest.mark.asyncio
    async def test_iniciar_sold_without_arm_returns_403(self, mocked_services):
        """Test INICIAR SOLD fails with 403 when no ARM unions completed."""
        from backend.services.occupation_service import OccupationService
        from backend.models.occupation import IniciarRequest
        from backend.models.enums import ActionType

        # Create service with validation
        service = OccupationService(
            redis_lock_service=mocked_services["redis_lock"],
            sheets_repository=mocked_services["sheets_repo"],
            metadata_repository=mocked_services["metadata_repo"],
            conflict_service=mocked_services["conflict_service"],
            redis_event_service=mocked_services["redis_event"],
            union_repository=mocked_services["union_repo"],
            validation_service=mocked_services["validation_service"]
        )

        # Mock spool exists with materials
        mock_spool = Mock()
        mock_spool.fecha_materiales = "01-02-2026"
        mock_spool.ot = "123"
        mocked_services["sheets_repo"].get_spool_by_tag.return_value = mock_spool

        # Mock validation to raise ArmPrerequisiteError
        mocked_services["validation_service"].validate_arm_prerequisite.side_effect = \
            ArmPrerequisiteError(tag_spool="OT-123", unions_sin_armar=3)

        # Create request
        request = IniciarRequest(
            tag_spool="OT-123",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.SOLD
        )

        # Act & Assert
        with pytest.raises(ArmPrerequisiteError) as exc_info:
            await service.iniciar_spool(request)

        # Verify validation was called
        mocked_services["validation_service"].validate_arm_prerequisite.assert_called_once_with(
            tag_spool="OT-123",
            ot="123"
        )

        # Verify lock was NOT acquired (fail early)
        mocked_services["redis_lock"].acquire_lock.assert_not_called()

        assert "Cannot start SOLD" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_iniciar_sold_with_arm_succeeds(self, mocked_services):
        """Test INICIAR SOLD succeeds when ARM prerequisite satisfied."""
        from backend.services.occupation_service import OccupationService
        from backend.models.occupation import IniciarRequest
        from backend.models.enums import ActionType

        # Create service with validation
        service = OccupationService(
            redis_lock_service=mocked_services["redis_lock"],
            sheets_repository=mocked_services["sheets_repo"],
            metadata_repository=mocked_services["metadata_repo"],
            conflict_service=mocked_services["conflict_service"],
            redis_event_service=mocked_services["redis_event"],
            union_repository=mocked_services["union_repo"],
            validation_service=mocked_services["validation_service"]
        )

        # Mock spool exists with materials
        mock_spool = Mock()
        mock_spool.fecha_materiales = "01-02-2026"
        mock_spool.ot = "123"
        mocked_services["sheets_repo"].get_spool_by_tag.return_value = mock_spool

        # Mock validation passes
        mocked_services["validation_service"].validate_arm_prerequisite.return_value = {
            "valid": True,
            "unions_armadas": 2
        }

        # Create request
        request = IniciarRequest(
            tag_spool="OT-123",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.SOLD
        )

        # Act
        response = await service.iniciar_spool(request)

        # Assert
        assert response.success is True
        assert "iniciado" in response.message.lower()

        # Verify validation was called
        mocked_services["validation_service"].validate_arm_prerequisite.assert_called_once()

        # Verify lock was acquired (validation passed)
        mocked_services["redis_lock"].acquire_lock.assert_called_once()

    @pytest.mark.asyncio
    async def test_iniciar_arm_skips_validation(self, mocked_services):
        """Test INICIAR ARM does not trigger ARM prerequisite validation."""
        from backend.services.occupation_service import OccupationService
        from backend.models.occupation import IniciarRequest
        from backend.models.enums import ActionType

        # Create service with validation
        service = OccupationService(
            redis_lock_service=mocked_services["redis_lock"],
            sheets_repository=mocked_services["sheets_repo"],
            metadata_repository=mocked_services["metadata_repo"],
            conflict_service=mocked_services["conflict_service"],
            redis_event_service=mocked_services["redis_event"],
            union_repository=mocked_services["union_repo"],
            validation_service=mocked_services["validation_service"]
        )

        # Mock spool exists with materials
        mock_spool = Mock()
        mock_spool.fecha_materiales = "01-02-2026"
        mock_spool.ot = "123"
        mocked_services["sheets_repo"].get_spool_by_tag.return_value = mock_spool

        # Create ARM request (not SOLD)
        request = IniciarRequest(
            tag_spool="OT-123",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion=ActionType.ARM
        )

        # Act
        response = await service.iniciar_spool(request)

        # Assert
        assert response.success is True

        # Verify validation was NOT called (ARM doesn't need it)
        mocked_services["validation_service"].validate_arm_prerequisite.assert_not_called()
