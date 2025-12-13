"""
Servicio de lógica de negocio para operaciones con Workers (Trabajadores).

Responsabilidades:
- Obtener trabajadores activos
- Buscar trabajadores por nombre
- Filtrar trabajadores inactivos
"""
import logging
from typing import Optional

from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
from backend.models.worker import Worker
from backend.config import config

logger = logging.getLogger(__name__)


class WorkerService:
    """
    Servicio de negocio para operaciones con trabajadores.

    Combina:
    - SheetsRepository: Acceso a datos
    - SheetsService: Parseo de filas
    """

    def __init__(
        self,
        sheets_repository: Optional[SheetsRepository] = None
    ):
        """
        Inicializa el servicio con sus dependencias.

        Args:
            sheets_repository: Repositorio para acceso a Google Sheets (optional)
        """
        self.sheets_repository = sheets_repository or SheetsRepository()
        self.sheets_service = SheetsService()  # Stateless parser

    def _get_all_workers(self) -> list[Worker]:
        """
        Obtiene todos los trabajadores desde Google Sheets.

        Returns:
            Lista de objetos Worker parseados (activos e inactivos)

        Raises:
            SheetsConnectionError: Si falla la conexión con Sheets
        """
        logger.info("Retrieving all workers from Google Sheets")

        # Leer hoja de trabajadores
        all_rows = self.sheets_repository.read_worksheet(
            config.HOJA_TRABAJADORES_NOMBRE
        )

        # Parsear filas a objetos Worker (skip header)
        workers = []
        for row_index, row in enumerate(all_rows[1:], start=2):  # Skip header
            try:
                worker = self.sheets_service.parse_worker_row(row)
                workers.append(worker)
            except ValueError as e:
                logger.warning(
                    f"Skipping invalid worker row {row_index}: {str(e)}"
                )
                continue

        logger.info(f"Retrieved {len(workers)} workers from Sheets")
        return workers

    def get_all_active_workers(self) -> list[Worker]:
        """
        Obtiene todos los trabajadores activos del sistema.

        Filtra trabajadores donde activo=True.

        Returns:
            Lista de objetos Worker con activo=True
            Lista vacía si no hay trabajadores activos

        Logs:
            INFO: Inicio de operación
            DEBUG: Cantidad de trabajadores activos encontrados
        """
        logger.info("Retrieving all active workers")

        # Obtener todos los trabajadores
        all_workers = self._get_all_workers()

        # Filtrar solo activos
        active_workers = [w for w in all_workers if w.activo]

        logger.debug(
            f"Found {len(active_workers)} active workers "
            f"(from {len(all_workers)} total)"
        )

        return active_workers

    def find_worker_by_nombre(self, nombre: str) -> Optional[Worker]:
        """
        Busca un trabajador por su nombre (case-insensitive).

        Solo busca entre trabajadores ACTIVOS.
        Normaliza espacios y mayúsculas/minúsculas para la búsqueda.

        Args:
            nombre: Nombre del trabajador a buscar (puede incluir apellido)

        Returns:
            Objeto Worker si se encuentra y está activo
            None si no existe o está inactivo

        Logs:
            INFO: Inicio de búsqueda con nombre
            DEBUG: Resultado de búsqueda (encontrado/no encontrado)
        """
        logger.info(f"Searching for worker: '{nombre}'")

        # Normalizar nombre para búsqueda case-insensitive
        nombre_normalized = nombre.strip().lower()

        # Obtener trabajadores activos
        active_workers = self.get_all_active_workers()

        # Buscar por nombre completo normalizado
        for worker in active_workers:
            # Comparar con nombre_completo (nombre + apellido)
            if worker.nombre_completo.lower() == nombre_normalized:
                logger.debug(f"Found worker: {worker.nombre_completo}")
                return worker

        logger.debug(f"Worker '{nombre}' not found among active workers")
        return None

    def find_worker_by_id(self, worker_id: int) -> Optional[Worker]:
        """
        Busca un trabajador por su ID (v2.0).

        Solo busca entre trabajadores ACTIVOS.

        Args:
            worker_id: ID del trabajador a buscar (ej: 93, 94, 95)

        Returns:
            Objeto Worker si se encuentra y está activo
            None si no existe o está inactivo

        Logs:
            INFO: Inicio de búsqueda con ID
            DEBUG: Resultado de búsqueda (encontrado/no encontrado)

        Examples:
            >>> service.find_worker_by_id(93)
            Worker(id=93, nombre="Mauricio", apellido="Rodriguez", activo=True)

            >>> service.find_worker_by_id(999)  # No existe
            None
        """
        logger.info(f"Searching for worker by ID: {worker_id}")

        # Obtener trabajadores activos
        active_workers = self.get_all_active_workers()

        # Buscar por ID
        for worker in active_workers:
            if worker.id == worker_id:
                logger.debug(f"Found worker: {worker.nombre_completo} (ID: {worker.id})")
                return worker

        logger.debug(f"Worker ID {worker_id} not found among active workers")
        return None
