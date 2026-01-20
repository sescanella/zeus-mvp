"""
Cache estático para mapeo de columnas de Google Sheets.

Este módulo proporciona un cache lazy-loading para los mapeos de columnas
de diferentes hojas de Google Sheets. El cache se construye on-demand
la primera vez que se solicita y se mantiene en memoria para requests subsecuentes.

v2.1 Feature: Dynamic Column Mapping
- Resistente a cambios en estructura de Google Sheets
- Lazy loading por defecto, con opción de pre-warming en startup
- Multi-sheet support (Operaciones, Trabajadores, Roles)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ColumnMapCache:
    """
    Cache estático para mapeos de columnas de Google Sheets.

    NO es un singleton - es una clase stateless con cache de clase.
    Esto facilita testing (se puede limpiar el cache) y no introduce
    dependencias de estado global.

    Usage:
        # Obtener column_map (lazy load si no existe)
        from backend.core.column_map_cache import ColumnMapCache

        column_map = ColumnMapCache.get_or_build(
            sheet_name="Operaciones",
            sheets_repository=sheets_repo
        )

        # Usar en SheetsService
        sheets_service = SheetsService(column_map=column_map)

        # Invalidar cache (si estructura cambia)
        ColumnMapCache.invalidate("Operaciones")

        # Limpiar todo (para tests)
        ColumnMapCache.clear_all()
    """

    # Cache: {sheet_name: {column_name_normalized: index}}
    _cache: dict[str, dict[str, int]] = {}

    @classmethod
    def get_or_build(
        cls,
        sheet_name: str,
        sheets_repository
    ) -> dict[str, int]:
        """
        Obtiene el column_map del cache, o lo construye si no existe.

        Este método es thread-safe para lecturas (Python GIL).
        Si se llama concurrentemente para la misma hoja, puede construirse
        múltiples veces, pero el resultado es idempotente.

        Args:
            sheet_name: Nombre de la hoja (ej: "Operaciones", "Trabajadores")
            sheets_repository: Repositorio para leer la hoja

        Returns:
            dict[str, int]: Mapeo {nombre_columna_normalizado: índice}

        Raises:
            Exception: Si falla la lectura de Google Sheets

        Examples:
            >>> column_map = ColumnMapCache.get_or_build("Operaciones", repo)
            >>> column_map["armador"]  # Returns: 34
            >>> column_map["fechaarmado"]  # Returns: 33
        """
        # Si ya está en cache, retornar
        if sheet_name in cls._cache:
            logger.debug(f"Column map cache HIT for '{sheet_name}' ({len(cls._cache[sheet_name])} columns)")
            return cls._cache[sheet_name]

        # Cache MISS - construir mapeo
        logger.info(f"Column map cache MISS for '{sheet_name}' - building...")

        try:
            # Leer todas las filas (incluye header en row 0)
            all_rows = sheets_repository.read_worksheet(sheet_name)

            if not all_rows or len(all_rows) == 0:
                raise ValueError(f"Sheet '{sheet_name}' is empty")

            # Extraer header (primera fila)
            header_row = all_rows[0]

            # Construir mapeo usando SheetsService.build_column_map()
            # (importación lazy para evitar circular dependency)
            from backend.services.sheets_service import SheetsService
            column_map = SheetsService.build_column_map(header_row)

            # Guardar en cache
            cls._cache[sheet_name] = column_map

            logger.info(
                f"Column map built for '{sheet_name}': {len(column_map)} columns detected"
            )
            logger.debug(
                f"Columns in '{sheet_name}': {', '.join(sorted(column_map.keys())[:10])}..."
            )

            return column_map

        except Exception as e:
            logger.error(
                f"Failed to build column map for '{sheet_name}': {e}",
                exc_info=True
            )
            raise

    @classmethod
    def invalidate(cls, sheet_name: str) -> None:
        """
        Invalida el cache para una hoja específica.

        Útil si se detecta que la estructura de la hoja cambió durante
        la ejecución de la aplicación (caso raro en producción).

        Args:
            sheet_name: Nombre de la hoja a invalidar

        Examples:
            >>> ColumnMapCache.invalidate("Operaciones")
            >>> # Próxima llamada a get_or_build() reconstruirá el mapeo
        """
        if sheet_name in cls._cache:
            del cls._cache[sheet_name]
            logger.info(f"Column map cache invalidated for '{sheet_name}'")
        else:
            logger.debug(f"Column map cache invalidation skipped (not cached): '{sheet_name}'")

    @classmethod
    def clear_all(cls) -> None:
        """
        Limpia todo el cache.

        Útil principalmente para tests, para asegurar aislamiento entre
        diferentes casos de prueba.

        Examples:
            >>> # En pytest fixture
            >>> @pytest.fixture(autouse=True)
            >>> def clear_cache():
            >>>     ColumnMapCache.clear_all()
        """
        cls._cache.clear()
        logger.debug("Column map cache cleared (all sheets)")

    @classmethod
    def get_cached_sheets(cls) -> list[str]:
        """
        Retorna la lista de hojas que están actualmente en cache.

        Útil para debugging y monitoring.

        Returns:
            list[str]: Nombres de hojas cacheadas

        Examples:
            >>> ColumnMapCache.get_cached_sheets()
            ['Operaciones', 'Trabajadores']
        """
        return list(cls._cache.keys())

    @classmethod
    def get_column_count(cls, sheet_name: str) -> Optional[int]:
        """
        Retorna el número de columnas detectadas para una hoja.

        Args:
            sheet_name: Nombre de la hoja

        Returns:
            int si la hoja está cacheada, None si no

        Examples:
            >>> ColumnMapCache.get_column_count("Operaciones")
            62
        """
        if sheet_name in cls._cache:
            return len(cls._cache[sheet_name])
        return None

    @classmethod
    def validate_critical_columns(
        cls,
        sheet_name: str,
        required_columns: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Valida que columnas críticas estén presentes en el mapeo.

        Args:
            sheet_name: Nombre de la hoja
            required_columns: Lista de nombres de columnas requeridas (sin normalizar)

        Returns:
            tuple[bool, list[str]]: (todas_presentes, columnas_faltantes)

        Examples:
            >>> ok, missing = ColumnMapCache.validate_critical_columns(
            ...     "Operaciones",
            ...     ["TAG_SPOOL", "Armador", "Soldador"]
            ... )
            >>> if not ok:
            ...     logger.error(f"Missing columns: {missing}")
        """
        if sheet_name not in cls._cache:
            logger.warning(f"Cannot validate columns for uncached sheet: '{sheet_name}'")
            return False, required_columns

        column_map = cls._cache[sheet_name]

        # Normalizar nombres requeridos para búsqueda
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "")

        missing_columns = []
        for col_name in required_columns:
            normalized = normalize(col_name)
            if normalized not in column_map:
                missing_columns.append(col_name)

        all_present = len(missing_columns) == 0

        if all_present:
            logger.debug(
                f"All {len(required_columns)} critical columns found in '{sheet_name}'"
            )
        else:
            logger.error(
                f"Missing {len(missing_columns)} critical columns in '{sheet_name}': {missing_columns}"
            )

        return all_present, missing_columns
