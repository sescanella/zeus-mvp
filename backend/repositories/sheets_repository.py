"""
Repositorio para acceso a Google Sheets usando gspread.

Maneja toda la comunicación con la API de Google Sheets,
incluyendo autenticación, lectura y escritura de datos.
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import Optional
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

    def __init__(self):
        """Inicializa el repositorio (autenticación lazy)."""
        self.logger = logging.getLogger(__name__)
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._cache = get_cache()  # Cache singleton para reducir API calls

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

                # Crear credenciales desde archivo JSON
                creds = Credentials.from_service_account_file(
                    config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH,
                    scopes=config.get_scopes()
                )

                # Autorizar cliente gspread
                self._client = gspread.authorize(creds)

                self.logger.info("✅ Cliente gspread autenticado exitosamente")

            except FileNotFoundError:
                raise SheetsConnectionError(
                    "Archivo de credenciales no encontrado",
                    details=f"Path: {config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH}"
                )
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
        Actualiza una celda específica.

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

            # Convertir letra a índice de columna
            column_index = self._column_letter_to_index(column_letter)

            # Actualizar celda (gspread usa 1-indexed para columnas también)
            worksheet.update_cell(row, column_index + 1, value)

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
        Actualiza múltiples celdas en una sola operación (más eficiente).

        Invalida el cache de la hoja después de actualizar para asegurar
        que lecturas subsecuentes obtengan datos actualizados.

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

            # Ejecutar batch update
            worksheet.batch_update(batch_data)

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
