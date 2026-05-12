from __future__ import annotations

"""
Regression + behaviour tests for the drift-resilient ColumnMapCache.

Background: a real production incident on 2026-05-12 corrupted the
AÑADIR SPOOL workflow because Engineering inserted a new column
(`MatSys`) between `FLAG` and `Ocupado_Por` in the Operaciones sheet.
The backend's ColumnMapCache had been built once at process startup and
never refreshed, so `Ocupado_Por` was still looked up at the OLD index
(now occupied by `MatSys`, which contained `"-"`). The OcupacionFilter
saw `"-"` and excluded every spool as "ocupado". The 18 tags Matías
listed in chat were all genuinely available but invisible to the modal.

The fix makes `read_worksheet()` hash the header on every call and
rebuild the column map atomically when the hash changes. Critical
columns (declared in `backend/core/sheet_schema.py`) MUST be present
after every rebuild — otherwise the rebuild raises
`CriticalColumnDriftError` and the request surfaces HTTP 503 rather
than serving wrong data.
"""
from unittest.mock import Mock

import pytest

from backend.core.column_map_cache import ColumnMapCache
from backend.core.sheet_schema import ALL_SCHEMAS
from backend.exceptions import CriticalColumnDriftError
from backend.services.sheets_service import SheetsService


@pytest.fixture(autouse=True)
def reset_cache():
    """Each test starts with an empty column-map cache."""
    ColumnMapCache.clear_all()
    yield
    ColumnMapCache.clear_all()


def _operaciones_header_pre_matsys() -> list[str]:
    """76-col header BEFORE the MatSys insertion. Mirrors PROD on 2026-05-11."""
    cols: list[str] = [""] * 76
    cols[1] = "NV"
    cols[2] = "OT"
    cols[5] = "SPLIT"
    cols[6] = "TAG_SPOOL"
    cols[34] = "Fecha_Materiales"
    cols[35] = "Fecha_Armado"
    cols[36] = "Armador"
    cols[37] = "Fecha_Soldadura"
    cols[38] = "Soldador"
    cols[39] = "Fecha_QC_Metrologia"
    cols[65] = "FLAG"
    cols[66] = "Ocupado_Por"
    cols[67] = "Fecha_Ocupacion"
    cols[68] = "version"
    cols[69] = "Estado_Detalle"
    return cols


def _operaciones_header_with_matsys() -> list[str]:
    """77-col header AFTER MatSys was inserted between FLAG and Ocupado_Por."""
    pre = _operaciones_header_pre_matsys()
    return pre[:66] + ["MatSys"] + pre[66:]


def _build_repo_returning(header_row: list[str], extra_rows: list[list[str]] | None = None) -> Mock:
    """Build a Mock SheetsRepository whose read_worksheet returns a fake sheet."""
    repo = Mock()
    rows = [header_row] + (extra_rows or [])
    repo.read_worksheet = Mock(return_value=rows)
    return repo


# ---------------------------------------------------------------- 1


def test_header_hash_changes_on_column_insert():
    """Inserting a column shifts indices; the cache must rebuild on next read."""
    old = _operaciones_header_pre_matsys()
    new = _operaciones_header_with_matsys()

    ColumnMapCache.get_or_rebuild_if_changed("Operaciones", old)
    old_hash = ColumnMapCache.get_header_hash("Operaciones")
    assert ColumnMapCache.get_column_count("Operaciones") is not None

    ColumnMapCache.get_or_rebuild_if_changed("Operaciones", new)
    new_hash = ColumnMapCache.get_header_hash("Operaciones")

    assert new_hash != old_hash, "Header hash must change when a column is inserted"


# ---------------------------------------------------------------- 2


def test_critical_column_rename_raises():
    """Renaming Armador to ArmadorXX must raise CriticalColumnDriftError."""
    header = _operaciones_header_pre_matsys()
    header[36] = "ArmadorXX"  # rename critical column

    with pytest.raises(CriticalColumnDriftError) as exc:
        ColumnMapCache.get_or_rebuild_if_changed("Operaciones", header)

    assert exc.value.data["sheet_name"] == "Operaciones"
    assert exc.value.data["expected_column"] == "Armador"


# ---------------------------------------------------------------- 3


def test_non_critical_column_removal_no_error():
    """Removing a non-critical column (FLAG is not in the schema) is fine."""
    header = _operaciones_header_pre_matsys()
    # FLAG (idx 65) is NOT in OPERACIONES_SCHEMA.critical_columns. Remove it.
    header.pop(65)

    # Must not raise — Ocupado_Por et al. shifted left but they're still valid.
    column_map = ColumnMapCache.get_or_rebuild_if_changed("Operaciones", header)

    from backend.utils.normalize import normalize_column_name as _norm
    assert column_map[_norm("Ocupado_Por")] == 65  # was 66, now 65 (one shift)
    assert column_map[_norm("Estado_Detalle")] == 68  # was 69, now 68


# ---------------------------------------------------------------- 4 (regression)


def test_parse_spool_row_after_column_insert_reads_correct_ocupado_por():
    """
    Regression test for the real 2026-05-12 bug.

    Sequence: cache is warmed with the 76-col header. Then Engineering
    inserts the `MatSys` column. On the next read, the cache must rebuild
    so that `Ocupado_Por` resolves to its NEW index (67), not the old one
    (66, now occupied by `MatSys`).
    """
    # 1) Warm cache with pre-MatSys header
    pre = _operaciones_header_pre_matsys()
    ColumnMapCache.get_or_rebuild_if_changed("Operaciones", pre)
    assert ColumnMapCache.get_column_count("Operaciones") is not None

    # 2) Engineering inserts MatSys → headers shift right by 1 from idx 66
    new_header = _operaciones_header_with_matsys()

    # 3) Build a row matching the NEW header: MatSys="-", Ocupado_Por="".
    row = [""] * len(new_header)
    row[5] = "MK-1344-TW-27123-001"  # SPLIT
    row[6] = "MK-1344-TW-27123-001"  # TAG_SPOOL
    row[66] = "-"   # MatSys (new column inserted here)
    row[67] = ""    # Ocupado_Por (genuinely empty in PROD)

    # 4) The next read_worksheet returns header_new + row. The drift hook
    #    rebuilds the cache.
    ColumnMapCache.get_or_rebuild_if_changed("Operaciones", new_header)

    # 5) A SheetsService built against the cache must now resolve
    #    `Ocupado_Por` to index 67 — and the value at that index in the
    #    new row is "" (empty), NOT "-" (which would be the bug).
    from backend.utils.normalize import normalize_column_name as _norm
    column_map = ColumnMapCache.get_or_build("Operaciones", _build_repo_returning(new_header, [row]))
    ocupado_idx = column_map[_norm("Ocupado_Por")]

    assert ocupado_idx == 67, "Ocupado_Por must point to its NEW index after rebuild"
    assert row[ocupado_idx] == "", (
        "Reading row at the rebuilt index must return the actual Ocupado_Por "
        f"value (empty), not the MatSys sentinel — got {row[ocupado_idx]!r}"
    )


# ---------------------------------------------------------------- 5


def test_sheets_service_property_refreshes_after_invalidation():
    """SheetsService._column_map property must reflect cache invalidation."""
    header_v1 = _operaciones_header_pre_matsys()
    header_v2 = _operaciones_header_with_matsys()

    repo = _build_repo_returning(header_v1)
    service = SheetsService(sheet_name="Operaciones", sheets_repository=repo)

    # First snapshot
    from backend.utils.normalize import normalize_column_name as _norm
    map_v1 = service._column_map
    assert map_v1[_norm("Ocupado_Por")] == 66

    # Simulate Engineering inserting MatSys: repo now returns the new header
    repo.read_worksheet = Mock(return_value=[header_v2])
    ColumnMapCache.invalidate("Operaciones")

    # The property must rebuild from the new header on next access
    map_v2 = service._column_map
    assert map_v2[_norm("Ocupado_Por")] == 67, (
        "Property must observe the cache rebuild, not return a stale snapshot"
    )


# ---------------------------------------------------------------- 6


def test_admin_endpoint_invalidates(monkeypatch):
    """POST /api/admin/invalidate-column-cache invalidates + rebuilds + returns drift info."""
    from fastapi.testclient import TestClient

    # Build a tiny FastAPI app that only mounts the admin router so the test
    # does not depend on main.py side-effects (startup pre-warm).
    from fastapi import FastAPI
    from backend.routers import admin as admin_router
    from backend.core.dependency import get_sheets_repository

    repo = _build_repo_returning(_operaciones_header_pre_matsys())
    app = FastAPI()
    app.include_router(admin_router.router, prefix="/api")
    app.dependency_overrides[get_sheets_repository] = lambda: repo

    client = TestClient(app)
    resp = client.post("/api/admin/invalidate-column-cache?sheet=Operaciones")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["invalidated"] is True
    assert body["critical_ok"] is True
    assert body["column_count"] > 0


# ---------------------------------------------------------------- 7


def test_critical_column_missing_at_build_raises():
    """If a critical column is absent from the header, build raises."""
    header = _operaciones_header_pre_matsys()
    header[5] = ""  # remove SPLIT (critical)
    header[6] = ""  # remove TAG_SPOOL (critical)

    repo = _build_repo_returning(header)
    with pytest.raises(CriticalColumnDriftError):
        ColumnMapCache.get_or_build("Operaciones", repo)


# ---------------------------------------------------------------- 8


def test_repeated_reads_with_same_header_no_rebuild():
    """100 reads with an identical header must rebuild only once."""
    header = _operaciones_header_pre_matsys()

    # First call: cache MISS → rebuild
    ColumnMapCache.get_or_rebuild_if_changed("Operaciones", header)
    first_built_at = ColumnMapCache.get_built_at("Operaciones")
    assert first_built_at is not None

    # 99 more calls with the same header must NOT rebuild
    for _ in range(99):
        ColumnMapCache.get_or_rebuild_if_changed("Operaciones", header)

    assert ColumnMapCache.get_built_at("Operaciones") == first_built_at, (
        "Cache must not rebuild when the header hash is unchanged"
    )


# --------------------------------------------------------- schema sanity


def test_all_schemas_have_critical_columns():
    """Sanity check: every schema in the registry must declare at least one critical column."""
    assert ALL_SCHEMAS, "ALL_SCHEMAS registry must not be empty"
    for name, schema in ALL_SCHEMAS.items():
        assert schema.critical_columns, f"{name} schema must declare critical_columns"
