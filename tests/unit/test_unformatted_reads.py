from __future__ import annotations

"""
Regression tests for UNFORMATTED_VALUE reads.

Background: on 2026-05-12 Matías's tracked cards showed badge "Libre" with
no ARM-progress chip even though Ronnie Reyes had completed ARM the day
before. Root cause: the column `Total_Uniones` in the Operaciones sheet
had cell format "Fecha" applied. Reading with FORMATTED_VALUE (the
default) returned `"1900-01-06"` for the integer 7 (Excel epoch
serialization). The parser tried `int("1900-01-06")` → `null`. The
frontend then could not paint the `ARM 7/7` green chip.

Fix: read with `value_render_option=UNFORMATTED_VALUE`, so the cell
returns its native type (`7` as int). Real date cells now return Excel
serial integers (e.g. `46153` for 2026-05-11), which the extended
`parse_date()` handles natively.

These tests exercise the parsing path end-to-end with UNFORMATTED-shaped
rows.
"""
from datetime import date, datetime
from unittest.mock import Mock

import pytest

from backend.core.column_map_cache import ColumnMapCache
from backend.services.sheets_service import SheetsService


@pytest.fixture(autouse=True)
def reset_cache():
    ColumnMapCache.clear_all()
    yield
    ColumnMapCache.clear_all()


# ----------------------------------------------------------- parse_date


def test_parse_date_accepts_excel_serial_int():
    """Serial 46153 → 2026-05-11 (the day Ronnie completed ARM)."""
    assert SheetsService.parse_date(46153) == date(2026, 5, 11)


def test_parse_date_accepts_excel_serial_float():
    """Serial 46096.0 → 2026-03-15 (Fecha_Materiales for the 6 tracked spools)."""
    assert SheetsService.parse_date(46096.0) == date(2026, 3, 15)


def test_parse_date_still_accepts_dd_mm_yyyy_string():
    """Backward compat: FORMATTED-style strings still parse."""
    assert SheetsService.parse_date("11/5/2026") == date(2026, 5, 11)
    assert SheetsService.parse_date("11-05-2026") == date(2026, 5, 11)
    assert SheetsService.parse_date("2026-05-11") == date(2026, 5, 11)


def test_parse_date_handles_empty_and_none():
    assert SheetsService.parse_date(None) is None
    assert SheetsService.parse_date("") is None
    assert SheetsService.parse_date("  ") is None


def test_parse_date_rejects_booleans():
    """True/False are int subclasses in Python — must NOT be parsed as dates."""
    assert SheetsService.parse_date(True) is None
    assert SheetsService.parse_date(False) is None


def test_parse_date_rejects_garbage_string():
    assert SheetsService.parse_date("not-a-date") is None


# ---------------------------------------------------------- safe_float


def test_safe_float_accepts_native_int():
    assert SheetsService.safe_float(7) == 7.0


def test_safe_float_accepts_native_float():
    assert SheetsService.safe_float(7.5) == 7.5


def test_safe_float_accepts_string():
    assert SheetsService.safe_float("7") == 7.0


def test_safe_float_defaults_on_empty():
    assert SheetsService.safe_float("") == 0.0
    assert SheetsService.safe_float(None) == 0.0


# ------------------------------------------- end-to-end via parse_spool_row


def _build_operaciones_header() -> list[str]:
    """Build a minimal Operaciones header covering the v4.0 critical columns."""
    return [
        "", "NV", "OT", "", "", "SPLIT", "TAG_SPOOL", "",
        # Padding up to index 34 (Fecha_Materiales)
        *[""] * (34 - 8),
        "Fecha_Materiales",       # 34
        "Fecha_Armado",           # 35
        "Armador",                # 36
        "Fecha_Soldadura",        # 37
        "Soldador",               # 38
        "Fecha_QC_Metrologia",    # 39
        # Padding up to index 65 (FLAG / MatSys / Ocupado_Por block)
        *[""] * (65 - 40),
        "FLAG",                   # 65
        "MatSys",                 # 66
        "Ocupado_Por",            # 67
        "Fecha_Ocupacion",        # 68
        "version",                # 69
        "Estado_Detalle",         # 70
        "Total_Uniones",          # 71
        "Uniones_ARM_Completadas",        # 72
        "Uniones_SOLD_Completadas",       # 73
        "Pulgadas_ARM",           # 74
        "Pulgadas_SOLD",          # 75
    ]


def test_parse_spool_row_unformatted_matsys_bug_regression():
    """
    Direct regression test for the bug Matías reported.

    Build an Operaciones row that mimics what UNFORMATTED_VALUE returns for
    the spool MK-1344-TW-27135-001 right now in production:
      - SPLIT, TAG_SPOOL, NV: real strings
      - Total_Uniones: native int 7 (NOT "1900-01-06")
      - Uniones_ARM_Completadas: native int 7
      - Fecha_Armado: Excel serial 46153 (= 2026-05-11)
      - Fecha_Materiales: Excel serial 46096 (= 2026-03-15)
      - Pulgadas_ARM: native float 21.0
      - Ocupado_Por, MatSys: "-" string and empty
    """
    from backend.services.spool_service_v2 import SpoolServiceV2

    header = _build_operaciones_header()
    expected_len = len(header)

    row = [""] * expected_len
    row[1] = "NV0650"
    row[2] = "OT-27135"
    row[5] = "MK-1344-TW-27135-001"   # SPLIT
    row[6] = "MK-1344-TW-27135-001"   # TAG_SPOOL
    row[34] = 46096                    # Fecha_Materiales (serial → 2026-03-15)
    row[35] = 46153                    # Fecha_Armado (serial → 2026-05-11)
    row[36] = "RR(99)"                 # Armador
    row[66] = "-"                      # MatSys (legitimate sentinel)
    row[67] = ""                       # Ocupado_Por (empty → not occupied)
    row[71] = 7                        # Total_Uniones (native int, NOT "1900-01-06")
    row[72] = 7                        # Uniones_ARM_Completadas
    row[73] = 0                        # Uniones_SOLD_Completadas
    row[74] = 21.0                     # Pulgadas_ARM
    row[75] = 0.0                      # Pulgadas_SOLD

    # Build mock repo returning header + row so ColumnMapCache and parsing both work.
    repo = Mock()
    repo.read_worksheet = Mock(return_value=[header, row])

    svc = SpoolServiceV2(sheets_repository=repo)
    spool = svc.parse_spool_row(row)

    assert spool.tag_spool == "MK-1344-TW-27135-001"
    assert spool.total_uniones == 7, (
        f"Total_Uniones must round-trip from native int 7, got {spool.total_uniones!r}"
    )
    assert spool.uniones_arm_completadas == 7
    assert spool.fecha_armado == date(2026, 5, 11)
    assert spool.fecha_materiales == date(2026, 3, 15)
    assert spool.armador == "RR(99)"
    assert spool.ocupado_por is None
    assert spool.pulgadas_arm == 21.0


def test_parse_spool_row_unformatted_handles_string_dates_too():
    """Backward compat: a row built with FORMATTED-style strings still parses."""
    from backend.services.spool_service_v2 import SpoolServiceV2

    header = _build_operaciones_header()
    row = [""] * len(header)
    row[1] = "NV0650"
    row[2] = "OT-27135"
    row[5] = "MK-1344-TW-27135-001"
    row[6] = "MK-1344-TW-27135-001"
    row[34] = "15/3/2026"
    row[35] = "11/5/2026"
    row[36] = "RR(99)"
    row[67] = ""
    row[71] = "7"   # legacy: number as string
    row[72] = "7"
    row[74] = "21.0"

    repo = Mock()
    repo.read_worksheet = Mock(return_value=[header, row])

    svc = SpoolServiceV2(sheets_repository=repo)
    spool = svc.parse_spool_row(row)

    assert spool.total_uniones == 7
    assert spool.fecha_armado == date(2026, 5, 11)
    assert spool.fecha_materiales == date(2026, 3, 15)
    assert spool.pulgadas_arm == 21.0


def test_parse_spool_row_unformatted_empty_numeric_fields():
    """Empty numeric cells must yield None (not 0)."""
    from backend.services.spool_service_v2 import SpoolServiceV2

    header = _build_operaciones_header()
    row = [""] * len(header)
    row[5] = "MK-1344-TW-XXXXX-009"
    row[6] = "MK-1344-TW-XXXXX-009"
    row[34] = ""
    row[35] = ""
    # Total_Uniones not set → empty string

    repo = Mock()
    repo.read_worksheet = Mock(return_value=[header, row])

    svc = SpoolServiceV2(sheets_repository=repo)
    spool = svc.parse_spool_row(row)

    assert spool.total_uniones is None
    assert spool.fecha_armado is None
    assert spool.fecha_materiales is None


# --------------------------------------------------------- parse_datetime
#
# Added with B-001/B-002 fix. Fecha_Ocupacion is the only Spool field that's
# typed Optional[str] AND has a Fecha format applied in Sheets, so it's the
# only field where UNFORMATTED_VALUE leaks a float into Pydantic (which
# rejects float→str). parse_datetime is the canonical helper that absorbs
# both Excel serial floats and string representations and normalizes to a
# datetime, which the caller then formats via format_datetime_for_sheets to
# get a canonical "DD-MM-YYYY HH:MM:SS" string.


def test_parse_datetime_accepts_excel_serial_float():
    """The exact float we saw in Railway logs for MK-1346-TW-28082-011.

    Serial 46155.48180555556 ≈ 2026-05-13 11:33:48. Floating-point math on
    the fractional day can drift the seconds by 1, so we accept that.
    """
    result = SheetsService.parse_datetime(46155.48180555556)
    assert result is not None
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 13
    assert result.hour == 11
    assert result.minute == 33
    assert abs(result.second - 48) <= 1


def test_parse_datetime_accepts_canonical_string():
    """The format the backend writes ('DD-MM-YYYY HH:MM:SS')."""
    assert SheetsService.parse_datetime("13-05-2026 11:33:48") == datetime(
        2026, 5, 13, 11, 33, 48
    )


def test_parse_datetime_accepts_iso_string():
    """ISO 'YYYY-MM-DD HH:MM:SS' fallback."""
    assert SheetsService.parse_datetime("2026-05-13 11:33:48") == datetime(
        2026, 5, 13, 11, 33, 48
    )


def test_parse_datetime_accepts_date_only_fallback():
    """A cell that's a Date (not Datetime) returns midnight."""
    assert SheetsService.parse_datetime("13-05-2026") == datetime(
        2026, 5, 13, 0, 0, 0
    )


def test_parse_datetime_returns_none_on_empty():
    assert SheetsService.parse_datetime("") is None
    assert SheetsService.parse_datetime(None) is None


def test_parse_datetime_returns_none_on_unparseable_string():
    """Garbage in → None out (with WARNING log, not exception)."""
    assert SheetsService.parse_datetime("not a date") is None


def test_parse_datetime_rejects_bool():
    """Booleans subclass int in Python — must NOT be parsed as serials."""
    assert SheetsService.parse_datetime(True) is None
    assert SheetsService.parse_datetime(False) is None


# ---------- B-001/B-002 regression: SpoolDataCorruptError, no silent None
#
# Before the fix, `SheetsRepository.get_spool_by_tag` caught Pydantic
# ValidationError in a bare `except Exception` and returned None. The
# router interpreted None as "spool no encontrado" → 404 falso, and the
# frontend dropped the card silently. Now it must raise
# SpoolDataCorruptError so the router responds 500 with an actionable
# detail and the operator sees a toast.
#
# We assert here on the exception class shape only (the integration path
# through SheetsRepository.get_spool_by_tag requires gspread auth so it's
# verified at the API layer, not in unit tests).


def test_spool_data_corrupt_error_carries_actionable_data():
    """The exception that's now raised must carry tag + detail so the
    router and the frontend can show a useful message."""
    from backend.exceptions import SpoolDataCorruptError

    exc = SpoolDataCorruptError(
        tag_spool="MK-1346-TW-28082-011",
        validation_detail="1 validation error for Spool ...",
    )
    assert exc.error_code == "SPOOL_DATA_CORRUPT"
    assert exc.data["tag_spool"] == "MK-1346-TW-28082-011"
    assert exc.data["validation_detail"].startswith("1 validation error")
    assert "MK-1346-TW-28082-011" in exc.message
