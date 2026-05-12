"""
Smoke tests para SupervisorService.

Mockean SupervisorRepository — no llamadas reales a Sheets.
Cubren validaciones, idempotencia, auditoría, y resilience cuando el audit
append falla (no debe bloquear la mutación principal).
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import pytz

from backend.models.supervisor import (
    AuditEvent,
    EventType,
    LegacySnapshot,
    TrackedSpool,
)
from backend.services.supervisor_service import SupervisorService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    return SupervisorService(supervisor_repo=mock_repo)


# ─── Validación de inputs ─────────────────────────────────────────────────────


def test_add_rejects_empty_tag(service, mock_repo):
    with pytest.raises(ValueError, match="tag_spool"):
        service.add_to_list("   ", session_id="sess-1")
    mock_repo.upsert_tracked_spool.assert_not_called()


def test_add_rejects_empty_session_id(service, mock_repo):
    with pytest.raises(ValueError, match="session_id"):
        service.add_to_list("MK-1", session_id="")
    mock_repo.upsert_tracked_spool.assert_not_called()


def test_remove_rejects_empty_tag(service, mock_repo):
    with pytest.raises(ValueError, match="tag_spool"):
        service.remove_from_list("", session_id="sess-1")
    mock_repo.remove_tracked_spool.assert_not_called()


# ─── add_to_list happy paths ──────────────────────────────────────────────────


def test_add_calls_upsert_and_emits_audit(service, mock_repo):
    """Happy path: upsert + audit append, ambos con datos correctos."""
    mock_repo.upsert_tracked_spool.side_effect = lambda s: s

    result = service.add_to_list("MK-NEW", session_id="sess-1")

    assert result.tag_spool == "MK-NEW"

    mock_repo.upsert_tracked_spool.assert_called_once()
    upserted_spool = mock_repo.upsert_tracked_spool.call_args.args[0]
    assert isinstance(upserted_spool, TrackedSpool)
    assert upserted_spool.tag_spool == "MK-NEW"

    # Audit
    mock_repo.append_audit_events.assert_called_once()
    events = mock_repo.append_audit_events.call_args.args[0]
    assert len(events) == 1
    assert events[0].event_type == EventType.LIST_ADD
    assert events[0].tag_spool == "MK-NEW"
    assert events[0].session_id == "sess-1"


def test_add_strips_whitespace_from_tag(service, mock_repo):
    mock_repo.upsert_tracked_spool.side_effect = lambda s: s
    result = service.add_to_list("  MK-X  ", session_id="s")
    assert result.tag_spool == "MK-X"


def test_add_audit_failure_does_not_block_upsert(service, mock_repo):
    """Si append_audit_events lanza, el upsert ya hecho NO se rollback."""
    mock_repo.upsert_tracked_spool.side_effect = lambda s: s
    mock_repo.append_audit_events.side_effect = RuntimeError("audit down")

    result = service.add_to_list("MK-1", session_id="sess-1")

    # Mutación principal exitosa; audit falló silenciosamente
    assert result.tag_spool == "MK-1"
    mock_repo.upsert_tracked_spool.assert_called_once()
    mock_repo.append_audit_events.assert_called_once()


# ─── remove_from_list ─────────────────────────────────────────────────────────


def test_remove_returns_false_and_skips_audit_when_absent(service, mock_repo):
    """No-op: tag no existía, no se emite LIST_REMOVE."""
    mock_repo.remove_tracked_spool.return_value = False

    result = service.remove_from_list("MK-MISSING", session_id="sess-1")

    assert result is False
    mock_repo.remove_tracked_spool.assert_called_once_with("MK-MISSING")
    mock_repo.append_audit_events.assert_not_called()


def test_remove_emits_audit_when_actually_deleted(service, mock_repo):
    mock_repo.remove_tracked_spool.return_value = True

    result = service.remove_from_list("MK-DEL", session_id="sess-1")

    assert result is True
    mock_repo.append_audit_events.assert_called_once()
    events = mock_repo.append_audit_events.call_args.args[0]
    assert events[0].event_type == EventType.LIST_REMOVE
    assert events[0].tag_spool == "MK-DEL"


# ─── Passthroughs ─────────────────────────────────────────────────────────────


def test_record_audit_batch_passthrough(service, mock_repo):
    mock_repo.append_audit_events.return_value = 5
    events = [
        AuditEvent(session_id="s", event_type=EventType.MODAL_OPEN)
        for _ in range(2)
    ]
    n = service.record_audit_batch(events)
    assert n == 5
    mock_repo.append_audit_events.assert_called_once_with(events)


def test_get_audit_since_passthrough(service, mock_repo):
    SCL = pytz.timezone("America/Santiago")
    cutoff = SCL.localize(datetime(2026, 5, 8))
    sample = AuditEvent(session_id="s", event_type=EventType.SESSION_START)
    mock_repo.get_audit_events_since.return_value = [sample]

    result = service.get_audit_since(cutoff)

    assert result == [sample]
    mock_repo.get_audit_events_since.assert_called_once_with(cutoff)


def test_record_legacy_snapshot_passthrough(service, mock_repo):
    mock_repo.append_legacy_snapshot.return_value = True
    snap = LegacySnapshot(snapshot_id="abc", raw="[]")
    assert service.record_legacy_snapshot(snap) is True
    mock_repo.append_legacy_snapshot.assert_called_once_with(snap)


def test_list_tracked_spools_passthrough(service, mock_repo):
    SCL = pytz.timezone("America/Santiago")
    sample = [
        TrackedSpool(
            tag_spool="A",
            added_at=SCL.localize(datetime(2026, 5, 1)),
            updated_at=SCL.localize(datetime(2026, 5, 1)),
        )
    ]
    mock_repo.list_tracked_spools.return_value = sample
    assert service.list_tracked_spools() == sample
