"""Unit tests for NotasService (v5.1 F-1)."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.exceptions import SpoolNoEncontradoError, WorkerNoEncontradoError
from backend.services.notas_service import NotasService


@pytest.fixture
def mocks(monkeypatch):
    """Shared mocks: freeze today's date, stub all repo/service dependencies."""

    # Freeze today_chile so the YYYYMMDD prefix is deterministic.
    fixed_today = date(2026, 4, 21)
    monkeypatch.setattr(
        "backend.services.notas_service.today_chile",
        lambda: fixed_today,
    )

    sheets_repo = MagicMock()
    metadata_repo = MagicMock()
    worker_service = MagicMock()

    # Default: row resolution succeeds at row 42.
    sheets_repo.find_row_by_column_value.return_value = 42
    sheets_repo._index_to_column_letter.return_value = "G"

    # Default worker exists.
    fake_worker = MagicMock()
    fake_worker.nombre_completo = "MR(93)"
    worker_service.find_worker_by_id.return_value = fake_worker

    # Default ColumnMapCache — patch at call site inside _find_spool_row.
    fake_column_map = {"tagspool": 6}  # TAG_SPOOL normalized
    monkeypatch.setattr(
        "backend.core.column_map_cache.ColumnMapCache.get_or_build",
        lambda sheet_name, repo: fake_column_map,
    )

    return {
        "sheets_repo": sheets_repo,
        "metadata_repo": metadata_repo,
        "worker_service": worker_service,
        "fixed_today": fixed_today,
    }


@pytest.fixture
def service(mocks):
    return NotasService(
        sheets_repository=mocks["sheets_repo"],
        metadata_repository=mocks["metadata_repo"],
        worker_service=mocks["worker_service"],
    )


# ==================== GET ====================


def test_get_nota_returns_empty_string_when_cell_blank(service, mocks):
    mocks["sheets_repo"].get_cell_value.return_value = None
    result = service.get_nota("MK-1923")
    assert result == ""


def test_get_nota_returns_existing_content(service, mocks):
    mocks["sheets_repo"].get_cell_value.return_value = "20260415: lanzada a producción"
    result = service.get_nota("MK-1923")
    assert result == "20260415: lanzada a producción"


def test_get_nota_raises_when_spool_missing(service, mocks):
    # _find_spool_row raises SpoolNoEncontradoError when the row lookup returns None.
    mocks["sheets_repo"].find_row_by_column_value.return_value = None
    with pytest.raises(SpoolNoEncontradoError):
        service.get_nota("DOES-NOT-EXIST")


# ==================== APPEND ====================


def test_append_creates_first_entry_with_yyyymmdd_prefix(service, mocks):
    mocks["sheets_repo"].get_cell_value.return_value = None  # empty cell

    result = service.append_nota(
        tag_spool="MK-1923", worker_id=93, texto="pendiente revisión QC"
    )

    assert result == "20260421: pendiente revisión QC"

    # Sheet write happened with expected value
    mocks["sheets_repo"].update_cell_by_column_name.assert_called_once()
    kwargs = mocks["sheets_repo"].update_cell_by_column_name.call_args.kwargs
    assert kwargs["column_name"] == "Notas"
    assert kwargs["row"] == 42
    assert kwargs["value"] == "20260421: pendiente revisión QC"


def test_append_preserves_existing_history(service, mocks):
    mocks["sheets_repo"].get_cell_value.return_value = (
        "20260415: lanzada a producción"
    )

    result = service.append_nota(
        tag_spool="MK-1923", worker_id=93, texto="refuerzo pedido"
    )

    expected = "20260415: lanzada a producción\n20260421: refuerzo pedido"
    assert result == expected

    kwargs = mocks["sheets_repo"].update_cell_by_column_name.call_args.kwargs
    assert kwargs["value"] == expected


def test_append_writes_audit_event(service, mocks):
    mocks["sheets_repo"].get_cell_value.return_value = None

    service.append_nota(tag_spool="MK-1923", worker_id=93, texto="nota")

    mocks["metadata_repo"].log_event.assert_called_once()
    call_kwargs = mocks["metadata_repo"].log_event.call_args.kwargs
    assert call_kwargs["evento_tipo"] == "NOTAS_ACTUALIZADA"
    assert call_kwargs["tag_spool"] == "MK-1923"
    assert call_kwargs["worker_id"] == 93
    assert call_kwargs["worker_nombre"] == "MR(93)"
    assert "nota" in call_kwargs["metadata_json"]


def test_append_rejects_empty_text(service):
    with pytest.raises(ValueError, match="vacío"):
        service.append_nota(tag_spool="MK-1923", worker_id=93, texto="   ")


def test_append_rejects_unknown_worker(service, mocks):
    mocks["worker_service"].find_worker_by_id.return_value = None
    with pytest.raises(WorkerNoEncontradoError):
        service.append_nota(tag_spool="MK-1923", worker_id=99999, texto="nota")

    # Critical: never wrote to sheet or metadata
    mocks["sheets_repo"].update_cell_by_column_name.assert_not_called()
    mocks["metadata_repo"].log_event.assert_not_called()


def test_append_rejects_unknown_spool(service, mocks):
    # _find_spool_row raises SpoolNoEncontradoError when the row lookup returns None.
    mocks["sheets_repo"].find_row_by_column_value.return_value = None
    with pytest.raises(SpoolNoEncontradoError):
        service.append_nota(tag_spool="DOES-NOT-EXIST", worker_id=93, texto="nota")

    mocks["sheets_repo"].update_cell_by_column_name.assert_not_called()
    mocks["metadata_repo"].log_event.assert_not_called()


def test_append_trims_whitespace_from_text(service, mocks):
    mocks["sheets_repo"].get_cell_value.return_value = None
    result = service.append_nota(
        tag_spool="MK-1923", worker_id=93, texto="  nota con espacios  "
    )
    assert result == "20260421: nota con espacios"


def test_append_does_not_fail_user_write_if_audit_log_fails(service, mocks, caplog):
    """Audit trail errors are logged but don't block the user-facing write."""
    mocks["sheets_repo"].get_cell_value.return_value = None
    mocks["metadata_repo"].log_event.side_effect = RuntimeError("Sheets timeout")

    # Should not raise — note was written to the Sheet successfully
    result = service.append_nota(tag_spool="MK-1923", worker_id=93, texto="nota")

    assert result == "20260421: nota"
    # Sheet write still happened
    mocks["sheets_repo"].update_cell_by_column_name.assert_called_once()
    # Error surfaces in logs
    assert "audit event failed" in caplog.text.lower()


def test_append_allows_none_worker_and_records_anonimo(service, mocks):
    """When worker_id is None the note is still saved and the audit records ANONIMO."""
    mocks["sheets_repo"].get_cell_value.return_value = None

    result = service.append_nota(
        tag_spool="MK-1923", worker_id=None, texto="nota sin firma"
    )

    assert result == "20260421: nota sin firma"
    # Worker lookup must NOT happen when worker_id is None
    mocks["worker_service"].find_worker_by_id.assert_not_called()
    # Sheet write happened with expected value
    mocks["sheets_repo"].update_cell_by_column_name.assert_called_once()
    # Audit event uses worker_id=0 and worker_nombre="ANONIMO"
    audit_kwargs = mocks["metadata_repo"].log_event.call_args.kwargs
    assert audit_kwargs["worker_id"] == 0
    assert audit_kwargs["worker_nombre"] == "ANONIMO"
    assert audit_kwargs["evento_tipo"] == "NOTAS_ACTUALIZADA"


def test_append_with_none_worker_still_requires_non_empty_text(service):
    """Even without a worker, empty text is rejected."""
    with pytest.raises(ValueError, match="vacío"):
        service.append_nota(tag_spool="MK-1923", worker_id=None, texto="   ")
