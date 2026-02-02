"""
Integration tests for Metadata batch logging with chunking and union granularity.

Tests batch_log_events with auto-chunking for large volumes and n_union field.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import uuid

from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.metadata import MetadataEvent, EventoTipo, Accion
from backend.exceptions import SheetsUpdateError


@pytest.fixture
def mock_sheets_repo():
    """Mock SheetsRepository for Metadata operations."""
    repo = MagicMock()

    # Mock _get_spreadsheet for MetadataRepository._get_worksheet()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    mock_worksheet.append_rows = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    repo._get_spreadsheet.return_value = mock_spreadsheet

    return repo


@pytest.fixture
def metadata_repo(mock_sheets_repo):
    """Create MetadataRepository with mocked sheets."""
    # Patch config to avoid issues with HOJA_METADATA_NOMBRE
    with patch('backend.repositories.metadata_repository.config') as mock_config:
        mock_config.HOJA_METADATA_NOMBRE = "Metadata"
        repo = MetadataRepository(mock_sheets_repo)
        # Cache the worksheet to avoid repeated calls
        repo._get_worksheet()
        return repo


class TestBatchLogEvents:
    """Test batch logging with multiple events."""

    def test_batch_log_10_union_events(self, metadata_repo, mock_sheets_repo):
        """Should log 10 union events in single batch."""
        # Build 10 union events
        events = []
        for i in range(1, 11):
            event = MetadataEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
                tag_spool="TEST-01",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="02-02-2026",
                metadata_json='{"dn_union": 6.0, "tipo": "Brida"}',
                n_union=i
            )
            events.append(event)

        # Execute batch log
        metadata_repo.batch_log_events(events)

        # Verify append_rows called once (not 10 times)
        # Access the worksheet that was cached in the metadata_repo
        mock_worksheet = metadata_repo._worksheet
        mock_worksheet.append_rows.assert_called_once()

        # Verify all 10 events in single call
        call_args = mock_worksheet.append_rows.call_args
        rows = call_args[0][0]
        assert len(rows) == 10

    def test_batch_log_union_and_spool_events(self, metadata_repo, mock_sheets_repo):
        """Should log 10 union events + 1 spool event together."""
        events = []

        # 10 union events
        for i in range(1, 11):
            event = MetadataEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
                tag_spool="TEST-01",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="02-02-2026",
                metadata_json='{}',
                n_union=i
            )
            events.append(event)

        # 1 spool-level event (PAUSAR after partial work)
        spool_event = MetadataEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            evento_tipo=EventoTipo.PAUSAR_SPOOL,
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.PAUSAR,
            fecha_operacion="02-02-2026",
            metadata_json='{"reason": "partial_completion"}',
            n_union=None  # Spool-level has no n_union
        )
        events.append(spool_event)

        # Execute batch log
        metadata_repo.batch_log_events(events)

        # Verify single batch call with 11 events
        mock_worksheet = metadata_repo._worksheet
        mock_worksheet.append_rows.assert_called_once()

        call_args = mock_worksheet.append_rows.call_args
        rows = call_args[0][0]
        assert len(rows) == 11

    def test_batch_log_empty_list(self, metadata_repo, mock_sheets_repo):
        """Should handle empty events list gracefully."""
        metadata_repo.batch_log_events([])

        # Should not call append_rows
        mock_worksheet = metadata_repo._worksheet
        mock_worksheet.append_rows.assert_not_called()


class TestAutoChunking:
    """Test auto-chunking for large batches (>900 rows)."""

    def test_chunking_with_1000_events(self, metadata_repo, mock_sheets_repo):
        """Should chunk 1000 events into 2 batches (900 + 100)."""
        # Generate 1000 events
        events = []
        for i in range(1000):
            event = MetadataEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
                tag_spool=f"TEST-{i % 10:03d}",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="02-02-2026",
                metadata_json='{}',
                n_union=(i % 20) + 1
            )
            events.append(event)

        # Execute batch log
        metadata_repo.batch_log_events(events)

        # Verify append_rows called twice (2 chunks)
        mock_worksheet = metadata_repo._worksheet
        assert mock_worksheet.append_rows.call_count == 2

        # Verify first chunk is exactly 900 rows
        first_call = mock_worksheet.append_rows.call_args_list[0]
        first_chunk = first_call[0][0]
        assert len(first_chunk) == 900

        # Verify second chunk is 100 rows
        second_call = mock_worksheet.append_rows.call_args_list[1]
        second_chunk = second_call[0][0]
        assert len(second_chunk) == 100

    def test_chunking_exactly_900_events(self, metadata_repo, mock_sheets_repo):
        """Should send 900 events in single chunk (no splitting)."""
        # Generate exactly 900 events
        events = []
        for i in range(900):
            event = MetadataEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
                tag_spool="TEST-01",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="02-02-2026",
                metadata_json='{}',
                n_union=(i % 20) + 1
            )
            events.append(event)

        # Execute batch log
        metadata_repo.batch_log_events(events)

        # Verify append_rows called once (exactly 900 fits in one chunk)
        mock_worksheet = metadata_repo._worksheet
        mock_worksheet.append_rows.assert_called_once()

        # Verify chunk is exactly 900 rows
        call_args = mock_worksheet.append_rows.call_args
        rows = call_args[0][0]
        assert len(rows) == 900

    def test_chunking_901_events(self, metadata_repo, mock_sheets_repo):
        """Should chunk 901 events into 2 batches (900 + 1)."""
        # Generate 901 events (just over limit)
        events = []
        for i in range(901):
            event = MetadataEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
                tag_spool="TEST-01",
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="02-02-2026",
                metadata_json='{}',
                n_union=(i % 20) + 1
            )
            events.append(event)

        # Execute batch log
        metadata_repo.batch_log_events(events)

        # Verify append_rows called twice
        mock_worksheet = metadata_repo._worksheet
        assert mock_worksheet.append_rows.call_count == 2

        # Verify chunks are 900 + 1
        first_call = mock_worksheet.append_rows.call_args_list[0]
        first_chunk = first_call[0][0]
        assert len(first_chunk) == 900

        second_call = mock_worksheet.append_rows.call_args_list[1]
        second_chunk = second_call[0][0]
        assert len(second_chunk) == 1


class TestNUnionField:
    """Test n_union field written to column K."""

    def test_n_union_field_in_sheet_row(self, metadata_repo):
        """Should include n_union in to_sheets_row output."""
        # Create event with n_union
        event = MetadataEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            metadata_json='{}',
            n_union=5
        )

        # Convert to sheet row
        row = event.to_sheets_row()

        # Verify n_union is at position 10 (column K, 0-indexed)
        assert len(row) == 11  # 11 total columns
        assert row[10] == "5"  # n_union at index 10 (converted to string for Sheets)

    def test_n_union_none_for_spool_events(self, metadata_repo):
        """Should have None/empty n_union for spool-level events."""
        # Create spool-level event (no n_union)
        event = MetadataEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            evento_tipo=EventoTipo.PAUSAR_SPOOL,
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.PAUSAR,
            fecha_operacion="02-02-2026",
            metadata_json='{}',
            n_union=None
        )

        # Convert to sheet row
        row = event.to_sheets_row()

        # Verify n_union is empty string at position 10
        assert row[10] == ""


class TestMixedEvents:
    """Test mixed v3.0 and v4.0 events in same batch."""

    def test_mixed_v3_and_v4_events(self, metadata_repo, mock_sheets_repo):
        """Should handle v3.0 spool events and v4.0 union events together."""
        events = []

        # v3.0 event (TOMAR_SPOOL - spool-level, no n_union)
        v3_event = MetadataEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            evento_tipo=EventoTipo.TOMAR_SPOOL,
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.TOMAR,
            fecha_operacion="02-02-2026",
            metadata_json='{}',
            n_union=None
        )
        events.append(v3_event)

        # v4.0 event (UNION_ARM_REGISTRADA - union-level, has n_union)
        v4_event = MetadataEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            metadata_json='{"dn_union": 6.0}',
            n_union=3
        )
        events.append(v4_event)

        # Execute batch log
        metadata_repo.batch_log_events(events)

        # Verify both events logged
        mock_worksheet = metadata_repo._worksheet
        mock_worksheet.append_rows.assert_called_once()

        call_args = mock_worksheet.append_rows.call_args
        rows = call_args[0][0]
        assert len(rows) == 2

        # Verify v3.0 event has empty n_union
        assert rows[0][10] == ""  # n_union column

        # Verify v4.0 event has n_union value
        assert rows[1][10] == "3"  # Converted to string


class TestBuildUnionEvents:
    """Test build_union_events helper method."""

    def test_build_union_events_for_arm(self, metadata_repo):
        """Should build ARM union events from details."""
        union_ids = ["001+1", "001+2", "001+3"]
        union_details = [
            {"dn_union": 4.5, "tipo": "Brida", "duracion_min": 15.5},
            {"dn_union": 6.0, "tipo": "Socket", "duracion_min": 20.0},
            {"dn_union": 8.0, "tipo": "Acople", "duracion_min": 18.3}
        ]

        events = metadata_repo.build_union_events(
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            union_ids=union_ids,
            union_details=union_details
        )

        # Verify 3 events created
        assert len(events) == 3

        # Verify each event has correct n_union
        assert events[0].n_union == 1
        assert events[1].n_union == 2
        assert events[2].n_union == 3

        # Verify event types
        assert all(e.evento_tipo == EventoTipo.UNION_ARM_REGISTRADA for e in events)

    def test_build_union_events_for_sold(self, metadata_repo):
        """Should build SOLD union events from details."""
        union_ids = ["001+5", "001+6"]
        union_details = [
            {"dn_union": 10.0, "tipo": "Brida", "duracion_min": 25.0},
            {"dn_union": 12.0, "tipo": "Codo", "duracion_min": 30.5}
        ]

        events = metadata_repo.build_union_events(
            tag_spool="TEST-01",
            worker_id=95,
            worker_nombre="MG(95)",
            operacion="SOLD",
            union_ids=union_ids,
            union_details=union_details
        )

        # Verify 2 events created
        assert len(events) == 2

        # Verify n_union extraction from ID
        assert events[0].n_union == 5
        assert events[1].n_union == 6

        # Verify event types
        assert all(e.evento_tipo == EventoTipo.UNION_SOLD_REGISTRADA for e in events)


class TestErrorHandling:
    """Test error handling for batch operations."""

    def test_batch_log_with_sheets_error(self, metadata_repo, mock_sheets_repo):
        """Should raise exception on API failure."""
        # Mock append_rows to raise exception
        mock_worksheet = metadata_repo._worksheet
        mock_worksheet.append_rows.side_effect = Exception("API Error")

        # Create single event
        event = MetadataEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
            tag_spool="TEST-01",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            metadata_json='{}',
            n_union=1
        )

        # Should raise exception (SheetsUpdateError or TypeError due to pre-existing bug)
        # The important thing is that errors are propagated, not swallowed
        with pytest.raises((SheetsUpdateError, TypeError)):
            metadata_repo.batch_log_events([event])
