"""
Utilidades para formateo de fechas en Google Sheets.

Este módulo centraliza el formateo de fechas para garantizar
consistencia en todo el backend.

v2.1: Agrega soporte para timezone (America/Santiago).
"""

from datetime import date, datetime
import pytz
from backend.config import config


def get_timezone() -> pytz.timezone:
    """
    Obtiene el timezone configurado del sistema.

    Returns:
        pytz.timezone: Timezone configurado (default: America/Santiago)

    Examples:
        >>> tz = get_timezone()
        >>> tz.zone
        'America/Santiago'
    """
    return pytz.timezone(config.TIMEZONE)


def now_chile() -> datetime:
    """
    Obtiene la fecha y hora actual en timezone de Chile.

    Returns:
        datetime: Datetime actual en timezone America/Santiago

    Examples:
        >>> dt = now_chile()
        >>> dt.tzinfo.zone
        'America/Santiago'
    """
    tz = get_timezone()
    return datetime.now(tz)


def today_chile() -> date:
    """
    Obtiene la fecha actual en timezone de Chile.

    Returns:
        date: Fecha actual en timezone America/Santiago

    Examples:
        >>> d = today_chile()
        >>> isinstance(d, date)
        True
    """
    return now_chile().date()


def format_date_for_sheets(date_obj: date) -> str:
    """
    Formatea una fecha en formato DD-MM-YYYY para Google Sheets.

    IMPORTANTE: Google Sheets interpretará este formato como fecha
    solo si se usa value_input_option='USER_ENTERED'.

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


def format_datetime_for_sheets(dt: datetime) -> str:
    """
    Formatea un datetime en formato DD-MM-YYYY HH:MM:SS para Google Sheets.

    IMPORTANTE: Google Sheets interpretará este formato como datetime
    solo si se usa value_input_option='USER_ENTERED'.

    Args:
        dt: Objeto datetime de Python (puede ser timezone-aware o naive)

    Returns:
        String en formato DD-MM-YYYY HH:MM:SS (ej: "21-01-2026 14:30:00")

    Examples:
        >>> dt = datetime(2026, 1, 21, 14, 30, 0)
        >>> format_datetime_for_sheets(dt)
        '21-01-2026 14:30:00'
    """
    return dt.strftime("%d-%m-%Y %H:%M:%S")
