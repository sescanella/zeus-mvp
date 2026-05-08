"""
Router-level tests for backend/routers/supervisor_router.py.

Cubre los 5 gaps que el unit testing de capas inferiores no puede cubrir:
1. DI wiring del FastAPI layer (Depends(get_supervisor_service)).
2. Translation ValueError → HTTP 400.
3. Pydantic schema rejection → HTTP 422 con shape estándar.
4. Parsing de ISO 8601 con TZ en `since: datetime`.
5. Response shapes exactos para cada endpoint.

Patrón: TestClient(app) + app.dependency_overrides[get_supervisor_service] = MagicMock.
NO mockea SupervisorRepository ni SheetsRepository — confiamos en que la capa de
service está cubierta por test_supervisor_service.py.

Reference:
- Router: backend/routers/supervisor_router.py
- DI: backend/core/dependency.py:get_supervisor_service
- Models: backend/models/supervisor.py
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import pytz
from fastapi.testclient import TestClient

from backend.core.dependency import get_supervisor_service
from backend.main import app
from backend.models.supervisor import (
    AuditEvent,
    EventType,
    LegacySnapshot,
    TrackedSpool,
)


SCL = pytz.timezone("America/Santiago")


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
def client(mock_service):
    # NOTE: do NOT use `with TestClient(app)` — that triggers
    # @app.on_event("startup") which calls Sheets validators (v4 schema +
    # supervisor schema). The other router tests in this codebase all use
    # `TestClient(app)` directly to skip startup. Mirroring that pattern.
    app.dependency_overrides[get_supervisor_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def _sample_spool(tag="MK-1", priority=1, notes=None) -> TrackedSpool:
    """Helper to build a TrackedSpool with deterministic timestamps."""
    ts = SCL.localize(datetime(2026, 5, 8, 9, 0, 0))
    return TrackedSpool(
        tag_spool=tag,
        priority=priority,
        added_at=ts,
        updated_at=ts,
        notes=notes,
    )


# ─── GET /list ───────────────────────────────────────────────────────────────


def test_get_list_returns_items_array(client, mock_service):
    mock_service.list_tracked_spools.return_value = [
        _sample_spool("MK-A", priority=1),
        _sample_spool("MK-B", priority=3),
    ]

    resp = client.get("/api/supervisor/list")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert len(body["items"]) == 2
    tags = [it["tag_spool"] for it in body["items"]]
    assert tags == ["MK-A", "MK-B"]
    mock_service.list_tracked_spools.assert_called_once()


# ─── POST /list/add ──────────────────────────────────────────────────────────


def test_add_to_list_happy_path(client, mock_service):
    """Default priority is 0 when omitted; response wraps the spool in `item`."""
    returned = _sample_spool("MK-NEW", priority=0)
    mock_service.add_to_list.return_value = returned

    resp = client.post(
        "/api/supervisor/list/add",
        json={"tag_spool": "MK-NEW", "session_id": "sess-1"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "item" in body
    assert body["item"]["tag_spool"] == "MK-NEW"
    assert body["item"]["priority"] == 0
    # Service called with default priority=0
    mock_service.add_to_list.assert_called_once_with("MK-NEW", 0, "sess-1")


def test_add_to_list_pydantic_rejects_priority_too_high(client, mock_service):
    """Pydantic catches priority>3 BEFORE the service is called → 422."""
    resp = client.post(
        "/api/supervisor/list/add",
        json={"tag_spool": "X", "priority": 4, "session_id": "s"},
    )

    assert resp.status_code == 422
    body = resp.json()
    # FastAPI's standard error envelope
    assert "detail" in body
    error = body["detail"][0]
    assert error["loc"] == ["body", "priority"]
    assert "less than or equal to 3" in error["msg"].lower()
    mock_service.add_to_list.assert_not_called()


def test_add_to_list_value_error_returns_400(client, mock_service):
    """When the service raises ValueError, the router maps to 400, not 500."""
    mock_service.add_to_list.side_effect = ValueError(
        "tag_spool no puede estar vacío"
    )

    resp = client.post(
        "/api/supervisor/list/add",
        json={"tag_spool": "valid", "priority": 1, "session_id": "s"},
    )

    assert resp.status_code == 400
    assert "tag_spool" in resp.json()["detail"]


def test_add_to_list_pydantic_rejects_empty_session_id(client, mock_service):
    """session_id has min_length=1 in the request schema."""
    resp = client.post(
        "/api/supervisor/list/add",
        json={"tag_spool": "MK-X", "priority": 1, "session_id": ""},
    )

    assert resp.status_code == 422
    mock_service.add_to_list.assert_not_called()


# ─── POST /list/remove ───────────────────────────────────────────────────────


def test_remove_returns_200_with_removed_false_when_absent(client, mock_service):
    """Idempotent remove → 200 with removed:false. Preserves optimistic UX."""
    mock_service.remove_from_list.return_value = False

    resp = client.post(
        "/api/supervisor/list/remove",
        json={"tag_spool": "MK-MISSING", "session_id": "s"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"removed": False, "tag_spool": "MK-MISSING"}


def test_remove_returns_200_with_removed_true_when_deleted(client, mock_service):
    mock_service.remove_from_list.return_value = True

    resp = client.post(
        "/api/supervisor/list/remove",
        json={"tag_spool": "MK-DEL", "session_id": "s"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"removed": True, "tag_spool": "MK-DEL"}


# ─── POST /list/priority ─────────────────────────────────────────────────────


def test_set_priority_happy_path(client, mock_service):
    returned = _sample_spool("MK-P", priority=3)
    mock_service.set_priority.return_value = returned

    resp = client.post(
        "/api/supervisor/list/priority",
        json={"tag_spool": "MK-P", "priority": 3, "session_id": "s"},
    )

    assert resp.status_code == 200
    assert resp.json()["item"]["priority"] == 3
    mock_service.set_priority.assert_called_once_with("MK-P", 3, "s")


# ─── POST /audit/batch ───────────────────────────────────────────────────────


def test_audit_batch_returns_appended_count(client, mock_service):
    mock_service.record_audit_batch.return_value = 2

    resp = client.post(
        "/api/supervisor/audit/batch",
        json={
            "events": [
                {
                    "id": "evt-1",
                    "session_id": "s1",
                    "event_type": "MODAL_OPEN",
                    "timestamp": "2026-05-08T09:00:00-04:00",
                },
                {
                    "id": "evt-2",
                    "session_id": "s1",
                    "event_type": "MODAL_CLOSE",
                    "timestamp": "2026-05-08T09:00:01-04:00",
                },
            ]
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"appended": 2}

    # Service received parsed AuditEvent instances
    mock_service.record_audit_batch.assert_called_once()
    args = mock_service.record_audit_batch.call_args.args[0]
    assert len(args) == 2
    assert args[0].event_type == EventType.MODAL_OPEN
    assert args[1].event_type == EventType.MODAL_CLOSE


def test_audit_batch_rejects_more_than_100_events(client, mock_service):
    """AuditEventBatch.max_length=100; Pydantic must reject 101."""
    events = [
        {
            "id": f"e-{i}",
            "session_id": "s",
            "event_type": "MODAL_OPEN",
            "timestamp": "2026-05-08T09:00:00-04:00",
        }
        for i in range(101)
    ]
    resp = client.post(
        "/api/supervisor/audit/batch",
        json={"events": events},
    )

    assert resp.status_code == 422
    mock_service.record_audit_batch.assert_not_called()


# ─── GET /audit ──────────────────────────────────────────────────────────────


def test_get_audit_parses_iso_8601_with_timezone(client, mock_service):
    """ISO 8601 with offset must reach the service as a tz-aware datetime."""
    mock_service.get_audit_since.return_value = [
        AuditEvent(
            id="x",
            session_id="s",
            event_type=EventType.SESSION_START,
            timestamp=SCL.localize(datetime(2026, 5, 8, 10, 0, 0)),
        )
    ]

    resp = client.get(
        "/api/supervisor/audit",
        params={"since": "2026-05-08T00:00:00-04:00"},
    )

    assert resp.status_code == 200
    assert len(resp.json()["events"]) == 1

    # Service got a tz-aware datetime
    received = mock_service.get_audit_since.call_args.args[0]
    assert isinstance(received, datetime)
    assert received.tzinfo is not None
    assert received.year == 2026 and received.month == 5 and received.day == 8


def test_get_audit_missing_since_returns_422(client, mock_service):
    resp = client.get("/api/supervisor/audit")
    assert resp.status_code == 422
    mock_service.get_audit_since.assert_not_called()


# ─── POST /legacy-snapshot ───────────────────────────────────────────────────


def test_legacy_snapshot_returns_written_true_on_first_write(client, mock_service):
    mock_service.record_legacy_snapshot.return_value = True

    resp = client.post(
        "/api/supervisor/legacy-snapshot",
        json={
            "snapshot_id": "snap-1",
            "captured_at": "2026-05-08T09:00:00-04:00",
            "raw": '[{"tag":"X"}]',
            "user_agent": "test/1.0",
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"snapshot_id": "snap-1", "written": True}

    # Service received a LegacySnapshot instance
    received = mock_service.record_legacy_snapshot.call_args.args[0]
    assert isinstance(received, LegacySnapshot)
    assert received.raw == '[{"tag":"X"}]'


def test_legacy_snapshot_returns_written_false_on_duplicate(client, mock_service):
    mock_service.record_legacy_snapshot.return_value = False

    resp = client.post(
        "/api/supervisor/legacy-snapshot",
        json={
            "snapshot_id": "snap-existing",
            "raw": "[]",
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"snapshot_id": "snap-existing", "written": False}
