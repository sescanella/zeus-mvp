"""Sanitize values before writing to Google Sheets (USER_ENTERED mode)."""

from typing import Any


def sanitize_for_sheets(value: Any) -> Any:
    """Prevent formula injection in Google Sheets.

    Google Sheets USER_ENTERED mode interprets strings starting with
    =, +, -, @ as formulas. Prefix with single quote to force text.

    Non-string values (int, float, None, bool) pass through unchanged.
    """
    if isinstance(value, str) and len(value) > 0 and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value


def sanitize_row_for_sheets(row: list) -> list:
    """Sanitize all string values in a row before writing to Sheets.

    Applies sanitize_for_sheets to each element.  Non-string values
    (int, float, None) pass through unchanged.

    Args:
        row: List of values representing a sheet row.

    Returns:
        New list with all string values sanitized.
    """
    return [sanitize_for_sheets(v) for v in row]
