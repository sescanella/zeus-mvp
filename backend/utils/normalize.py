"""
Centralized column name normalization for Google Sheets lookups.

All column name normalization MUST use this function to ensure consistency
with ColumnMapCache keys. The function strips accents, lowercases, and
removes spaces/underscores/slashes.

Usage:
    from backend.utils.normalize import normalize_column_name

    normalized = normalize_column_name("Fecha_QC_Metrología")
    # Returns: "fechaqcmetrologia"
"""
import unicodedata


def normalize_column_name(name: str) -> str:
    """
    Normalize a column name for cache-consistent lookup.

    Strips accents (NFKD decomposition), lowercases, removes spaces,
    underscores, and slashes. This MUST match the normalization used
    by ColumnMapCache.get_or_build() and SheetsService.build_column_map().

    Args:
        name: Column name from Google Sheets header or code reference

    Returns:
        Normalized string for column_map lookup

    Examples:
        >>> normalize_column_name("Fecha_QC_Metrología")
        'fechaqcmetrologia'
        >>> normalize_column_name("TAG_SPOOL")
        'tagspool'
        >>> normalize_column_name("Ocupado_Por")
        'ocupadopor'
    """
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().replace(" ", "").replace("_", "").replace("/", "")
