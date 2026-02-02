"""
Version detection utilities for v3.0 vs v4.0 spool identification.

Simple helpers for determining if a spool is v3.0 (no unions) or v4.0 (has unions).
Used by v4.0 routers to route requests appropriately.

Reference:
- Plan: 11-01-PLAN.md
- Full service: backend/services/version_detection_service.py (Phase 9)
"""
from typing import Dict, Any


def is_v4_spool(spool_data: dict) -> bool:
    """
    Detect if spool is v4.0 (has unions) or v3.0 (no unions).

    A spool is considered v4.0 if it has Total_Uniones > 0.
    This indicates that union-level tracking is enabled.

    Args:
        spool_data: Dictionary with spool data (must include Total_Uniones key)

    Returns:
        bool: True if v4.0 spool (has unions), False if v3.0 spool (no unions)

    Example:
        >>> is_v4_spool({"TAG_SPOOL": "OT-123", "Total_Uniones": "5"})
        True
        >>> is_v4_spool({"TAG_SPOOL": "TEST-02", "Total_Uniones": "0"})
        False
        >>> is_v4_spool({"TAG_SPOOL": "TEST-02", "Total_Uniones": None})
        False
    """
    total_uniones = spool_data.get("Total_Uniones")

    # None or empty string = v3.0 spool
    if total_uniones is None or total_uniones == "":
        return False

    # Convert to int and check if > 0
    try:
        return int(total_uniones) > 0
    except (ValueError, TypeError):
        # Invalid value = treat as v3.0
        return False


def get_spool_version(spool_data: dict) -> str:
    """
    Return spool version string ("v3.0" or "v4.0").

    Args:
        spool_data: Dictionary with spool data (must include Total_Uniones key)

    Returns:
        str: "v4.0" if has unions, "v3.0" if no unions

    Example:
        >>> get_spool_version({"TAG_SPOOL": "OT-123", "Total_Uniones": "5"})
        'v4.0'
        >>> get_spool_version({"TAG_SPOOL": "TEST-02", "Total_Uniones": "0"})
        'v3.0'
    """
    return "v4.0" if is_v4_spool(spool_data) else "v3.0"


def format_version_badge(spool_data: dict) -> Dict[str, Any]:
    """
    Format version information for UI display.

    Returns a dict with version string and badge color.

    Args:
        spool_data: Dictionary with spool data (must include Total_Uniones key)

    Returns:
        dict: {"version": "v4.0", "color": "green"} or {"version": "v3.0", "color": "gray"}

    Example:
        >>> format_version_badge({"TAG_SPOOL": "OT-123", "Total_Uniones": "5"})
        {'version': 'v4.0', 'color': 'green'}
        >>> format_version_badge({"TAG_SPOOL": "TEST-02", "Total_Uniones": "0"})
        {'version': 'v3.0', 'color': 'gray'}
    """
    version = get_spool_version(spool_data)
    return {
        "version": version,
        "color": "green" if version == "v4.0" else "gray"
    }
