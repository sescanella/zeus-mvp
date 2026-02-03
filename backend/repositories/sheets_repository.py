"""
Repositorio para acceso a Google Sheets usando gspread.

Maneja toda la comunicación con la API de Google Sheets,
incluyendo autenticación, lectura y escritura de datos.
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import Optional
from datetime import datetime, date
import logging
from functools import wraps
import time

from backend.config import config
from backend.exceptions import SheetsConnectionError, SheetsUpdateError
from backend.utils.cache import get_cache


def retry_on_sheets_error(max_retries: int = 3, backoff_seconds: float = 1.0):
    """
    Decorator para reintentar operaciones de Sheets con backoff exponencial.

    Args:
        max_retries: Número máximo de reintentos
        backoff_seconds: Segundos base para espera (se duplica en cada reintento)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except gspread.exceptions.APIError as e:
                    if attempt == max_retries - 1:
                        # Último intento fallido
                        raise SheetsConnectionError(
                            f"Max retries reached after {max_retries} attempts",
                            details=str(e)
                        )

                    # Esperar con backoff exponencial
                    wait_time = backoff_seconds * (2 ** attempt)
                    logging.warning(
                        f"Sheets API error on attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time}s... Error: {str(e)}"
                    )
                    time.sleep(wait_time)

            # Fallback (no debería llegar aquí)
            raise SheetsConnectionError("Unexpected error in retry logic")

        return wrapper
    return decorator


class SheetsRepository:
    """
    Repositorio para operaciones CRUD en Google Sheets.

    Responsabilidades:
    - Autenticación con Service Account
    - Lectura de hojas completas
    - Búsqueda de filas por valor de columna
    - Actualización de celdas (individual y batch)
    - Manejo de errores y reintentos
    """

    def __init__(self, compatibility_mode: str = "v2.1"):
        """
        Inicializa el repositorio (autenticación lazy).

        Args:
            compatibility_mode: Version mode ("v2.1" or "v3.0")
                - "v2.1": v3.0 columns return None/0 (default until migration complete)
                - "v3.0": Full v3.0 column access enabled
        """
        self.logger = logging.getLogger(__name__)
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._cache = get_cache()  # Cache singleton para reducir API calls
        self._compatibility_mode = compatibility_mode  # v2.1 or v3.0

    def _get_client(self) -> gspread.Client:
        """
        Obtiene cliente gspread autenticado (lazy loading).

        Returns:
            gspread.Client autenticado

        Raises:
            SheetsConnectionError: Si falla la autenticación
        """
        if not self._client:
            try:
                self.logger.info("Autenticando con Service Account...")

                # Obtener credenciales (desde JSON env var o archivo)
                creds_dict = config.get_credentials_dict()
                if not creds_dict:
                    raise SheetsConnectionError(
                        "No se encontraron credenciales de Google Service Account",
                        details="Verificar GOOGLE_APPLICATION_CREDENTIALS_JSON o archivo local"
                    )

                # Crear credenciales desde diccionario
                creds = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=config.get_scopes()
                )

                # Autorizar cliente gspread
                self._client = gspread.authorize(creds)

                self.logger.info("✅ Cliente gspread autenticado exitosamente")

            except SheetsConnectionError:
                # Re-raise nuestras excepciones custom
                raise
            except Exception as e:
                raise SheetsConnectionError(
                    "Error durante autenticación",
                    details=str(e)
                )

        return self._client

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """
        Obtiene el spreadsheet (libro) de Google Sheets.

        Returns:
            gspread.Spreadsheet

        Raises:
            SheetsConnectionError: Si no se puede abrir el spreadsheet
        """
        if not self._spreadsheet:
            try:
                client = self._get_client()
                self._spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
                self.logger.info(f"✅ Spreadsheet abierto: {self._spreadsheet.title}")

            except gspread.exceptions.SpreadsheetNotFound:
                raise SheetsConnectionError(
                    "Spreadsheet no encontrado",
                    details=f"ID: {config.GOOGLE_SHEET_ID}"
                )
            except Exception as e:
                raise SheetsConnectionError(
                    "Error abriendo spreadsheet",
                    details=str(e)
                )

        return self._spreadsheet

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def read_worksheet(self, sheet_name: str) -> list[list]:
        """
        Lee una hoja completa de Google Sheets con cache.

        Verifica cache primero. Si hay cache hit, retorna datos cacheados.
        Si cache miss, lee de Sheets y cachea con TTL apropiado.

        Args:
            sheet_name: Nombre de la hoja (ej: "Operaciones", "Trabajadores")

        Returns:
            Lista de filas, cada fila es una lista de valores

        Raises:
            SheetsConnectionError: Si falla la lectura
        """
        # Intentar leer del cache primero
        cache_key = f"worksheet:{sheet_name}"
        cached_data = self._cache.get(cache_key)

        if cached_data is not None:
            self.logger.info(f"✅ Cache hit: '{sheet_name}' ({len(cached_data)} filas)")
            return cached_data

        # Cache miss - leer de Google Sheets
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)

            # Leer todos los valores (batch read)
            all_values = worksheet.get_all_values()

            # Cachear con TTL según tipo de hoja
            # Trabajadores cambian poco → TTL largo (300s)
            # Operaciones cambian frecuente → TTL corto (60s)
            ttl = 300 if sheet_name == config.HOJA_TRABAJADORES_NOMBRE else 60

            self._cache.set(cache_key, all_values, ttl_seconds=ttl)

            self.logger.info(
                f"✅ Leídas {len(all_values)} filas de '{sheet_name}' "
                f"(cached por {ttl}s)"
            )
            return all_values

        except gspread.exceptions.WorksheetNotFound:
            raise SheetsConnectionError(
                f"Hoja '{sheet_name}' no encontrada en el spreadsheet",
                details=f"Hojas disponibles: {[ws.title for ws in self._get_spreadsheet().worksheets()]}"
            )
        except Exception as e:
            raise SheetsConnectionError(
                f"Error leyendo hoja '{sheet_name}'",
                details=str(e)
            )

    def find_row_by_column_value(
        self,
        sheet_name: str,
        column_letter: str,
        value: str
    ) -> Optional[int]:
        """
        Busca una fila por el valor de una columna específica.

        Args:
            sheet_name: Nombre de la hoja
            column_letter: Letra de la columna (ej: "G" para TAG_SPOOL)
            value: Valor a buscar

        Returns:
            Número de fila (1-indexed) o None si no se encuentra

        Example:
            row_num = repo.find_row_by_column_value("Operaciones", "G", "MK-123")
            # Retorna 25 si el spool está en la fila 25
        """
        all_rows = self.read_worksheet(sheet_name)

        # Convertir letra de columna a índice (A=0, B=1, ..., G=6, ...)
        column_index = self._column_letter_to_index(column_letter)

        # Buscar valor (skip header row - index 0)
        for row_index, row in enumerate(all_rows[1:], start=2):  # Start at row 2 (1-indexed)
            if column_index < len(row) and row[column_index] == value:
                self.logger.debug(f"Valor '{value}' encontrado en fila {row_index}, columna {column_letter}")
                return row_index

        self.logger.debug(f"Valor '{value}' no encontrado en columna {column_letter}")
        return None

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def update_cell(
        self,
        sheet_name: str,
        row: int,
        column_letter: str,
        value: any
    ) -> None:
        """
        Actualiza una celda específica usando USER_ENTERED para formateo correcto.

        USER_ENTERED permite que Google Sheets interprete valores como fechas,
        números, etc., en lugar de tratarlos como texto plano.

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)
            column_letter: Letra de columna (ej: "V", "BC")
            value: Nuevo valor

        Raises:
            SheetsUpdateError: Si falla la actualización
        """
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)

            # Usar worksheet.update() con value_input_option='USER_ENTERED'
            # en lugar de update_cell() para permitir interpretación de fechas
            cell_address = f"{column_letter}{row}"
            worksheet.update(
                cell_address,
                [[value]],
                value_input_option='USER_ENTERED'
            )

            self.logger.info(f"✅ Actualizada celda {column_letter}{row} = {value} en '{sheet_name}'")

        except Exception as e:
            raise SheetsUpdateError(
                f"Error actualizando celda {column_letter}{row}",
                updates={"row": row, "column": column_letter, "value": value, "error": str(e)}
            )

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def batch_update(
        self,
        sheet_name: str,
        updates: list[dict]
    ) -> None:
        """
        Actualiza múltiples celdas en una sola operación con USER_ENTERED.

        Invalida el cache de la hoja después de actualizar para asegurar
        que lecturas subsecuentes obtengan datos actualizados.

        Usa value_input_option='USER_ENTERED' para permitir que Google Sheets
        interprete valores como fechas, números, etc.

        Args:
            sheet_name: Nombre de la hoja
            updates: Lista de dicts con formato:
                     [{"row": 10, "column": "V", "value": 0.1}, ...]

        Raises:
            SheetsUpdateError: Si falla la actualización
        """
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)

            # Preparar batch updates
            batch_data = []
            for update in updates:
                row = update["row"]
                column = update["column"]
                value = update["value"]

                # Formato A1 notation: "V25", "BC10", etc.
                cell_address = f"{column}{row}"

                batch_data.append({
                    'range': cell_address,
                    'values': [[value]]
                })

            # Ejecutar batch update con value_input_option='USER_ENTERED'
            worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            self.logger.info(
                f"✅ Batch update: {len(updates)} celdas actualizadas en '{sheet_name}'"
            )

            # Invalidar cache para forzar re-lectura en próximo acceso
            cache_key = f"worksheet:{sheet_name}"
            self._cache.invalidate(cache_key)

        except Exception as e:
            raise SheetsUpdateError(
                "Error en batch update",
                updates={"count": len(updates), "updates": updates, "error": str(e)}
            )

    def update_cell_by_column_name(
        self,
        sheet_name: str,
        row: int,
        column_name: str,
        value: any
    ) -> None:
        """
        Actualiza una celda usando NOMBRE de columna con USER_ENTERED (v2.1).

        Usa ColumnMapCache para obtener índice dinámicamente.
        Resistente a cambios en estructura del spreadsheet.
        Usa value_input_option='USER_ENTERED' para formateo correcto de fechas.

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)
            column_name: Nombre de columna (ej: "Armador", "Fecha_Armado")
            value: Nuevo valor

        Raises:
            ValueError: Si la columna no existe en el mapeo
            SheetsUpdateError: Si falla la actualización

        Example:
            >>> repo.update_cell_by_column_name("Operaciones", 10, "Armador", "Juan Pérez")
            # Actualiza columna Armador en fila 10
        """
        try:
            # Obtener column_map para esta hoja
            from backend.core.column_map_cache import ColumnMapCache
            column_map = ColumnMapCache.get_or_build(sheet_name, self)

            # Normalizar nombre de columna
            def normalize(name: str) -> str:
                return name.lower().replace(" ", "").replace("_", "")

            normalized_name = normalize(column_name)

            # Buscar índice de columna
            if normalized_name not in column_map:
                raise ValueError(
                    f"Columna '{column_name}' no encontrada en hoja '{sheet_name}'. "
                    f"Columnas disponibles: {list(column_map.keys())[:10]}..."
                )

            column_index = column_map[normalized_name]

            # Obtener spreadsheet y worksheet
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)

            # Convertir índice a letra de columna
            column_letter = self._index_to_column_letter(column_index)
            cell_address = f"{column_letter}{row}"

            # Actualizar celda con value_input_option='USER_ENTERED'
            worksheet.update(
                cell_address,
                [[value]],
                value_input_option='USER_ENTERED'
            )

            self.logger.info(
                f"✅ Actualizada celda '{column_name}' (idx={column_index}) fila {row} = {value} en '{sheet_name}'"
            )

            # Invalidate cache to ensure fresh data on next read
            # CRITICAL: State machine callbacks (ARM/SOLD iniciar) use this method to write Armador/Soldador
            # Without cache invalidation, subsequent reads (like PAUSAR hydration) get stale data
            cache_key = f"worksheet:{sheet_name}"
            self._cache.invalidate(cache_key)

        except ValueError:
            raise
        except Exception as e:
            raise SheetsUpdateError(
                f"Error actualizando celda por nombre '{column_name}' fila {row}",
                updates={"row": row, "column_name": column_name, "value": value, "error": str(e)}
            )

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def batch_update_by_column_name(
        self,
        sheet_name: str,
        updates: list[dict]
    ) -> None:
        """
        Actualiza múltiples celdas usando NOMBRES de columnas con USER_ENTERED (v2.1).

        Usa ColumnMapCache para resolver nombres dinámicamente.
        Más eficiente que múltiples llamadas individuales.
        Usa value_input_option='USER_ENTERED' para formateo correcto de fechas.

        Args:
            sheet_name: Nombre de la hoja
            updates: Lista de dicts con formato:
                     [{"row": 10, "column_name": "Armador", "value": "Juan"}, ...]

        Raises:
            ValueError: Si alguna columna no existe
            SheetsUpdateError: Si falla la actualización

        Example:
            >>> updates = [
            ...     {"row": 10, "column_name": "Armador", "value": "Juan"},
            ...     {"row": 10, "column_name": "Fecha_Armado", "value": "21-01-2026"}
            ... ]
            >>> repo.batch_update_by_column_name("Operaciones", updates)
        """
        try:
            # Obtener column_map para esta hoja
            from backend.core.column_map_cache import ColumnMapCache
            column_map = ColumnMapCache.get_or_build(sheet_name, self)

            # Normalizar nombre de columna
            def normalize(name: str) -> str:
                return name.lower().replace(" ", "").replace("_", "")

            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)

            # Preparar batch updates (convertir nombres a índices)
            batch_data = []
            for update in updates:
                row = update["row"]
                column_name = update["column_name"]
                value = update["value"]

                # Buscar índice de columna
                normalized_name = normalize(column_name)
                if normalized_name not in column_map:
                    raise ValueError(
                        f"Columna '{column_name}' no encontrada en hoja '{sheet_name}'. "
                        f"Columnas disponibles: {list(column_map.keys())[:10]}..."
                    )

                column_index = column_map[normalized_name]

                # Convertir a letra de columna para A1 notation
                column_letter = self._index_to_column_letter(column_index)
                cell_address = f"{column_letter}{row}"

                batch_data.append({
                    'range': cell_address,
                    'values': [[value]]
                })

            # Ejecutar batch update con value_input_option='USER_ENTERED'
            worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

            self.logger.info(
                f"✅ Batch update by column name: {len(updates)} celdas actualizadas en '{sheet_name}'"
            )

            # Invalidar cache para forzar re-lectura
            cache_key = f"worksheet:{sheet_name}"
            self._cache.invalidate(cache_key)

        except ValueError:
            raise
        except Exception as e:
            raise SheetsUpdateError(
                "Error en batch update by column name",
                updates={"count": len(updates), "updates": updates, "error": str(e)}
            )

    @staticmethod
    def _index_to_column_letter(index: int) -> str:
        """
        Convierte índice (0-indexed) a letra de columna.

        Args:
            index: Índice 0-indexed (0=A, 1=B, 25=Z, 26=AA, 54=BC)

        Returns:
            str: Letra(s) de columna

        Example:
            >>> SheetsRepository._index_to_column_letter(0)
            'A'
            >>> SheetsRepository._index_to_column_letter(25)
            'Z'
            >>> SheetsRepository._index_to_column_letter(26)
            'AA'
        """
        index += 1  # Convertir a 1-indexed
        letter = ""
        while index > 0:
            index -= 1
            letter = chr(index % 26 + ord('A')) + letter
            index //= 26
        return letter

    @staticmethod
    def _column_letter_to_index(column: str) -> int:
        """
        Convierte letra de columna a índice (0-indexed).

        Args:
            column: Letra(s) de columna (ej: "A", "B", "AA", "BC")

        Returns:
            int: Índice 0-indexed (A=0, B=1, Z=25, AA=26, BC=54)

        Example:
            >>> SheetsRepository._column_letter_to_index("A")
            0
            >>> SheetsRepository._column_letter_to_index("G")
            6
            >>> SheetsRepository._column_letter_to_index("BC")
            54
        """
        column = column.upper()
        index = 0
        for i, char in enumerate(reversed(column)):
            index += (ord(char) - ord('A') + 1) * (26 ** i)
        return index - 1  # Convertir a 0-indexed

    # =========================================================================
    # v3.0 Column Access Methods (Occupation tracking)
    # =========================================================================

    def get_ocupado_por(self, sheet_name: str, row: int) -> Optional[str]:
        """
        Lee el valor de la columna Ocupado_Por para una fila (v3.0).

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)

        Returns:
            str: Worker ocupando el spool (formato "INICIALES(ID)") o None
        """
        if self._compatibility_mode == "v2.1":
            return None

        all_rows = self.read_worksheet(sheet_name)
        if row >= len(all_rows):
            return None

        from backend.core.column_map_cache import ColumnMapCache
        column_map = ColumnMapCache.get_or_build(sheet_name, self)

        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "")

        idx = column_map.get(normalize("Ocupado_Por"))
        if idx is None or idx >= len(all_rows[row]):
            return None

        value = all_rows[row][idx]
        return value.strip() if value else None

    def get_fecha_ocupacion(self, sheet_name: str, row: int) -> Optional[str]:
        """
        Lee el valor de la columna Fecha_Ocupacion para una fila (v3.0).

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)

        Returns:
            str: Fecha de ocupación (YYYY-MM-DD) o None
        """
        if self._compatibility_mode == "v2.1":
            return None

        all_rows = self.read_worksheet(sheet_name)
        if row >= len(all_rows):
            return None

        from backend.core.column_map_cache import ColumnMapCache
        column_map = ColumnMapCache.get_or_build(sheet_name, self)

        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "")

        idx = column_map.get(normalize("Fecha_Ocupacion"))
        if idx is None or idx >= len(all_rows[row]):
            return None

        value = all_rows[row][idx]
        return value.strip() if value else None

    def get_version(self, sheet_name: str, row: int) -> int:
        """
        Lee el valor de la columna version para una fila (v3.0).

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)

        Returns:
            int: Version token (default 0)
        """
        if self._compatibility_mode == "v2.1":
            return 0

        all_rows = self.read_worksheet(sheet_name)
        if row >= len(all_rows):
            return 0

        from backend.core.column_map_cache import ColumnMapCache
        column_map = ColumnMapCache.get_or_build(sheet_name, self)

        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "")

        idx = column_map.get(normalize("version"))
        if idx is None or idx >= len(all_rows[row]):
            return 0

        value = all_rows[row][idx]
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    def set_ocupado_por(
        self,
        sheet_name: str,
        row: int,
        worker_nombre: Optional[str]
    ) -> None:
        """
        Actualiza la columna Ocupado_Por para una fila (v3.0).

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)
            worker_nombre: Worker ocupando el spool o None para liberar
        """
        if self._compatibility_mode == "v2.1":
            self.logger.warning("Skipping set_ocupado_por in v2.1 compatibility mode")
            return

        self.update_cell_by_column_name(
            sheet_name=sheet_name,
            row=row,
            column_name="Ocupado_Por",
            value=worker_nombre if worker_nombre else ""
        )

    def set_fecha_ocupacion(
        self,
        sheet_name: str,
        row: int,
        fecha: Optional[str]
    ) -> None:
        """
        Actualiza la columna Fecha_Ocupacion para una fila (v3.0).

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)
            fecha: Fecha de ocupación (YYYY-MM-DD) o None para limpiar
        """
        if self._compatibility_mode == "v2.1":
            self.logger.warning("Skipping set_fecha_ocupacion in v2.1 compatibility mode")
            return

        self.update_cell_by_column_name(
            sheet_name=sheet_name,
            row=row,
            column_name="Fecha_Ocupacion",
            value=fecha if fecha else ""
        )

    def increment_version(self, sheet_name: str, row: int) -> int:
        """
        Incrementa el token de versión para una fila (v3.0 optimistic locking).

        Args:
            sheet_name: Nombre de la hoja
            row: Número de fila (1-indexed)

        Returns:
            int: Nueva versión después de incrementar
        """
        if self._compatibility_mode == "v2.1":
            self.logger.warning("Skipping increment_version in v2.1 compatibility mode")
            return 0

        current_version = self.get_version(sheet_name, row)
        new_version = current_version + 1

        self.update_cell_by_column_name(
            sheet_name=sheet_name,
            row=row,
            column_name="version",
            value=new_version
        )

        return new_version

    def update_spool_occupation(
        self,
        tag_spool: str,
        ocupado_por: Optional[str] = None,
        fecha_ocupacion: Optional[str] = None,
        estado: Optional[str] = None
    ) -> None:
        """
        Update occupation fields for a spool (v3.0 convenience method).

        Args:
            tag_spool: TAG del spool a actualizar
            ocupado_por: Worker nombre (INICIALES(ID)) o None para limpiar
            fecha_ocupacion: Fecha (YYYY-MM-DD) o None para limpiar
            estado: Estado de ocupación (optional, for PAUSAR marking)

        Raises:
            SpoolNoEncontradoError: If spool not found
            SheetsUpdateError: If update fails
        """
        from backend.models.spool import Spool
        from backend.exceptions import SpoolNoEncontradoError

        # Find spool row
        spool = self.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        sheet_name = config.HOJA_OPERACIONES_NOMBRE

        # Update occupation fields
        if ocupado_por is not None:
            self.set_ocupado_por(sheet_name, spool.fila_sheets, ocupado_por)

        if fecha_ocupacion is not None:
            self.set_fecha_ocupacion(sheet_name, spool.fila_sheets, fecha_ocupacion)

        # Note: estado field will be added in future v3.0 schema enhancement
        # For now, we skip it if provided
        if estado:
            self.logger.info(f"Estado '{estado}' provided but not yet supported in v3.0 schema")

        self.logger.info(
            f"Spool {tag_spool} occupation updated: ocupado_por={ocupado_por}, "
            f"fecha={fecha_ocupacion}"
        )

    def update_spool_completion(
        self,
        tag_spool: str,
        operacion: str,
        fecha_operacion: str,
        ocupado_por: Optional[str] = None,
        fecha_ocupacion: Optional[str] = None
    ) -> None:
        """
        Update completion fields for a spool (v3.0 convenience method).

        Args:
            tag_spool: TAG del spool a actualizar
            operacion: ARM or SOLD
            fecha_operacion: Fecha de completado (YYYY-MM-DD)
            ocupado_por: Worker nombre to clear (typically None)
            fecha_ocupacion: Fecha ocupacion to clear (typically None)

        Raises:
            SpoolNoEncontradoError: If spool not found
            SheetsUpdateError: If update fails
        """
        from backend.models.spool import Spool
        from backend.exceptions import SpoolNoEncontradoError

        # Find spool row
        spool = self.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        sheet_name = config.HOJA_OPERACIONES_NOMBRE

        # Update fecha column based on operation
        if operacion == "ARM":
            column_name = "Fecha_Armado"
        elif operacion == "SOLD":
            column_name = "Fecha_Soldadura"
        else:
            column_name = f"Fecha_{operacion}"  # Generic for future operations

        self.update_cell_by_column_name(
            sheet_name=sheet_name,
            row=spool.fila_sheets,
            column_name=column_name,
            value=fecha_operacion
        )

        # Clear occupation fields
        if ocupado_por is not None:
            self.set_ocupado_por(sheet_name, spool.fila_sheets, ocupado_por)

        if fecha_ocupacion is not None:
            self.set_fecha_ocupacion(sheet_name, spool.fila_sheets, fecha_ocupacion)

        self.logger.info(
            f"Spool {tag_spool} {operacion} completed: fecha={fecha_operacion}, "
            f"occupation cleared"
        )

    def get_spool_version(self, tag_spool: str) -> str:
        """
        Get current version token for a spool (v3.0 optimistic locking).

        Args:
            tag_spool: TAG del spool

        Returns:
            str: Current version token (UUID4 string) or "0" if not set

        Raises:
            SpoolNoEncontradoError: If spool not found
        """
        from backend.exceptions import SpoolNoEncontradoError
        from backend.config import config
        from backend.core.column_map_cache import ColumnMapCache

        # Get column map for dynamic column lookup
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self)

        # Normalize column name helper
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        # Try to find TAG_SPOOL column (could be named "TAG_SPOOL" or "SPLIT" in the sheet)
        tag_column_index = None
        tag_column_names_to_try = ["TAG_SPOOL", "SPLIT", "tag_spool"]

        for col_name in tag_column_names_to_try:
            normalized = normalize(col_name)
            if normalized in column_map:
                tag_column_index = column_map[normalized]
                self.logger.debug(f"Found TAG column as '{col_name}' at index {tag_column_index}")
                break

        if tag_column_index is None:
            # Fallback to hardcoded index 6 (column G, 0-indexed) if dynamic lookup fails
            self.logger.warning(
                f"TAG_SPOOL column not found in column map, falling back to column G (index 6). "
                f"Available columns: {list(column_map.keys())[:10]}..."
            )
            tag_column_index = 6  # Column G is index 6 (0-indexed: A=0, B=1, ..., G=6)

        # Convert column index to letter
        column_letter = self._index_to_column_letter(tag_column_index)

        # Find spool row by TAG_SPOOL column
        row_num = self.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=column_letter,
            value=tag_spool
        )

        if row_num is None:
            raise SpoolNoEncontradoError(tag_spool)

        # Read version using dynamic column mapping
        version = self.get_version(config.HOJA_OPERACIONES_NOMBRE, row_num)

        # Return as string (UUID4 format expected)
        return str(version) if version else "0"

    def get_spool_by_tag(self, tag_spool: str) -> Optional['Spool']:
        """
        Get complete spool data by TAG_SPOOL.

        Args:
            tag_spool: TAG unique identifier of the spool

        Returns:
            Spool object with all data, or None if not found

        Raises:
            SheetsConnectionError: On Google Sheets API errors
        """
        from backend.models.spool import Spool
        from backend.config import config
        from datetime import datetime
        from backend.core.column_map_cache import ColumnMapCache

        # Get column map for dynamic column lookup
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self)

        # Normalize column name helper
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        # Try to find TAG_SPOOL column (could be named "TAG_SPOOL" or "SPLIT" in the sheet)
        tag_column_index = None
        tag_column_names_to_try = ["TAG_SPOOL", "SPLIT", "tag_spool"]

        for col_name in tag_column_names_to_try:
            normalized = normalize(col_name)
            if normalized in column_map:
                tag_column_index = column_map[normalized]
                self.logger.debug(f"Found TAG column as '{col_name}' at index {tag_column_index}")
                break

        if tag_column_index is None:
            # Fallback to hardcoded G (column index 6, 0-indexed) if dynamic lookup fails
            self.logger.warning(
                f"TAG_SPOOL column not found in column map, falling back to column G. "
                f"Available columns: {list(column_map.keys())[:10]}..."
            )
            tag_column_index = 6  # Column G is index 6 (0-indexed: A=0, B=1, ..., G=6)

        # Convert column index to letter
        column_letter = self._index_to_column_letter(tag_column_index)

        # Find spool row by TAG_SPOOL column
        row_num = self.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=column_letter,
            value=tag_spool
        )

        if row_num is None:
            return None  # Spool not found

        # Read the entire row
        all_rows = self.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        if not all_rows or row_num > len(all_rows):
            return None

        row_data = all_rows[row_num - 1]  # Convert 1-indexed to 0-indexed

        # Get column map for dynamic column access
        from backend.core.column_map_cache import ColumnMapCache
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self)

        def normalize(name: str) -> str:
            """Normalize column name to match ColumnMapCache format."""
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        def get_col_value(col_name: str) -> Optional[str]:
            """Helper to safely get column value by name."""
            normalized = normalize(col_name)
            if normalized not in column_map:
                return None
            col_index = column_map[normalized]  # Already 0-indexed from build_column_map
            if col_index < len(row_data):
                value = row_data[col_index]
                return value if value and value.strip() else None
            return None

        def parse_date(date_str: Optional[str]) -> Optional[date]:
            """Helper to parse date string to date object."""
            if not date_str:
                return None
            try:
                # Try YYYY-MM-DD format first
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    # Try DD/MM/YYYY format (Google Sheets default)
                    return datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    try:
                        # Try DD-MM-YYYY format
                        return datetime.strptime(date_str, "%d-%m-%Y").date()
                    except ValueError:
                        return None

        # Build Spool object
        try:
            # v3.0 fields: only read and parse if in v3.0 mode
            if self._compatibility_mode == "v3.0":
                version_raw = get_col_value("version")
                try:
                    version_value = int(version_raw) if version_raw else 0
                except (ValueError, TypeError):
                    version_value = 0
                ocupado_por_value = get_col_value("Ocupado_Por")
                fecha_ocupacion_value = get_col_value("Fecha_Ocupacion")
                estado_detalle_value = get_col_value("Estado_Detalle")
            else:
                version_value = 0
                ocupado_por_value = None
                fecha_ocupacion_value = None
                estado_detalle_value = None

            spool = Spool(
                tag_spool=tag_spool,
                ot=get_col_value("OT"),  # v4.0: Orden de Trabajo (columna B)
                nv=get_col_value("NV"),
                fecha_materiales=parse_date(get_col_value("Fecha_Materiales")),
                fecha_armado=parse_date(get_col_value("Fecha_Armado")),
                fecha_soldadura=parse_date(get_col_value("Fecha_Soldadura")),
                fecha_qc_metrologia=parse_date(get_col_value("Fecha_QC_Metrología")),
                armador=get_col_value("Armador"),
                soldador=get_col_value("Soldador"),
                ocupado_por=ocupado_por_value,
                fecha_ocupacion=fecha_ocupacion_value,
                version=version_value,
                estado_detalle=estado_detalle_value,
            )
            return spool
        except Exception as e:
            self.logger.error(
                f"Error constructing Spool object for {tag_spool}: {e}",
                exc_info=True
            )
            return None

    def get_spools_for_metrologia(self) -> list['Spool']:
        """
        Get spools ready for metrología inspection.

        Filter criteria (ALL must be true):
        - fecha_armado != None (ARM completed)
        - fecha_soldadura != None (SOLD completed)
        - fecha_qc_metrologia == None (METROLOGIA not done)
        - ocupado_por == None (not occupied - prevents race conditions)

        Returns:
            List of Spool objects ready for inspection (may be empty)

        Raises:
            SheetsConnectionError: On Google Sheets API errors
        """
        from backend.models.spool import Spool
        from backend.config import config
        from datetime import datetime

        # Read all rows from Operaciones sheet
        all_rows = self.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        if not all_rows or len(all_rows) < 2:  # Need at least header + 1 data row
            return []

        # Get column map for dynamic column access
        from backend.core.column_map_cache import ColumnMapCache
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self)

        def normalize(name: str) -> str:
            """Normalize column name to match ColumnMapCache format."""
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        def get_col_value(row_data: list, col_name: str) -> Optional[str]:
            """Helper to safely get column value by name."""
            normalized = normalize(col_name)
            if normalized not in column_map:
                return None
            col_index = column_map[normalized]  # Already 0-indexed from build_column_map
            if col_index < len(row_data):
                value = row_data[col_index]
                return value if value and value.strip() else None
            return None

        def parse_date(date_str: Optional[str]) -> Optional[date]:
            """Helper to parse date string to date object."""
            if not date_str:
                return None
            try:
                # Try YYYY-MM-DD format first
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    # Try DD/MM/YYYY format (Google Sheets default)
                    return datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    try:
                        # Try DD-MM-YYYY format
                        return datetime.strptime(date_str, "%d-%m-%Y").date()
                    except ValueError:
                        return None

        # Filter spools
        ready_spools = []
        for row_data in all_rows[1:]:  # Skip header row
            try:
                # Get key fields for filtering
                tag_spool = get_col_value(row_data, "TAG_SPOOL")
                if not tag_spool:
                    continue  # Skip rows without TAG_SPOOL

                fecha_armado = parse_date(get_col_value(row_data, "Fecha_Armado"))
                fecha_soldadura = parse_date(get_col_value(row_data, "Fecha_Soldadura"))
                fecha_qc_metrologia = parse_date(get_col_value(row_data, "Fecha_QC_Metrología"))
                ocupado_por = get_col_value(row_data, "Ocupado_Por") if self._compatibility_mode == "v3.0" else None

                # Apply filter criteria
                if (
                    fecha_armado is not None and
                    fecha_soldadura is not None and
                    fecha_qc_metrologia is None and
                    ocupado_por is None
                ):
                    # Build Spool object for filtered row
                    spool = Spool(
                        tag_spool=tag_spool,
                        ot=get_col_value(row_data, "OT"),  # v4.0: Orden de Trabajo
                        nv=get_col_value(row_data, "NV"),
                        fecha_materiales=parse_date(get_col_value(row_data, "Fecha_Materiales")),
                        fecha_armado=fecha_armado,
                        fecha_soldadura=fecha_soldadura,
                        fecha_qc_metrologia=fecha_qc_metrologia,
                        armador=get_col_value(row_data, "Armador"),
                        soldador=get_col_value(row_data, "Soldador"),
                        ocupado_por=ocupado_por,
                        fecha_ocupacion=get_col_value(row_data, "Fecha_Ocupacion") if self._compatibility_mode == "v3.0" else None,
                        version=int(get_col_value(row_data, "version") or 0) if self._compatibility_mode == "v3.0" else 0,
                        estado_detalle=get_col_value(row_data, "Estado_Detalle") if self._compatibility_mode == "v3.0" else None,
                    )
                    ready_spools.append(spool)
            except Exception as e:
                # Log error but continue processing other rows
                self.logger.warning(f"Error processing row for metrología filter: {e}")
                continue

        self.logger.info(f"get_spools_for_metrologia: {len(ready_spools)} spools ready")
        return ready_spools

    def get_all_spools(self) -> list['Spool']:
        """
        Get ALL spools from Operaciones sheet (v3.0).

        Used by reparacion endpoint to filter RECHAZADO/BLOQUEADO spools.
        Returns all spools with v3.0 fields (ocupado_por, estado_detalle).

        Returns:
            list[Spool]: All spools from sheet

        Raises:
            SheetsConnectionError: On Google Sheets API errors
        """
        from backend.models.spool import Spool
        from backend.config import config
        from datetime import datetime, date

        # Read all rows
        all_rows = self.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        if not all_rows or len(all_rows) < 2:
            self.logger.warning("No data rows found in Operaciones sheet")
            return []

        # Get column map using ColumnMapCache
        from backend.core.column_map_cache import ColumnMapCache
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, self)

        def normalize(name: str) -> str:
            """Normalize column name to match ColumnMapCache format."""
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        def get_col_value(row_data: list, col_name: str) -> Optional[str]:
            """Helper to safely get column value by name."""
            normalized = normalize(col_name)
            if normalized not in column_map:
                return None
            col_index = column_map[normalized]  # Already 0-indexed from build_column_map
            if col_index < len(row_data):
                value = row_data[col_index]
                return value if value and str(value).strip() else None
            return None

        def parse_date(date_str: Optional[str]) -> Optional[date]:
            """Helper to parse date string to date object."""
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    return datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    try:
                        return datetime.strptime(date_str, "%d-%m-%Y").date()
                    except ValueError:
                        return None

        spools = []
        # Skip header (row 0)
        for row_data in all_rows[1:]:
            try:
                tag_spool = get_col_value(row_data, "TAG_SPOOL")
                if not tag_spool:
                    continue  # Skip rows without TAG_SPOOL

                spool = Spool(
                    tag_spool=tag_spool,
                    ot=get_col_value(row_data, "OT"),  # v4.0: Orden de Trabajo
                    nv=get_col_value(row_data, "NV"),
                    fecha_materiales=parse_date(get_col_value(row_data, "Fecha_Materiales")),
                    fecha_armado=parse_date(get_col_value(row_data, "Fecha_Armado")),
                    fecha_soldadura=parse_date(get_col_value(row_data, "Fecha_Soldadura")),
                    fecha_qc_metrologia=parse_date(get_col_value(row_data, "Fecha_QC_Metrología")),
                    armador=get_col_value(row_data, "Armador"),
                    soldador=get_col_value(row_data, "Soldador"),
                    ocupado_por=get_col_value(row_data, "Ocupado_Por") if self._compatibility_mode == "v3.0" else None,
                    fecha_ocupacion=get_col_value(row_data, "Fecha_Ocupacion") if self._compatibility_mode == "v3.0" else None,
                    version=int(get_col_value(row_data, "version") or 0) if self._compatibility_mode == "v3.0" else 0,
                    estado_detalle=get_col_value(row_data, "Estado_Detalle") if self._compatibility_mode == "v3.0" else None,
                )
                spools.append(spool)
            except Exception as e:
                self.logger.warning(f"Error processing row for all spools: {e}")
                continue

        self.logger.info(f"get_all_spools: {len(spools)} spools fetched")
        return spools

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def update_spool_with_version(
        self,
        tag_spool: str,
        updates: dict,
        expected_version: str
    ) -> str:
        """
        Update spool with version check for optimistic locking (v3.0).

        This is the critical method for preventing race conditions via version validation.

        Flow:
        1. Read current version from sheet using dynamic header mapping
        2. Compare with expected_version
        3. If mismatch: raise VersionConflictError
        4. If match: update all fields atomically + increment version
        5. Return new version token

        Args:
            tag_spool: TAG del spool a actualizar
            updates: Dictionary of {column_name: value} updates
            expected_version: Version token expected by this operation

        Returns:
            str: New version token after successful update

        Raises:
            SpoolNoEncontradoError: If spool not found
            VersionConflictError: If version mismatch (concurrent update detected)
            SheetsUpdateError: If update fails

        Example:
            >>> repo.update_spool_with_version(
            ...     tag_spool="TAG-123",
            ...     updates={"Ocupado_Por": "MR(93)", "Fecha_Ocupacion": "2026-01-27"},
            ...     expected_version="550e8400-e29b-41d4-a716-446655440000"
            ... )
            "7c9e6679-7425-40de-944b-e07fc1f90ae7"  # New version
        """
        from backend.exceptions import SpoolNoEncontradoError, VersionConflictError
        from backend.config import config
        import uuid

        sheet_name = config.HOJA_OPERACIONES_NOMBRE

        # Step 1: Find spool row
        row_num = self.find_row_by_column_value(
            sheet_name=sheet_name,
            column_letter="G",  # TAG_SPOOL column
            value=tag_spool
        )

        if row_num is None:
            raise SpoolNoEncontradoError(tag_spool)

        # Step 2: Read current version using dynamic header mapping
        current_version = self.get_version(sheet_name, row_num)
        current_version_str = str(current_version) if current_version else "0"

        # Step 3: Version check - raise VersionConflictError if mismatch
        if current_version_str != expected_version:
            raise VersionConflictError(
                expected=expected_version,
                actual=current_version_str,
                message=f"Spool {tag_spool} was modified by another operation"
            )

        # Step 4: Generate new version token (UUID4)
        new_version = str(uuid.uuid4())

        # Step 5: Prepare batch update (all updates + version increment)
        batch_updates = []

        for column_name, value in updates.items():
            batch_updates.append({
                "row": row_num,
                "column_name": column_name,
                "value": value
            })

        # Add version update to batch
        batch_updates.append({
            "row": row_num,
            "column_name": "version",
            "value": new_version
        })

        # Step 6: Execute atomic batch update
        try:
            self.batch_update_by_column_name(sheet_name, batch_updates)

            self.logger.info(
                f"✅ Spool {tag_spool} updated with version check: "
                f"version {expected_version} → {new_version}, "
                f"{len(updates)} fields updated"
            )

            return new_version

        except Exception as e:
            raise SheetsUpdateError(
                f"Failed to update spool {tag_spool} with version check: {e}",
                updates={"expected_version": expected_version, "updates": updates}
            )


if __name__ == "__main__":
    """Script de prueba para validar el repositorio."""
    logging.basicConfig(level=logging.INFO)

    try:
        repo = SheetsRepository()

        # Test 1: Leer hoja Trabajadores
        print("\n📖 Test 1: Leyendo hoja Trabajadores...")
        workers_rows = repo.read_worksheet(config.HOJA_TRABAJADORES_NOMBRE)
        print(f"✅ {len(workers_rows)} filas leídas")
        if len(workers_rows) > 0:
            print(f"   Header: {workers_rows[0]}")
            print(f"   Primera fila de datos: {workers_rows[1] if len(workers_rows) > 1 else 'N/A'}")

        # Test 2: Leer hoja Operaciones
        print("\n📖 Test 2: Leyendo hoja Operaciones...")
        ops_rows = repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        print(f"✅ {len(ops_rows)} filas leídas")
        if len(ops_rows) > 0:
            print(f"   Columnas totales: {len(ops_rows[0])}")

        print("\n✅ Todos los tests pasaron exitosamente")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
