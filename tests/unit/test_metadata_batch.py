"""
Unit tests for Metadata batch logging with n_union field and chunking (v4.0).

Tests:
- MetadataEvent with n_union field serialization
- to_sheets_row() produces 11 columns with n_union
- from_sheets_row() handles 10-column (v3.0) and 11-column (v4.0) rows
- batch_log_events with various batch sizes (10, 100, 900, 1000, 2000)
- Chunking logic (verify chunks are exactly 900 rows except last)
- Empty events list handling
- New event types (UNION_ARM_REGISTRADA, UNION_SOLD_REGISTRADA, SPOOL_CANCELADO)
- Backward compatibility of log_event with n_union
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import pytz
import uuid

from backend.models.metadata import MetadataEvent, Accion
from backend.models.enums import EventoTipo
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.utils.date_formatter import format_datetime_for_sheets, now_chile


# Test MetadataEvent with n_union field
def test_metadata_event_with_n_union():
    """Test MetadataEvent includes n_union field and serializes correctly."""
    event = MetadataEvent(
        id="test-uuid",
        timestamp=datetime(2026, 2, 2, 14, 30, 0, tzinfo=pytz.timezone('America/Santiago')),
        evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
        tag_spool="TEST-01",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM",
        accion=Accion.COMPLETAR,
        fecha_operacion="02-02-2026",
        metadata_json='{"dn_union": 4}',
        n_union=5
    )

    assert event.n_union == 5
    assert event.evento_tipo == EventoTipo.UNION_ARM_REGISTRADA


def test_to_sheets_row_with_n_union():
    """Test to_sheets_row() produces 11 columns with n_union in column K."""
    event = MetadataEvent(
        id="test-uuid",
        timestamp=datetime(2026, 2, 2, 14, 30, 0, tzinfo=pytz.timezone('America/Santiago')),
        evento_tipo=EventoTipo.UNION_SOLD_REGISTRADA,
        tag_spool="TEST-02",
        worker_id=94,
        worker_nombre="CP(94)",
        operacion="SOLD",
        accion=Accion.COMPLETAR,
        fecha_operacion="02-02-2026",
        metadata_json='{"dn_union": 6}',
        n_union=3
    )

    row = event.to_sheets_row()

    assert len(row) == 11  # 11 columns (A-K)
    assert row[0] == "test-uuid"
    assert row[2] == "UNION_SOLD_REGISTRADA"
    assert row[3] == "TEST-02"
    assert row[4] == "94"
    assert row[10] == "3"  # Column K (n_union)


def test_to_sheets_row_without_n_union():
    """Test to_sheets_row() produces empty string in column K when n_union=None."""
    event = MetadataEvent(
        id="test-uuid",
        timestamp=datetime(2026, 2, 2, 14, 30, 0, tzinfo=pytz.timezone('America/Santiago')),
        evento_tipo=EventoTipo.TOMAR_SPOOL,
        tag_spool="TEST-03",
        worker_id=95,
        worker_nombre="JP(95)",
        operacion="ARM",
        accion=Accion.TOMAR,
        fecha_operacion="02-02-2026",
        metadata_json='{}',
        n_union=None
    )

    row = event.to_sheets_row()

    assert len(row) == 11
    assert row[10] == ""  # Column K empty when n_union=None


def test_from_sheets_row_with_11_columns():
    """Test from_sheets_row() parses n_union from 11-column row (v4.0)."""
    row = [
        "test-uuid",
        "02-02-2026 14:30:00",
        "UNION_ARM_REGISTRADA",
        "TEST-01",
        "93",
        "MR(93)",
        "ARM",
        "COMPLETAR",
        "02-02-2026",
        '{"dn_union": 4}',
        "5"  # n_union
    ]

    event = MetadataEvent.from_sheets_row(row)

    assert event.n_union == 5
    assert event.evento_tipo == EventoTipo.UNION_ARM_REGISTRADA
    assert event.tag_spool == "TEST-01"


def test_from_sheets_row_with_10_columns():
    """Test from_sheets_row() handles v3.0 rows (10 columns, no n_union)."""
    row = [
        "test-uuid",
        "02-02-2026 14:30:00",
        "TOMAR_SPOOL",
        "TEST-02",
        "94",
        "CP(94)",
        "ARM",
        "TOMAR",
        "02-02-2026",
        '{}'
    ]

    event = MetadataEvent.from_sheets_row(row)

    assert event.n_union is None  # v3.0 backward compatibility
    assert event.evento_tipo == EventoTipo.TOMAR_SPOOL


def test_from_sheets_row_with_empty_n_union():
    """Test from_sheets_row() handles empty n_union (column K exists but empty)."""
    row = [
        "test-uuid",
        "02-02-2026 14:30:00",
        "PAUSAR_SPOOL",
        "TEST-03",
        "95",
        "JP(95)",
        "SOLD",
        "PAUSAR",
        "02-02-2026",
        '{}',
        ""  # Empty n_union
    ]

    event = MetadataEvent.from_sheets_row(row)

    assert event.n_union is None


def test_from_sheets_row_with_invalid_n_union():
    """Test from_sheets_row() gracefully handles non-integer n_union."""
    row = [
        "test-uuid",
        "02-02-2026 14:30:00",
        "UNION_ARM_REGISTRADA",
        "TEST-04",
        "93",
        "MR(93)",
        "ARM",
        "COMPLETAR",
        "02-02-2026",
        '{"dn_union": 4}',
        "invalid"  # Non-integer n_union
    ]

    event = MetadataEvent.from_sheets_row(row)

    assert event.n_union is None  # Gracefully handle invalid value


def test_new_event_types():
    """Test new v4.0 event types are valid."""
    # UNION_ARM_REGISTRADA
    event1 = MetadataEvent(
        id="test-uuid-1",
        timestamp=now_chile(),
        evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
        tag_spool="TEST-01",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM",
        accion=Accion.COMPLETAR,
        fecha_operacion="02-02-2026",
        n_union=1
    )
    assert event1.evento_tipo == EventoTipo.UNION_ARM_REGISTRADA

    # UNION_SOLD_REGISTRADA
    event2 = MetadataEvent(
        id="test-uuid-2",
        timestamp=now_chile(),
        evento_tipo=EventoTipo.UNION_SOLD_REGISTRADA,
        tag_spool="TEST-02",
        worker_id=94,
        worker_nombre="CP(94)",
        operacion="SOLD",
        accion=Accion.COMPLETAR,
        fecha_operacion="02-02-2026",
        n_union=2
    )
    assert event2.evento_tipo == EventoTipo.UNION_SOLD_REGISTRADA

    # SPOOL_CANCELADO
    event3 = MetadataEvent(
        id="test-uuid-3",
        timestamp=now_chile(),
        evento_tipo=EventoTipo.SPOOL_CANCELADO,
        tag_spool="TEST-03",
        worker_id=95,
        worker_nombre="JP(95)",
        operacion="ARM",
        accion=Accion.PAUSAR,
        fecha_operacion="02-02-2026",
        n_union=None
    )
    assert event3.evento_tipo == EventoTipo.SPOOL_CANCELADO


def test_batch_log_events_with_10_events():
    """Test batch_log_events with 10 events (no chunking needed)."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    # Mock worksheet
    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Create 10 test events
    events = [
        MetadataEvent(
            id=f"test-uuid-{i}",
            timestamp=now_chile(),
            evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
            tag_spool=f"TEST-{i:02d}",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            n_union=i
        )
        for i in range(1, 11)
    ]

    # Call batch_log_events
    repo.batch_log_events(events)

    # Verify append_rows called once with all 10 events
    mock_worksheet.append_rows.assert_called_once()
    call_args = mock_worksheet.append_rows.call_args
    rows = call_args[0][0]
    assert len(rows) == 10


def test_batch_log_events_with_900_events():
    """Test batch_log_events with exactly 900 events (1 chunk)."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Create 900 events
    events = [
        MetadataEvent(
            id=f"test-uuid-{i}",
            timestamp=now_chile(),
            evento_tipo=EventoTipo.UNION_SOLD_REGISTRADA,
            tag_spool=f"TEST-{i:04d}",
            worker_id=94,
            worker_nombre="CP(94)",
            operacion="SOLD",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            n_union=(i % 10) + 1
        )
        for i in range(900)
    ]

    repo.batch_log_events(events)

    # Verify append_rows called once
    mock_worksheet.append_rows.assert_called_once()
    call_args = mock_worksheet.append_rows.call_args
    rows = call_args[0][0]
    assert len(rows) == 900


def test_batch_log_events_with_1000_events():
    """Test batch_log_events with 1000 events (2 chunks: 900 + 100)."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Create 1000 events
    events = [
        MetadataEvent(
            id=f"test-uuid-{i}",
            timestamp=now_chile(),
            evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
            tag_spool=f"TEST-{i:04d}",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            n_union=(i % 15) + 1
        )
        for i in range(1000)
    ]

    repo.batch_log_events(events)

    # Verify append_rows called twice
    assert mock_worksheet.append_rows.call_count == 2

    # Verify first chunk is 900 rows
    first_call = mock_worksheet.append_rows.call_args_list[0]
    first_chunk = first_call[0][0]
    assert len(first_chunk) == 900

    # Verify second chunk is 100 rows
    second_call = mock_worksheet.append_rows.call_args_list[1]
    second_chunk = second_call[0][0]
    assert len(second_chunk) == 100


def test_batch_log_events_with_2000_events():
    """Test batch_log_events with 2000 events (3 chunks: 900 + 900 + 200)."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Create 2000 events
    events = [
        MetadataEvent(
            id=f"test-uuid-{i}",
            timestamp=now_chile(),
            evento_tipo=EventoTipo.UNION_SOLD_REGISTRADA,
            tag_spool=f"TEST-{i:04d}",
            worker_id=94,
            worker_nombre="CP(94)",
            operacion="SOLD",
            accion=Accion.COMPLETAR,
            fecha_operacion="02-02-2026",
            n_union=(i % 20) + 1
        )
        for i in range(2000)
    ]

    repo.batch_log_events(events)

    # Verify append_rows called 3 times
    assert mock_worksheet.append_rows.call_count == 3

    # Verify chunk sizes
    chunks = [call[0][0] for call in mock_worksheet.append_rows.call_args_list]
    assert len(chunks[0]) == 900
    assert len(chunks[1]) == 900
    assert len(chunks[2]) == 200


def test_batch_log_events_with_empty_list():
    """Test batch_log_events with empty events list (graceful handling)."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Call with empty list
    repo.batch_log_events([])

    # Verify append_rows NOT called
    mock_worksheet.append_rows.assert_not_called()


def test_log_event_with_n_union():
    """Test log_event accepts optional n_union parameter."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Call log_event with n_union
    event_id = repo.log_event(
        evento_tipo="UNION_ARM_REGISTRADA",
        tag_spool="TEST-01",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM",
        accion="COMPLETAR",
        fecha_operacion=None,
        metadata_json='{"dn_union": 4}',
        n_union=5
    )

    # Verify append_row called
    mock_worksheet.append_row.assert_called_once()

    # Verify row has 11 columns with n_union
    call_args = mock_worksheet.append_row.call_args
    row = call_args[0][0]
    assert len(row) == 11
    assert row[10] == "5"  # n_union in column K


def test_log_event_without_n_union():
    """Test log_event backward compatibility (n_union=None by default)."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    mock_worksheet = Mock()
    repo._worksheet = mock_worksheet

    # Call log_event WITHOUT n_union
    event_id = repo.log_event(
        evento_tipo="TOMAR_SPOOL",
        tag_spool="TEST-02",
        worker_id=94,
        worker_nombre="CP(94)",
        operacion="ARM",
        accion="TOMAR",
        fecha_operacion=None,
        metadata_json='{}'
    )

    # Verify append_row called
    mock_worksheet.append_row.assert_called_once()

    # Verify row has 11 columns with empty n_union
    call_args = mock_worksheet.append_row.call_args
    row = call_args[0][0]
    assert len(row) == 11
    assert row[10] == ""  # n_union empty (column K)


def test_build_union_events():
    """Test build_union_events generates proper MetadataEvent list."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    union_ids = ["OT-123+1", "OT-123+2", "OT-123+3"]
    union_details = [
        {"dn_union": 4, "tipo": "B", "duracion_min": 15.5},
        {"dn_union": 6, "tipo": "A", "duracion_min": 20.0},
        {"dn_union": 4, "tipo": "C", "duracion_min": 18.2}
    ]

    events = repo.build_union_events(
        tag_spool="TEST-01",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM",
        union_ids=union_ids,
        union_details=union_details
    )

    # Verify 3 events created
    assert len(events) == 3

    # Verify first event
    assert events[0].tag_spool == "TEST-01"
    assert events[0].worker_id == 93
    assert events[0].evento_tipo == EventoTipo.UNION_ARM_REGISTRADA
    assert events[0].n_union == 1
    assert events[0].accion == Accion.COMPLETAR

    # Verify metadata_json contains union details
    import json
    metadata = json.loads(events[0].metadata_json)
    assert metadata["dn_union"] == 4
    assert metadata["tipo"] == "B"
    assert metadata["duracion_min"] == 15.5


def test_build_union_events_sold():
    """Test build_union_events with SOLD operation."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    union_ids = ["OT-456+5", "OT-456+6"]
    union_details = [
        {"dn_union": 8, "tipo": "A", "duracion_min": 25.0},
        {"dn_union": 10, "tipo": "B", "duracion_min": 30.5}
    ]

    events = repo.build_union_events(
        tag_spool="TEST-02",
        worker_id=94,
        worker_nombre="CP(94)",
        operacion="SOLD",
        union_ids=union_ids,
        union_details=union_details
    )

    assert len(events) == 2
    assert events[0].evento_tipo == EventoTipo.UNION_SOLD_REGISTRADA
    assert events[0].n_union == 5
    assert events[1].n_union == 6


def test_build_union_events_malformed_id():
    """Test build_union_events gracefully skips malformed union IDs."""
    sheets_repo = Mock(spec=SheetsRepository)
    repo = MetadataRepository(sheets_repo)

    union_ids = ["OT-123+1", "INVALID-ID", "OT-123+3"]
    union_details = [
        {"dn_union": 4, "tipo": "B", "duracion_min": 15.5},
        {"dn_union": 6, "tipo": "A", "duracion_min": 20.0},
        {"dn_union": 4, "tipo": "C", "duracion_min": 18.2}
    ]

    events = repo.build_union_events(
        tag_spool="TEST-03",
        worker_id=93,
        worker_nombre="MR(93)",
        operacion="ARM",
        union_ids=union_ids,
        union_details=union_details
    )

    # Verify only 2 valid events created (malformed ID skipped)
    assert len(events) == 2
    assert events[0].n_union == 1
    assert events[1].n_union == 3
