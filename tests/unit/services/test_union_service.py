"""
Unit tests for UnionService.

Tests:
- process_selection with valid unions (mock batch_update success)
- calcular_pulgadas with various decimal values
- build_eventos_metadata generates correct event structure
- Union validation and filtering logic
- Error handling for invalid union IDs
- All repository dependencies mocked
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid

from backend.services.union_service import UnionService, SOLD_REQUIRED_TYPES
from backend.models.union import Union
from backend.models.metadata import MetadataEvent, Accion
from backend.models.enums import EventoTipo
from backend.exceptions import SheetsConnectionError


@pytest.fixture
def mock_union_repo():
    """Mock UnionRepository."""
    return Mock()


@pytest.fixture
def mock_metadata_repo():
    """Mock MetadataRepository."""
    return Mock()


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository."""
    return Mock()


@pytest.fixture
def union_service(mock_union_repo, mock_metadata_repo, mock_sheets_repo):
    """Create UnionService with mocked dependencies."""
    return UnionService(
        union_repo=mock_union_repo,
        metadata_repo=mock_metadata_repo,
        sheets_repo=mock_sheets_repo
    )


@pytest.fixture
def sample_unions():
    """Create sample Union objects for testing."""
    return [
        Union(
            id="OT-123+1",
            ot="123",
            tag_spool="OT-123",
            n_union=1,
            dn_union=4.0,
            tipo_union="BW",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version=str(uuid.uuid4()),
            creado_por="MR(93)",
            fecha_creacion=datetime.now(),
            modificado_por=None,
            fecha_modificacion=None
        ),
        Union(
            id="OT-123+2",
            ot="123",
            tag_spool="OT-123",
            n_union=2,
            dn_union=6.5,
            tipo_union="BR",
            arm_fecha_inicio=None,
            arm_fecha_fin=None,
            arm_worker=None,
            sol_fecha_inicio=None,
            sol_fecha_fin=None,
            sol_worker=None,
            ndt_fecha=None,
            ndt_status=None,
            version=str(uuid.uuid4()),
            creado_por="MR(93)",
            fecha_creacion=datetime.now(),
            modificado_por=None,
            fecha_modificacion=None
        )
    ]


class TestCalcularPulgadas:
    """Tests for calcular_pulgadas method."""

    def test_sum_with_valid_unions(self, union_service, sample_unions):
        """Test pulgadas calculation with valid unions."""
        result = union_service.calcular_pulgadas(sample_unions)

        # 4.0 + 6.5 = 10.5 (1 decimal precision)
        assert result == 10.5
        assert isinstance(result, float)

    def test_empty_union_list(self, union_service):
        """Test pulgadas calculation with empty list."""
        result = union_service.calcular_pulgadas([])
        assert result == 0.0

    def test_single_union(self, union_service, sample_unions):
        """Test pulgadas calculation with single union."""
        result = union_service.calcular_pulgadas([sample_unions[0]])
        assert result == 4.0

    def test_decimal_precision(self, union_service):
        """Test 1 decimal precision rounding."""
        # Create unions with values that need rounding
        unions = [
            MagicMock(id="OT-123+1", dn_union=4.123),
            MagicMock(id="OT-123+2", dn_union=6.567)
        ]

        result = union_service.calcular_pulgadas(unions)

        # 4.123 + 6.567 = 10.690 -> rounds to 10.7
        assert result == 10.7

    def test_handle_none_values(self, union_service):
        """Test graceful handling of None DN_UNION values."""
        unions = [
            MagicMock(id="OT-123+1", dn_union=4.0),
            MagicMock(id="OT-123+2", dn_union=None),  # None value
            MagicMock(id="OT-123+3", dn_union=6.5)
        ]

        result = union_service.calcular_pulgadas(unions)

        # Should skip None and sum 4.0 + 6.5 = 10.5
        assert result == 10.5

    def test_handle_invalid_values(self, union_service):
        """Test graceful handling of invalid DN_UNION values."""
        unions = [
            MagicMock(id="OT-123+1", dn_union=4.0),
            MagicMock(id="OT-123+2", dn_union="invalid"),  # Invalid value
            MagicMock(id="OT-123+3", dn_union=6.5)
        ]

        result = union_service.calcular_pulgadas(unions)

        # Should skip invalid and sum 4.0 + 6.5 = 10.5
        assert result == 10.5


class TestBuildEventosMetadata:
    """Tests for build_eventos_metadata method."""

    def test_build_arm_events(self, union_service):
        """Test building ARM metadata events."""
        union_ids = ["OT-123+1", "OT-123+2"]

        with patch('backend.utils.date_formatter.now_chile') as mock_now, \
             patch('backend.utils.date_formatter.today_chile') as mock_today, \
             patch('backend.utils.date_formatter.format_date_for_sheets') as mock_format:

            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)
            mock_today.return_value = datetime(2026, 2, 2).date()
            mock_format.return_value = "02-02-2026"

            eventos = union_service.build_eventos_metadata(
                tag_spool="OT-123",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                union_ids=union_ids,
                pulgadas=10.5
            )

        # Should create 1 batch event + 2 granular events = 3 total
        assert len(eventos) == 3

        # All events should be MetadataEvent instances
        assert all(isinstance(e, MetadataEvent) for e in eventos)

        # First event should be batch (N_UNION=None)
        batch_event = eventos[0]
        assert batch_event.n_union is None
        assert batch_event.evento_tipo == EventoTipo.UNION_ARM_REGISTRADA
        assert batch_event.operacion == "ARM"
        assert batch_event.accion == Accion.COMPLETAR
        assert '"union_count": 2' in batch_event.metadata_json
        assert '"pulgadas": 10.5' in batch_event.metadata_json

        # Next 2 events should be granular (N_UNION=1, N_UNION=2)
        assert eventos[1].n_union == 1
        assert eventos[2].n_union == 2
        assert all(e.evento_tipo == EventoTipo.UNION_ARM_REGISTRADA for e in eventos[1:])

    def test_build_sold_events(self, union_service):
        """Test building SOLD metadata events."""
        union_ids = ["OT-123+5", "OT-123+6", "OT-123+7"]

        with patch('backend.utils.date_formatter.now_chile') as mock_now, \
             patch('backend.utils.date_formatter.today_chile') as mock_today, \
             patch('backend.utils.date_formatter.format_date_for_sheets') as mock_format:

            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)
            mock_today.return_value = datetime(2026, 2, 2).date()
            mock_format.return_value = "02-02-2026"

            eventos = union_service.build_eventos_metadata(
                tag_spool="OT-123",
                worker_id=95,
                worker_nombre="MG(95)",
                operacion="SOLD",
                union_ids=union_ids,
                pulgadas=18.5
            )

        # Should create 1 batch event + 3 granular events = 4 total
        assert len(eventos) == 4

        # First event should be batch
        batch_event = eventos[0]
        assert batch_event.n_union is None
        assert batch_event.evento_tipo == EventoTipo.UNION_SOLD_REGISTRADA
        assert batch_event.operacion == "SOLD"

        # Granular events should have correct N_UNION
        assert eventos[1].n_union == 5
        assert eventos[2].n_union == 6
        assert eventos[3].n_union == 7

    def test_event_structure(self, union_service):
        """Test event structure contains all required fields."""
        with patch('backend.utils.date_formatter.now_chile') as mock_now, \
             patch('backend.utils.date_formatter.today_chile') as mock_today, \
             patch('backend.utils.date_formatter.format_date_for_sheets') as mock_format:

            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)
            mock_today.return_value = datetime(2026, 2, 2).date()
            mock_format.return_value = "02-02-2026"

            eventos = union_service.build_eventos_metadata(
                tag_spool="OT-123",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                union_ids=["OT-123+1"],
                pulgadas=4.0
            )

        event = eventos[0]

        # Check all required fields
        assert event.id is not None
        assert event.timestamp == datetime(2026, 2, 2, 14, 30, 0)
        assert event.tag_spool == "OT-123"
        assert event.worker_id == 93
        assert event.worker_nombre == "MR(93)"
        assert event.operacion == "ARM"
        assert event.accion == Accion.COMPLETAR
        assert event.fecha_operacion == "02-02-2026"
        assert event.metadata_json is not None

    def test_invalid_union_id_format(self, union_service):
        """Test handling of invalid union_id format."""
        with patch('backend.utils.date_formatter.now_chile') as mock_now, \
             patch('backend.utils.date_formatter.today_chile') as mock_today, \
             patch('backend.utils.date_formatter.format_date_for_sheets') as mock_format:

            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)
            mock_today.return_value = datetime(2026, 2, 2).date()
            mock_format.return_value = "02-02-2026"

            # Include valid and invalid union_ids
            union_ids = ["OT-123+1", "INVALID", "OT-123+2"]

            eventos = union_service.build_eventos_metadata(
                tag_spool="OT-123",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                union_ids=union_ids,
                pulgadas=10.5
            )

        # Should create 1 batch + 2 granular (skip invalid)
        assert len(eventos) == 3
        assert eventos[1].n_union == 1
        assert eventos[2].n_union == 2


class TestValidateUnionOwnership:
    """Tests for validate_union_ownership method."""

    def test_same_ot(self, union_service, sample_unions):
        """Test validation passes when all unions have same OT."""
        result = union_service.validate_union_ownership(sample_unions)
        assert result is True

    def test_different_ots(self, union_service):
        """Test validation fails when unions have different OTs."""
        unions = [
            MagicMock(id="OT-123+1", ot="123"),
            MagicMock(id="OT-124+1", ot="124")  # Different OT
        ]

        result = union_service.validate_union_ownership(unions)
        assert result is False

    def test_empty_list(self, union_service):
        """Test validation passes for empty list."""
        result = union_service.validate_union_ownership([])
        assert result is True

    def test_single_union(self, union_service, sample_unions):
        """Test validation passes for single union."""
        result = union_service.validate_union_ownership([sample_unions[0]])
        assert result is True


class TestFilterAvailableUnions:
    """Tests for filter_available_unions method."""

    def test_arm_filter(self, union_service):
        """Test ARM filter returns only unions with arm_fecha_fin=None."""
        unions = [
            MagicMock(id="OT-123+1", arm_fecha_fin=None, tipo_union="BW"),
            MagicMock(id="OT-123+2", arm_fecha_fin=datetime.now(), tipo_union="BR"),
            MagicMock(id="OT-123+3", arm_fecha_fin=None, tipo_union="SO")
        ]

        result = union_service.filter_available_unions(unions, "ARM")

        assert len(result) == 2
        assert result[0].id == "OT-123+1"
        assert result[1].id == "OT-123+3"

    def test_sold_filter(self, union_service):
        """Test SOLD filter returns unions where ARM complete but SOLD not complete."""
        unions = [
            MagicMock(
                id="OT-123+1",
                tipo_union="BW",
                arm_fecha_fin=None,
                sol_fecha_fin=None
            ),  # ARM not done
            MagicMock(
                id="OT-123+2",
                tipo_union="BR",
                arm_fecha_fin=datetime.now(),
                sol_fecha_fin=None
            ),  # Available
            MagicMock(
                id="OT-123+3",
                tipo_union="SO",
                arm_fecha_fin=datetime.now(),
                sol_fecha_fin=datetime.now()
            )  # SOLD already done
        ]

        result = union_service.filter_available_unions(unions, "SOLD")

        assert len(result) == 1
        assert result[0].id == "OT-123+2"

    def test_fw_union_excluded_from_sold(self, union_service):
        """Test FW unions are excluded from SOLD filter (ARM-only)."""
        unions = [
            MagicMock(
                id="OT-123+1",
                tipo_union="FW",  # ARM-only type
                arm_fecha_fin=datetime.now(),
                sol_fecha_fin=None
            ),
            MagicMock(
                id="OT-123+2",
                tipo_union="BW",  # SOLD-required type
                arm_fecha_fin=datetime.now(),
                sol_fecha_fin=None
            )
        ]

        result = union_service.filter_available_unions(unions, "SOLD")

        # Only BW should be available, FW excluded
        assert len(result) == 1
        assert result[0].id == "OT-123+2"
        assert result[0].tipo_union == "BW"

    def test_empty_list(self, union_service):
        """Test filter returns empty list for empty input."""
        result = union_service.filter_available_unions([], "ARM")
        assert result == []


class TestGetSoldRequiredTypes:
    """Tests for get_sold_required_types method."""

    def test_returns_correct_types(self, union_service):
        """Test returns correct SOLD_REQUIRED_TYPES constant."""
        result = union_service.get_sold_required_types()

        assert result == ['BW', 'BR', 'SO', 'FILL', 'LET']
        assert 'FW' not in result

    def test_returns_copy(self, union_service):
        """Test returns copy to prevent modification of original."""
        result = union_service.get_sold_required_types()

        # Modify returned list
        result.append('FW')

        # Original should be unchanged
        assert union_service.get_sold_required_types() == ['BW', 'BR', 'SO', 'FILL', 'LET']
        assert SOLD_REQUIRED_TYPES == ['BW', 'BR', 'SO', 'FILL', 'LET']


class TestProcessSelection:
    """Tests for process_selection method."""

    def test_successful_arm_processing(
        self,
        union_service,
        mock_union_repo,
        mock_metadata_repo,
        sample_unions
    ):
        """Test successful ARM union processing."""
        # Setup mocks
        mock_union_repo.get_by_spool.return_value = sample_unions
        mock_union_repo.batch_update_arm.return_value = 2
        mock_metadata_repo.batch_log_events.return_value = None

        with patch('backend.utils.date_formatter.now_chile') as mock_now:
            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)

            result = union_service.process_selection(
                tag_spool="OT-123",
                union_ids=["OT-123+1", "OT-123+2"],
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

        # Verify batch_update_arm was called
        mock_union_repo.batch_update_arm.assert_called_once()

        # Verify metadata events were logged
        mock_metadata_repo.batch_log_events.assert_called_once()

        # Verify result structure
        assert result["union_count"] == 2
        assert result["action"] == "ARM_COMPLETAR"
        assert result["pulgadas"] == 10.5  # 4.0 + 6.5 = 10.5
        assert result["event_count"] == 3  # 1 batch + 2 granular

    def test_successful_sold_processing(
        self,
        union_service,
        mock_union_repo,
        mock_metadata_repo
    ):
        """Test successful SOLD union processing."""
        # Create unions with ARM complete
        unions = [
            MagicMock(
                id="OT-123+1",
                ot="123",
                tag_spool="OT-123",
                dn_union=4.0,
                tipo_union="BW",
                arm_fecha_fin=datetime.now(),
                sol_fecha_fin=None
            ),
            MagicMock(
                id="OT-123+2",
                ot="123",
                tag_spool="OT-123",
                dn_union=6.5,
                tipo_union="BR",
                arm_fecha_fin=datetime.now(),
                sol_fecha_fin=None
            )
        ]

        mock_union_repo.get_by_spool.return_value = unions
        mock_union_repo.batch_update_sold.return_value = 2
        mock_metadata_repo.batch_log_events.return_value = None

        with patch('backend.utils.date_formatter.now_chile') as mock_now:
            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)

            result = union_service.process_selection(
                tag_spool="OT-123",
                union_ids=["OT-123+1", "OT-123+2"],
                worker_id=95,
                worker_nombre="MG(95)",
                operacion="SOLD"
            )

        # Verify batch_update_sold was called
        mock_union_repo.batch_update_sold.assert_called_once()

        # Verify result
        assert result["action"] == "SOLD_COMPLETAR"

    def test_empty_union_ids(self, union_service):
        """Test error when union_ids is empty."""
        with pytest.raises(ValueError, match="union_ids cannot be empty"):
            union_service.process_selection(
                tag_spool="OT-123",
                union_ids=[],
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

    def test_union_ids_not_found(
        self,
        union_service,
        mock_union_repo,
        sample_unions
    ):
        """Test error when union IDs don't exist."""
        mock_union_repo.get_by_spool.return_value = sample_unions

        with pytest.raises(ValueError, match="Union IDs not found"):
            union_service.process_selection(
                tag_spool="OT-123",
                union_ids=["OT-123+99"],  # Non-existent ID
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

    def test_mixed_ot_ownership(
        self,
        union_service,
        mock_union_repo
    ):
        """Test error when unions belong to different OTs."""
        unions = [
            MagicMock(id="OT-123+1", ot="123", tag_spool="OT-123", dn_union=4.0),
            MagicMock(id="OT-124+1", ot="124", tag_spool="OT-124", dn_union=6.5)
        ]

        mock_union_repo.get_by_spool.return_value = unions

        with pytest.raises(ValueError, match="All unions must belong to the same OT"):
            union_service.process_selection(
                tag_spool="OT-123",
                union_ids=["OT-123+1", "OT-124+1"],
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

    def test_filters_unavailable_unions(
        self,
        union_service,
        mock_union_repo,
        mock_metadata_repo
    ):
        """Test that unavailable unions are filtered out."""
        unions = [
            MagicMock(
                id="OT-123+1",
                ot="123",
                tag_spool="OT-123",
                dn_union=4.0,
                arm_fecha_fin=None  # Available
            ),
            MagicMock(
                id="OT-123+2",
                ot="123",
                tag_spool="OT-123",
                dn_union=6.5,
                arm_fecha_fin=datetime.now()  # Not available
            )
        ]

        mock_union_repo.get_by_spool.return_value = unions
        mock_union_repo.batch_update_arm.return_value = 1
        mock_metadata_repo.batch_log_events.return_value = None

        with patch('backend.utils.date_formatter.now_chile') as mock_now:
            mock_now.return_value = datetime(2026, 2, 2, 14, 30, 0)

            result = union_service.process_selection(
                tag_spool="OT-123",
                union_ids=["OT-123+1", "OT-123+2"],
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM"
            )

        # Only 1 union should be processed (the available one)
        assert result["union_count"] == 1
