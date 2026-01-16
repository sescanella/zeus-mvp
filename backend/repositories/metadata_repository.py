"""
Repositorio para operaciones en la hoja Metadata (Event Sourcing).

Maneja escritura append-only de eventos y lectura para reconstrucción de estado.
"""
import gspread
import logging
from typing import Optional
from functools import wraps
import time

from backend.config import config
from backend.models.metadata import MetadataEvent, EventoTipo, Accion
from backend.exceptions import SheetsConnectionError, SheetsUpdateError
from backend.repositories.sheets_repository import SheetsRepository


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


class MetadataRepository:
    """
    Repositorio para operaciones en la hoja Metadata (Event Sourcing).

    Responsabilidades:
    - Escritura append-only de eventos (inmutables)
    - Lectura de eventos para reconstrucción de estado
    - Consultas de eventos por spool, tipo, trabajador, etc.

    Arquitectura Event Sourcing:
    - Todos los eventos son inmutables (no se modifican ni eliminan)
    - El estado actual se reconstruye consultando el log de eventos
    - La hoja Operaciones es READ-ONLY (solo fuente de datos base)
    """

    def __init__(self, sheets_repo: SheetsRepository):
        """
        Inicializa el repositorio de Metadata.

        Args:
            sheets_repo: Instancia de SheetsRepository para acceso a Google Sheets
        """
        self.logger = logging.getLogger(__name__)
        self.sheets_repo = sheets_repo
        self._worksheet: Optional[gspread.Worksheet] = None

    def _get_worksheet(self) -> gspread.Worksheet:
        """
        Obtiene la hoja Metadata (lazy loading).

        Returns:
            gspread.Worksheet: Hoja de Metadata

        Raises:
            SheetsConnectionError: Si falla la conexión
        """
        if not self._worksheet:
            spreadsheet = self.sheets_repo._get_spreadsheet()
            self._worksheet = spreadsheet.worksheet(config.HOJA_METADATA_NOMBRE)
            self.logger.info(f"Hoja '{config.HOJA_METADATA_NOMBRE}' cargada correctamente")

        return self._worksheet

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def append_event(self, event: MetadataEvent) -> None:
        """
        Escribe un nuevo evento en la hoja Metadata (append-only).

        Args:
            event: Evento a escribir

        Raises:
            SheetsUpdateError: Si falla la escritura
        """
        try:
            worksheet = self._get_worksheet()
            row_data = event.to_sheets_row()

            self.logger.info(
                f"Escribiendo evento: {event.evento_tipo} - Spool: {event.tag_spool} - Worker: {event.worker_nombre}"
            )

            # Append a la última fila (después de headers)
            worksheet.append_row(row_data, value_input_option='USER_ENTERED')

            self.logger.info(f"Evento escrito exitosamente: ID={event.id}")

        except gspread.exceptions.APIError as e:
            raise SheetsUpdateError(
                f"Error al escribir evento en Metadata",
                details=f"evento_tipo={event.evento_tipo}, spool={event.tag_spool}, error={str(e)}"
            )
        except Exception as e:
            raise SheetsUpdateError(
                f"Error inesperado al escribir evento",
                details=str(e)
            )

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def get_events_by_spool(self, tag_spool: str) -> list[MetadataEvent]:
        """
        Obtiene todos los eventos de un spool específico.

        Args:
            tag_spool: Código del spool

        Returns:
            list[MetadataEvent]: Lista de eventos ordenados por timestamp (asc)

        Raises:
            SheetsConnectionError: Si falla la lectura
        """
        try:
            worksheet = self._get_worksheet()
            all_values = worksheet.get_all_values()

            # Filtrar por tag_spool (columna D, índice 3)
            # Saltar fila de headers (índice 0)
            events = []
            for row in all_values[1:]:  # Desde fila 2 en adelante
                if len(row) >= 9 and row[3] == tag_spool:  # Columna D (tag_spool)
                    try:
                        event = MetadataEvent.from_sheets_row(row)
                        events.append(event)
                    except Exception as e:
                        self.logger.warning(f"Error al parsear evento: {e}, row={row}")
                        continue

            # Ordenar por timestamp (ascendente)
            events.sort(key=lambda e: e.timestamp)

            self.logger.info(f"Encontrados {len(events)} eventos para spool: {tag_spool}")
            return events

        except gspread.exceptions.APIError as e:
            raise SheetsConnectionError(
                f"Error al leer eventos del spool {tag_spool}",
                details=str(e)
            )

    def get_all_events(self) -> list[MetadataEvent]:
        """
        Obtiene TODOS los eventos de la hoja Metadata.

        PERFORMANCE CRITICAL: Este método lee toda la hoja UNA VEZ para batch queries.
        Usado por SpoolServiceV2 para evitar N lecturas individuales.

        Returns:
            list[MetadataEvent]: Lista de todos los eventos ordenados por timestamp (asc)

        Raises:
            SheetsConnectionError: Si falla la lectura
        """
        self.logger.info("[METADATA DEBUG] === ENTERING get_all_events ===")
        try:
            self.logger.info("[METADATA DEBUG] Getting worksheet...")
            worksheet = self._get_worksheet()
            self.logger.info(f"[METADATA DEBUG] ✅ Got worksheet: {config.HOJA_METADATA_NOMBRE}")

            self.logger.info("[METADATA DEBUG] Reading all values from sheet...")
            all_values = worksheet.get_all_values()
            self.logger.info(f"[METADATA DEBUG] ✅ Read {len(all_values)} rows from sheet (including header)")

            # Parsear TODOS los eventos (saltar header row 0)
            self.logger.info("[METADATA DEBUG] Parsing events from rows...")
            events = []
            parse_errors = 0
            for row_idx, row in enumerate(all_values[1:], start=2):  # Desde fila 2
                if len(row) >= 9:  # Validar que tenga todas las columnas
                    try:
                        event = MetadataEvent.from_sheets_row(row)
                        events.append(event)
                    except Exception as e:
                        parse_errors += 1
                        self.logger.warning(f"[METADATA DEBUG] Error parsing row {row_idx}: {e}")
                        continue
                else:
                    self.logger.warning(f"[METADATA DEBUG] Row {row_idx} has only {len(row)} columns (expected >= 9)")

            self.logger.info(f"[METADATA DEBUG] Parsed {len(events)} events ({parse_errors} parse errors)")

            # Ordenar por timestamp (ascendente)
            self.logger.info("[METADATA DEBUG] Sorting events by timestamp...")
            events.sort(key=lambda e: e.timestamp)
            self.logger.info("[METADATA DEBUG] ✅ Events sorted")

            self.logger.info(f"[BATCH] Loaded {len(events)} total events from Metadata")
            self.logger.info("[METADATA DEBUG] === EXITING get_all_events SUCCESS ===")
            return events

        except gspread.exceptions.APIError as e:
            self.logger.error(f"[METADATA DEBUG] ❌ APIError: {e}")
            raise SheetsConnectionError(
                "Error al leer todos los eventos de Metadata",
                details=str(e)
            )
        except Exception as e:
            # Catch all other exceptions (WorksheetNotFound, parsing errors, etc.)
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"[METADATA DEBUG] ❌ Unexpected error: {type(e).__name__}: {e}")
            self.logger.error(f"[METADATA DEBUG] Full traceback:\n{error_details}")
            raise SheetsConnectionError(
                "Error inesperado al leer eventos de Metadata",
                details=f"{type(e).__name__}: {str(e)}"
            )

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def get_latest_event(self, tag_spool: str, evento_tipo: Optional[EventoTipo] = None) -> Optional[MetadataEvent]:
        """
        Obtiene el último evento de un spool (opcionalmente filtrado por tipo).

        Args:
            tag_spool: Código del spool
            evento_tipo: Tipo de evento a buscar (opcional)

        Returns:
            MetadataEvent o None si no hay eventos

        Raises:
            SheetsConnectionError: Si falla la lectura
        """
        events = self.get_events_by_spool(tag_spool)

        if not events:
            return None

        # Filtrar por tipo de evento si se especifica
        if evento_tipo:
            events = [e for e in events if e.evento_tipo == evento_tipo]

        # Retornar el último (ya están ordenados por timestamp asc)
        return events[-1] if events else None

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def has_completed_action(self, tag_spool: str, operacion: str) -> bool:
        """
        Verifica si un spool tiene una acción completada para una operación específica.

        Args:
            tag_spool: Código del spool
            operacion: Operación a verificar (ARM, SOLD, METROLOGIA)

        Returns:
            bool: True si la acción está completada

        Raises:
            SheetsConnectionError: Si falla la lectura
        """
        # Construir el tipo de evento COMPLETAR para la operación
        evento_tipo_completar = EventoTipo(f"COMPLETAR_{operacion}")

        # Buscar el último evento de completar para esta operación
        latest_event = self.get_latest_event(tag_spool, evento_tipo_completar)

        return latest_event is not None

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def get_worker_in_progress(self, tag_spool: str, operacion: str) -> Optional[str]:
        """
        Obtiene el nombre del trabajador que tiene en progreso una operación específica.

        Args:
            tag_spool: Código del spool
            operacion: Operación (ARM, SOLD, METROLOGIA)

        Returns:
            str: Nombre del trabajador o None si no hay acción en progreso

        Raises:
            SheetsConnectionError: Si falla la lectura
        """
        events = self.get_events_by_spool(tag_spool)

        # Filtrar eventos de esta operación
        op_events = [e for e in events if e.operacion == operacion]

        if not op_events:
            return None

        # Ordenar por timestamp (descendente) para obtener el último primero
        op_events.sort(key=lambda e: e.timestamp, reverse=True)

        # Buscar el último INICIAR y verificar que no esté COMPLETADO
        for event in op_events:
            if event.accion == Accion.COMPLETAR:
                # Ya está completado, no hay acción en progreso
                return None
            elif event.accion == Accion.INICIAR:
                # Encontramos INICIAR sin COMPLETAR posterior
                return event.worker_nombre

        return None
