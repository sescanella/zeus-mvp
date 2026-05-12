"""
Cache estático para mapeo de columnas de Google Sheets, resiliente ante
inserción/eliminación de columnas no críticas en la planilla.

Estrategia: cada entrada del caché almacena, además del column_map, un
hash del header con el que se construyó. Al llamar
`get_or_rebuild_if_changed(sheet_name, header_row, ...)` se compara el
hash del header recién leído contra el cacheado. Si difiere, el caché se
reconstruye automáticamente con el header nuevo (cero llamadas extras a
Sheets — el header ya está en memoria como parte de la lectura que
gatilló la verificación).

Si al reconstruir una columna crítica del schema (ver
`backend/core/sheet_schema.py`) ya no está, se lanza
`CriticalColumnDriftError` (HTTP 503) en vez de servir índices viejos.

Concurrencia: un `threading.Lock` a nivel de módulo garantiza que dos
requests que detecten drift simultáneo no reconstruyan a la vez. El
segundo entra, ve el hash nuevo en caché y salta el rebuild.
"""
import hashlib
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


_HEADER_HASH_SEPARATOR = "␟"  # U+241F SYMBOL FOR UNIT SEPARATOR
_lock = threading.Lock()


@dataclass(frozen=True)
class _CacheEntry:
    column_map: dict[str, int]
    header_hash: str
    header_row: tuple[str, ...]
    built_at_utc: datetime


def _hash_header(header_row: list[str]) -> str:
    payload = _HEADER_HASH_SEPARATOR.join((c or "") for c in header_row)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ColumnMapCache:
    """
    Cache estático para mapeos de columnas de Google Sheets.

    NO es un singleton — es una clase stateless con cache de clase. Esto
    facilita testing (se puede limpiar el cache) y no introduce dependencias
    de estado global.

    Usage:
        from backend.core.column_map_cache import ColumnMapCache

        # Construcción lazy (al primer uso o si el caché fue invalidado)
        column_map = ColumnMapCache.get_or_build("Operaciones", sheets_repo)

        # Verificación con header recién leído (auto-rebuild si difiere)
        ColumnMapCache.get_or_rebuild_if_changed(
            "Operaciones", header_row, sheets_repo,
        )

        # Invalidación manual
        ColumnMapCache.invalidate("Operaciones")

        # Reset total (para tests)
        ColumnMapCache.clear_all()
    """

    # Cache: {sheet_name: _CacheEntry}
    _cache: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------ build

    @classmethod
    def get_or_build(
        cls,
        sheet_name: str,
        sheets_repository,
    ) -> dict[str, int]:
        """
        Obtiene el column_map del cache, o lo construye si no existe.

        Args:
            sheet_name: Nombre de la hoja (ej: "Operaciones", "Trabajadores").
            sheets_repository: Repositorio para leer la hoja.

        Returns:
            dict[str, int]: Mapeo {nombre_columna_normalizado: índice}.

        Raises:
            Exception: Si falla la lectura de Google Sheets.
            CriticalColumnDriftError: Si tras leer header se detecta que
                falta una columna crítica del schema.
        """
        with _lock:
            entry = cls._cache.get(sheet_name)
            if entry is not None:
                logger.debug(
                    f"Column map cache HIT for '{sheet_name}' "
                    f"({len(entry.column_map)} columns)"
                )
                return entry.column_map

        logger.info(f"Column map cache MISS for '{sheet_name}' - building...")

        all_rows = sheets_repository.read_worksheet(sheet_name)

        # If read_worksheet itself populated the cache via
        # `get_or_rebuild_if_changed`, return that result without rebuilding.
        with _lock:
            entry = cls._cache.get(sheet_name)
            if entry is not None:
                return entry.column_map

        if not all_rows:
            raise ValueError(f"Sheet '{sheet_name}' is empty")

        header_row = all_rows[0]
        return cls._build_and_store(sheet_name, header_row)

    @classmethod
    def get_or_rebuild_if_changed(
        cls,
        sheet_name: str,
        header_row: list[str],
        sheets_repository=None,
    ) -> dict[str, int]:
        """
        Asegura que el caché refleja el `header_row` provisto.

        Se llama desde `SheetsRepository.read_worksheet()` con la primera
        fila de la planilla recién leída. Si el hash no coincide con el
        cacheado (o no había caché), reconstruye atómicamente.

        Args:
            sheet_name: Nombre de la hoja.
            header_row: Primera fila de la planilla (recién leída).
            sheets_repository: Reservado para usos futuros (no se usa hoy).

        Returns:
            dict[str, int]: column_map vigente.

        Raises:
            CriticalColumnDriftError: Si una columna crítica del schema
                falta o no coincide con su posición esperada tras rebuild.
        """
        new_hash = _hash_header(header_row)

        with _lock:
            entry = cls._cache.get(sheet_name)
            if entry is not None and entry.header_hash == new_hash:
                return entry.column_map
            return cls._rebuild_locked(sheet_name, header_row, new_hash)

    @classmethod
    def _build_and_store(
        cls,
        sheet_name: str,
        header_row: list[str],
    ) -> dict[str, int]:
        new_hash = _hash_header(header_row)
        with _lock:
            return cls._rebuild_locked(sheet_name, header_row, new_hash)

    @classmethod
    def _rebuild_locked(
        cls,
        sheet_name: str,
        header_row: list[str],
        new_hash: str,
    ) -> dict[str, int]:
        """Internal: caller MUST hold _lock."""
        # Lazy import to avoid circular dependency
        from backend.services.sheets_service import SheetsService

        column_map = SheetsService.build_column_map(header_row)

        # Round-trip validation against the schema registry (if any).
        # On critical drift we keep the OLD cache entry (do not store the new
        # one) and raise — the system serves 503 rather than data with a wrong
        # column.
        cls._validate_critical_or_raise(sheet_name, column_map, header_row)

        cls._cache[sheet_name] = _CacheEntry(
            column_map=column_map,
            header_hash=new_hash,
            header_row=tuple(header_row),
            built_at_utc=datetime.now(timezone.utc),
        )

        logger.info(
            f"Column map rebuilt for '{sheet_name}': "
            f"{len(column_map)} entries, {len(header_row)} cols in header"
        )
        return column_map

    # --------------------------------------------------------- validation

    @classmethod
    def _validate_critical_or_raise(
        cls,
        sheet_name: str,
        column_map: dict[str, int],
        header_row: list[str],
    ) -> None:
        """
        Para cada columna crítica declarada en ALL_SCHEMAS[sheet_name],
        verifica que:
          (a) está presente en column_map (presence check), y
          (b) el header en esa posición normaliza al mismo nombre crítico
              (round-trip check — pesca colisiones por normalización).

        Si alguna falla, lanza CriticalColumnDriftError SIN escribir el
        nuevo caché. La caller (`_rebuild_locked`) deja la entrada vieja
        intacta.
        """
        try:
            from backend.core.sheet_schema import ALL_SCHEMAS
        except ImportError:
            return  # schema registry not installed; skip strict checks

        schema = ALL_SCHEMAS.get(sheet_name)
        if schema is None:
            return

        from backend.exceptions import CriticalColumnDriftError
        from backend.utils.normalize import normalize_column_name as _norm

        for required in schema.critical_columns:
            normalized = _norm(required)
            idx = column_map.get(normalized)
            if idx is None:
                raise CriticalColumnDriftError(
                    sheet_name=sheet_name,
                    expected_column=required,
                    actual_header_at_index=None,
                )
            actual_header = header_row[idx] if 0 <= idx < len(header_row) else None
            if actual_header is None or _norm(actual_header) != normalized:
                raise CriticalColumnDriftError(
                    sheet_name=sheet_name,
                    expected_column=required,
                    actual_header_at_index=actual_header,
                )

    @classmethod
    def validate_critical_columns(
        cls,
        sheet_name: str,
        required_columns: list[str],
    ) -> tuple[bool, list[str]]:
        """
        Backwards-compatible presence-only check against the cached map.

        Returns:
            (all_present, missing_columns)
        """
        with _lock:
            entry = cls._cache.get(sheet_name)
        if entry is None:
            logger.warning(
                f"Cannot validate columns for uncached sheet: '{sheet_name}'"
            )
            return False, list(required_columns)

        from backend.utils.normalize import normalize_column_name as _norm

        missing = [c for c in required_columns if _norm(c) not in entry.column_map]
        all_present = not missing

        if all_present:
            logger.debug(
                f"All {len(required_columns)} critical columns found in '{sheet_name}'"
            )
        else:
            logger.error(
                f"Missing {len(missing)} critical columns in '{sheet_name}': {missing}"
            )
        return all_present, missing

    @classmethod
    def validate_critical_columns_strict(
        cls,
        sheet_name: str,
        required_columns: list[str],
    ) -> tuple[bool, list[dict]]:
        """
        Round-trip strict check: for each required column, verify that
        header_row[column_map[normalize(col)]] normalizes back to `col`.

        Catches normalize() collisions where two distinct columns map to
        the same key.

        Returns:
            (ok, drifts) — `drifts` is a list of dicts with keys
            `expected`, `actual_header`, `index` describing each mismatch.
        """
        with _lock:
            entry = cls._cache.get(sheet_name)
        if entry is None:
            return False, [{"expected": c, "actual_header": None, "index": None}
                           for c in required_columns]

        from backend.utils.normalize import normalize_column_name as _norm

        header_row = entry.header_row
        column_map = entry.column_map
        drifts: list[dict] = []

        for required in required_columns:
            normalized = _norm(required)
            idx = column_map.get(normalized)
            if idx is None:
                drifts.append({"expected": required, "actual_header": None, "index": None})
                continue
            actual = header_row[idx] if 0 <= idx < len(header_row) else None
            if actual is None or _norm(actual) != normalized:
                drifts.append({
                    "expected": required,
                    "actual_header": actual,
                    "index": idx,
                })

        return (len(drifts) == 0), drifts

    # ----------------------------------------------------- invalidation

    @classmethod
    def invalidate(cls, sheet_name: str) -> None:
        """Invalidate the cache for one sheet."""
        with _lock:
            if sheet_name in cls._cache:
                del cls._cache[sheet_name]
                logger.info(f"Column map cache invalidated for '{sheet_name}'")
            else:
                logger.debug(
                    f"Column map cache invalidation skipped (not cached): '{sheet_name}'"
                )

    @classmethod
    def clear_all(cls) -> None:
        """Clear the entire cache (used in tests)."""
        with _lock:
            cls._cache.clear()
        logger.debug("Column map cache cleared (all sheets)")

    # ----------------------------------------------------------- inspect

    @classmethod
    def get_cached_sheets(cls) -> list[str]:
        with _lock:
            return list(cls._cache.keys())

    @classmethod
    def get_column_count(cls, sheet_name: str) -> Optional[int]:
        with _lock:
            entry = cls._cache.get(sheet_name)
        return len(entry.column_map) if entry is not None else None

    @classmethod
    def get_header_hash(cls, sheet_name: str) -> Optional[str]:
        with _lock:
            entry = cls._cache.get(sheet_name)
        return entry.header_hash if entry is not None else None

    @classmethod
    def get_built_at(cls, sheet_name: str) -> Optional[datetime]:
        with _lock:
            entry = cls._cache.get(sheet_name)
        return entry.built_at_utc if entry is not None else None
