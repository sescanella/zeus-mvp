"""Sanitize values before writing to Google Sheets (USER_ENTERED mode)."""


def sanitize_for_sheets(value: str) -> str:
    """Prevent formula injection in Google Sheets.

    Google Sheets USER_ENTERED mode interprets strings starting with
    =, +, -, @ as formulas. Prefix with single quote to force text.
    """
    if isinstance(value, str) and len(value) > 0 and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value
