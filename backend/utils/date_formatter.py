"""
Utilidades para formateo de fechas en Google Sheets.

Este módulo centraliza el formateo de fechas para garantizar
consistencia en todo el backend.
"""

from datetime import date


def format_date_for_sheets(date_obj: date) -> str:
    """
    Formatea una fecha en formato DD-MM-YYYY para Google Sheets.

    Args:
        date_obj: Objeto date de Python

    Returns:
        String en formato DD-MM-YYYY (ej: "21-01-2026")

    Examples:
        >>> format_date_for_sheets(date(2026, 1, 21))
        '21-01-2026'
        >>> format_date_for_sheets(date(2025, 12, 10))
        '10-12-2025'
    """
    return date_obj.strftime("%d-%m-%Y")
