"""
Sanity tests for backend/models/supervisor.py.

Smoke-level: verifies roundtrip (to/from sheets), frozen invariant on event
sourcing models, and that LegacySnapshot preserves its raw bytes verbatim.
Full coverage of repository/service edge cases lives in tests for tasks #4–8.
"""
import pytest

from backend.models.supervisor import (
    AuditEvent,
    AuditEventBatch,
    EventType,
    LegacySnapshot,
    TrackedSpool,
)


# ─── TrackedSpool ─────────────────────────────────────────────────────────────


def test_tracked_spool_roundtrip_preserves_fields():
    from datetime import timezone

    s = TrackedSpool(tag_spool="MK-1344-GW-27133-002", priority=1)
    row = s.to_sheets_row()
    assert len(row) == 5

    parsed = TrackedSpool.from_sheets_row(row)
    assert parsed.tag_spool == s.tag_spool
    assert parsed.priority == s.priority
    # Sheets serialization drops microseconds. Compare in UTC seconds — the
    # two datetimes may carry different pytz tzinfo objects (LMT vs -04 STD)
    # but represent the same instant.
    a = parsed.added_at.astimezone(timezone.utc).replace(microsecond=0)
    b = s.added_at.astimezone(timezone.utc).replace(microsecond=0)
    assert a == b


def test_tracked_spool_priority_validation():
    with pytest.raises(Exception):
        TrackedSpool(tag_spool="X", priority=4)
    with pytest.raises(Exception):
        TrackedSpool(tag_spool="X", priority=-1)


def test_tracked_spool_empty_priority_defaults_to_zero():
    """Old rows with empty priority cell should parse to priority=0 not crash."""
    row = ["MK-1", "", "08-05-2026 09:00:00", "08-05-2026 09:00:00", ""]
    parsed = TrackedSpool.from_sheets_row(row)
    assert parsed.priority == 0
    assert parsed.notes is None


def test_tracked_spool_from_row_with_column_map():
    """from_sheets_row should respect column_map (out-of-order headers)."""
    column_map = {
        "tagspool": 2,
        "priority": 0,
        "addedat": 3,
        "updatedat": 4,
        "notes": 1,
    }
    row = ["1", "una nota", "MK-X", "08-05-2026 09:00:00", "08-05-2026 09:00:00"]
    parsed = TrackedSpool.from_sheets_row(row, column_map=column_map)
    assert parsed.tag_spool == "MK-X"
    assert parsed.priority == 1
    assert parsed.notes == "una nota"


# ─── AuditEvent ───────────────────────────────────────────────────────────────


def test_audit_event_is_frozen():
    e = AuditEvent(session_id="sess-1", event_type=EventType.SESSION_START)
    with pytest.raises(Exception):
        e.timestamp = e.timestamp  # frozen — even setting to same value fails


def test_audit_event_default_id_is_uuid_string():
    e = AuditEvent(session_id="sess-1", event_type=EventType.SESSION_START)
    assert isinstance(e.id, str) and len(e.id) >= 32


def test_audit_event_roundtrip_with_optionals():
    e = AuditEvent(
        session_id="sess-1",
        event_type=EventType.MODAL_OPEN,
        tag_spool="MK-1",
        modal="ActionModal",
        route="/",
        payload_json='{"trigger":"card_click"}',
    )
    row = e.to_sheets_row()
    assert len(row) == 8

    parsed = AuditEvent.from_sheets_row(row)
    assert parsed.id == e.id
    assert parsed.session_id == e.session_id
    assert parsed.event_type == EventType.MODAL_OPEN
    assert parsed.tag_spool == "MK-1"
    assert parsed.modal == "ActionModal"
    assert parsed.route == "/"
    assert parsed.payload_json == '{"trigger":"card_click"}'


def test_audit_event_roundtrip_omits_empty_optionals():
    """Optional fields stored as '' in Sheets should round-trip back to None."""
    e = AuditEvent(session_id="sess-1", event_type=EventType.SESSION_START)
    row = e.to_sheets_row()
    parsed = AuditEvent.from_sheets_row(row)
    assert parsed.tag_spool is None
    assert parsed.modal is None
    assert parsed.route is None
    assert parsed.payload_json is None


# ─── AuditEventBatch ──────────────────────────────────────────────────────────


def test_audit_event_batch_rejects_empty():
    with pytest.raises(Exception):
        AuditEventBatch(events=[])


def test_audit_event_batch_rejects_more_than_100():
    too_many = [
        AuditEvent(session_id="s", event_type=EventType.MODAL_OPEN)
        for _ in range(101)
    ]
    with pytest.raises(Exception):
        AuditEventBatch(events=too_many)


def test_audit_event_batch_accepts_one_to_hundred():
    one = AuditEventBatch(
        events=[AuditEvent(session_id="s", event_type=EventType.MODAL_OPEN)]
    )
    assert len(one.events) == 1
    hundred = AuditEventBatch(
        events=[
            AuditEvent(session_id="s", event_type=EventType.MODAL_OPEN)
            for _ in range(100)
        ]
    )
    assert len(hundred.events) == 100


# ─── LegacySnapshot ───────────────────────────────────────────────────────────


def test_legacy_snapshot_preserves_raw_bytes():
    raw = '[{"tag":"X","priority":1},{"tag":"Y","priority":null}]'
    snap = LegacySnapshot(snapshot_id="abc-123", raw=raw, user_agent="Test/1.0")
    assert snap.to_sheets_row()[2] == raw

    parsed = LegacySnapshot.from_sheets_row(snap.to_sheets_row())
    assert parsed.raw == raw  # byte-for-byte
    assert parsed.snapshot_id == "abc-123"
    assert parsed.user_agent == "Test/1.0"


def test_legacy_snapshot_is_frozen():
    snap = LegacySnapshot(snapshot_id="abc", raw="[]")
    with pytest.raises(Exception):
        snap.raw = "modified"


def test_legacy_snapshot_optional_user_agent():
    """user_agent absent should round-trip cleanly."""
    snap = LegacySnapshot(snapshot_id="abc", raw="[]")
    parsed = LegacySnapshot.from_sheets_row(snap.to_sheets_row())
    assert parsed.user_agent is None
