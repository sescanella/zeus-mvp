"""
Smoke tests para SupervisorRepository.

Mockean SheetsRepository.open_spreadsheet para evitar llamadas reales al API
de Google. Verifican el contrato de cada método público (idempotencia, dedup,
no-ops correctos).

Cobertura más amplia (parsing tolerante, errores 5xx con retry, etc.) vive
en Task #8.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import pytz

from backend.config import config
from backend.models.supervisor import (
    AuditEvent,
    EventType,
    LegacySnapshot,
    TrackedSpool,
)
from backend.repositories.supervisor_repository import SupervisorRepository


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_sheets_repo():
    """SheetsRepository mock que sirve worksheets scripted por nombre."""
    sheets_repo = MagicMock()
    spreadsheet = MagicMock()

    worksheets: dict[str, MagicMock] = {
        config.HOJA_AUDIT_LISTA_NOMBRE: MagicMock(),
        config.HOJA_AUDIT_EVENTS_NOMBRE: MagicMock(),
        config.HOJA_AUDIT_SNAPSHOTS_NOMBRE: MagicMock(),
    }

    def get_worksheet(name: str):
        return worksheets[name]

    spreadsheet.worksheet.side_effect = get_worksheet
    sheets_repo.open_spreadsheet.return_value = spreadsheet

    # Defaults: empty sheets
    for ws in worksheets.values():
        ws.col_values.return_value = ["TAG_SPOOL"]  # solo header
        ws.get_all_values.return_value = [["TAG_SPOOL"]]

    # Stash worksheets so tests can configure them
    sheets_repo._worksheets_for_test = worksheets
    return sheets_repo


@pytest.fixture
def repo(mock_sheets_repo):
    return SupervisorRepository(sheets_repo=mock_sheets_repo)


def _ws_lista(repo: SupervisorRepository) -> MagicMock:
    return repo.sheets_repo._worksheets_for_test[config.HOJA_AUDIT_LISTA_NOMBRE]


def _ws_audit(repo: SupervisorRepository) -> MagicMock:
    return repo.sheets_repo._worksheets_for_test[config.HOJA_AUDIT_EVENTS_NOMBRE]


def _ws_snapshots(repo: SupervisorRepository) -> MagicMock:
    return repo.sheets_repo._worksheets_for_test[config.HOJA_AUDIT_SNAPSHOTS_NOMBRE]


# ─── upsert_tracked_spool ────────────────────────────────────────────────────


def test_upsert_inserts_when_tag_absent(repo):
    """Sin filas previas → append_row. Sin update_call."""
    ws = _ws_lista(repo)
    ws.col_values.return_value = ["TAG_SPOOL"]  # nadie

    spool = TrackedSpool(tag_spool="MK-NEW", priority=1)
    repo.upsert_tracked_spool(spool)

    ws.append_row.assert_called_once()
    ws.update.assert_not_called()


def test_upsert_updates_when_tag_present(repo):
    """Tag ya existe en fila 4 → update A4:E4, sin append."""
    ws = _ws_lista(repo)
    ws.col_values.return_value = ["TAG_SPOOL", "MK-A", "MK-B", "MK-TARGET"]
    # → "MK-TARGET" está en row index 4 (1-indexed: header en 1, MK-A 2, MK-B 3, MK-TARGET 4)

    spool = TrackedSpool(tag_spool="MK-TARGET", priority=2)
    repo.upsert_tracked_spool(spool)

    ws.update.assert_called_once()
    call = ws.update.call_args
    assert call.kwargs["range_name"] == "A4:E4"
    assert call.kwargs["value_input_option"] == "USER_ENTERED"
    ws.append_row.assert_not_called()


def test_upsert_returns_the_spool(repo):
    spool = TrackedSpool(tag_spool="X", priority=1)
    result = repo.upsert_tracked_spool(spool)
    assert result is spool


# ─── remove_tracked_spool ────────────────────────────────────────────────────


def test_remove_no_op_when_tag_absent(repo):
    """Tag no existe → False, no delete_rows."""
    ws = _ws_lista(repo)
    ws.col_values.return_value = ["TAG_SPOOL", "MK-A", "MK-B"]

    deleted = repo.remove_tracked_spool("MK-MISSING")

    assert deleted is False
    ws.delete_rows.assert_not_called()


def test_remove_deletes_existing_row(repo):
    """Tag en fila 3 → delete_rows(3), True."""
    ws = _ws_lista(repo)
    ws.col_values.return_value = ["TAG_SPOOL", "MK-A", "MK-TARGET", "MK-C"]

    deleted = repo.remove_tracked_spool("MK-TARGET")

    assert deleted is True
    ws.delete_rows.assert_called_once_with(3)


# ─── append_audit_events ─────────────────────────────────────────────────────


def test_append_audit_skips_existing_ids(repo):
    """Eventos cuyo id ya está en col A se filtran antes de append_rows."""
    ws = _ws_audit(repo)
    # Audit ya tiene un evento con id "abc-1"
    ws.col_values.return_value = ["ID", "abc-1"]

    e1 = AuditEvent(
        id="abc-1",  # already in sheet
        session_id="s",
        event_type=EventType.MODAL_OPEN,
    )
    e2 = AuditEvent(
        id="abc-2",  # nuevo
        session_id="s",
        event_type=EventType.MODAL_CLOSE,
    )

    appended = repo.append_audit_events([e1, e2])

    assert appended == 1
    ws.append_rows.assert_called_once()
    rows_arg = ws.append_rows.call_args.args[0]
    assert len(rows_arg) == 1
    assert rows_arg[0][0] == "abc-2"


def test_append_audit_empty_list_is_noop(repo):
    appended = repo.append_audit_events([])
    assert appended == 0
    ws = _ws_audit(repo)
    ws.append_rows.assert_not_called()


def test_append_audit_all_dedup_no_write(repo):
    """Si todos los eventos ya están, no se llama append_rows."""
    ws = _ws_audit(repo)
    ws.col_values.return_value = ["ID", "x", "y"]

    e1 = AuditEvent(id="x", session_id="s", event_type=EventType.MODAL_OPEN)
    e2 = AuditEvent(id="y", session_id="s", event_type=EventType.MODAL_CLOSE)

    appended = repo.append_audit_events([e1, e2])
    assert appended == 0
    ws.append_rows.assert_not_called()


# ─── append_legacy_snapshot ──────────────────────────────────────────────────


def test_append_snapshot_writes_when_id_new(repo):
    ws = _ws_snapshots(repo)
    ws.col_values.return_value = ["Snapshot_ID"]  # vacío

    snap = LegacySnapshot(snapshot_id="snap-1", raw='[{"tag":"X"}]')
    written = repo.append_legacy_snapshot(snap)

    assert written is True
    ws.append_row.assert_called_once()


def test_append_snapshot_idempotent_on_duplicate_id(repo):
    ws = _ws_snapshots(repo)
    ws.col_values.return_value = ["Snapshot_ID", "snap-existing"]

    snap = LegacySnapshot(snapshot_id="snap-existing", raw='[{"tag":"X"}]')
    written = repo.append_legacy_snapshot(snap)

    assert written is False
    ws.append_row.assert_not_called()


# ─── list_tracked_spools ─────────────────────────────────────────────────────


def test_list_returns_empty_when_only_headers(repo):
    ws = _ws_lista(repo)
    ws.get_all_values.return_value = [
        ["TAG_SPOOL", "Priority", "Added_At", "Updated_At", "Notes"]
    ]
    assert repo.list_tracked_spools() == []


def test_list_parses_valid_rows(repo):
    ws = _ws_lista(repo)
    ws.get_all_values.return_value = [
        ["TAG_SPOOL", "Priority", "Added_At", "Updated_At", "Notes"],
        ["MK-1", "1", "08-05-2026 09:00:00", "08-05-2026 09:00:00", "una nota"],
        ["MK-2", "0", "08-05-2026 09:01:00", "08-05-2026 09:01:00", ""],
    ]

    items = repo.list_tracked_spools()
    assert len(items) == 2
    assert items[0].tag_spool == "MK-1"
    assert items[0].priority == 1
    assert items[0].notes == "una nota"
    assert items[1].tag_spool == "MK-2"
    assert items[1].notes is None


def test_list_skips_rows_that_fail_to_parse(repo):
    """Una fila garbage no rompe el resto."""
    ws = _ws_lista(repo)
    ws.get_all_values.return_value = [
        ["TAG_SPOOL", "Priority", "Added_At", "Updated_At", "Notes"],
        ["MK-OK", "1", "08-05-2026 09:00:00", "08-05-2026 09:00:00", ""],
        ["MK-BAD", "1", "no-es-fecha", "tampoco", ""],
        ["MK-OK-2", "2", "08-05-2026 09:00:00", "08-05-2026 09:00:00", ""],
    ]

    items = repo.list_tracked_spools()
    tags = [i.tag_spool for i in items]
    assert tags == ["MK-OK", "MK-OK-2"]


# ─── get_audit_events_since ──────────────────────────────────────────────────


def test_get_audit_since_filters_by_timestamp(repo):
    ws = _ws_audit(repo)
    # 3 eventos, el primero es anterior al cutoff.
    ws.get_all_values.return_value = [
        [
            "ID", "Timestamp", "Session_ID", "Event_Type",
            "TAG_SPOOL", "Modal", "Route", "Payload_JSON",
        ],
        ["e1", "07-05-2026 09:00:00", "s", "MODAL_OPEN", "", "", "", ""],
        ["e2", "08-05-2026 09:00:00", "s", "MODAL_OPEN", "", "", "", ""],
        ["e3", "08-05-2026 10:00:00", "s", "MODAL_CLOSE", "", "", "", ""],
    ]

    cutoff = pytz.timezone("America/Santiago").localize(
        datetime(2026, 5, 8, 0, 0, 0)
    )
    events = repo.get_audit_events_since(cutoff)

    ids = [e.id for e in events]
    assert ids == ["e2", "e3"]


# ─── validate_schema ─────────────────────────────────────────────────────────


def test_validate_schema_passes_with_correct_headers(repo):
    _ws_lista(repo).row_values.return_value = [
        "TAG_SPOOL", "Priority", "Added_At", "Updated_At", "Notes",
    ]
    _ws_audit(repo).row_values.return_value = [
        "ID", "Timestamp", "Session_ID", "Event_Type",
        "TAG_SPOOL", "Modal", "Route", "Payload_JSON",
    ]
    _ws_snapshots(repo).row_values.return_value = [
        "Snapshot_ID", "Captured_At", "Raw_JSON", "User_Agent",
    ]
    repo.validate_schema()  # should not raise


def test_validate_schema_fails_on_wrong_headers(repo):
    from backend.exceptions import SheetsConnectionError

    _ws_lista(repo).row_values.return_value = ["WRONG", "HEADERS"]
    _ws_audit(repo).row_values.return_value = [
        "ID", "Timestamp", "Session_ID", "Event_Type",
        "TAG_SPOOL", "Modal", "Route", "Payload_JSON",
    ]
    _ws_snapshots(repo).row_values.return_value = [
        "Snapshot_ID", "Captured_At", "Raw_JSON", "User_Agent",
    ]

    with pytest.raises(SheetsConnectionError) as exc_info:
        repo.validate_schema()
    assert "Headers incorrectos" in str(exc_info.value)
