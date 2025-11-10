"""
Servicio de lógica de negocio para operaciones con Spools.

Responsabilidades:
- Obtener spools filtrados según elegibilidad de acciones
- Buscar spools por TAG
- Aplicar reglas de negocio vía ValidationService
"""
import logging
from typing import Optional

from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
from backend.services.validation_service import ValidationService
from backend.models.spool import Spool
from backend.models.enums import ActionType
from backend.config import config

logger = logging.getLogger(__name__)


class SpoolService:
    """
    Servicio de negocio para operaciones con spools.

    Combina:
    - SheetsRepository: Acceso a datos
    - SheetsService: Parseo de filas
    - ValidationService: Validación de reglas de negocio
    """

    def __init__(
        self,
        sheets_repository: Optional[SheetsRepository] = None,
        validation_service: Optional[ValidationService] = None
    ):
        """
        Inicializa el servicio con sus dependencias.

        Args:
            sheets_repository: Repositorio para acceso a Google Sheets (optional)
            validation_service: Servicio de validación (optional)
        """
        self.sheets_repository = sheets_repository or SheetsRepository()
        self.validation_service = validation_service or ValidationService()
        self.sheets_service = SheetsService()  # Stateless parser

    def _get_all_spools(self) -> list[Spool]:
        """
        Obtiene todos los spools desde Google Sheets.

        Returns:
            Lista de objetos Spool parseados

        Raises:
            SheetsConnectionError: Si falla la conexión con Sheets
        """
        logger.info("Retrieving all spools from Google Sheets")

        # Leer hoja de operaciones
        all_rows = self.sheets_repository.read_worksheet(
            config.HOJA_OPERACIONES_NOMBRE
        )

        # Parsear filas a objetos Spool (skip header)
        spools = []
        for row_index, row in enumerate(all_rows[1:], start=2):  # Skip header
            try:
                spool = self.sheets_service.parse_spool_row(row)
                spools.append(spool)
            except ValueError as e:
                logger.warning(
                    f"Skipping invalid row {row_index}: {str(e)}"
                )
                continue

        logger.info(f"Retrieved {len(spools)} spools from Sheets")
        return spools

    def get_spools_para_iniciar(self, operacion: ActionType) -> list[Spool]:
        """
        Obtiene spools elegibles para INICIAR la operación especificada.

        Filtra spools usando ValidationService para asegurar que:
        - ARM: V=0 (PENDIENTE), BA llena, BB vacía
        - SOLD: W=0 (PENDIENTE), BB llena, BD vacía

        Args:
            operacion: Tipo de operación (ActionType.ARM o ActionType.SOLD)

        Returns:
            Lista de spools que pueden iniciar la operación
            Lista vacía si ninguno es elegible

        Logs:
            INFO: Inicio de filtrado con operación
            DEBUG: Spools excluidos y razón
            INFO: Cantidad de spools elegibles encontrados
        """
        logger.info(f"Filtering spools to start {operacion.value}")

        # Obtener todos los spools
        all_spools = self._get_all_spools()

        # Filtrar usando ValidationService
        eligible_spools = []

        for spool in all_spools:
            try:
                # Intentar validación según operación
                if operacion == ActionType.ARM:
                    self.validation_service.validar_puede_iniciar_arm(spool)
                elif operacion == ActionType.SOLD:
                    self.validation_service.validar_puede_iniciar_sold(spool)
                else:
                    logger.warning(f"Unknown operation type: {operacion}")
                    continue

                # Si no lanzó excepción, es elegible
                eligible_spools.append(spool)

            except Exception as e:
                # Cualquier excepción significa que no es elegible
                logger.debug(
                    f"Spool {spool.tag_spool} not eligible for {operacion.value} start: "
                    f"{type(e).__name__} - {str(e)}"
                )
                continue

        logger.info(
            f"Found {len(eligible_spools)} spools eligible to start {operacion.value} "
            f"(from {len(all_spools)} total)"
        )

        return eligible_spools

    def get_spools_para_completar(
        self,
        operacion: ActionType,
        worker_nombre: str
    ) -> list[Spool]:
        """
        Obtiene spools elegibles para COMPLETAR por un trabajador específico.

        CRÍTICO: Solo retorna spools donde worker_nombre es quien inició la acción.

        Filtra spools usando ValidationService para asegurar que:
        - ARM: V=0.1 (EN_PROGRESO), BC=worker_nombre
        - SOLD: W=0.1 (EN_PROGRESO), BE=worker_nombre

        Args:
            operacion: Tipo de operación (ActionType.ARM o ActionType.SOLD)
            worker_nombre: Nombre del trabajador que intenta completar

        Returns:
            Lista de spools que el trabajador puede completar
            Lista vacía si el trabajador no tiene spools en progreso

        Logs:
            INFO: Inicio de filtrado con operación y trabajador
            DEBUG: Spools excluidos (incluyendo violaciones de propiedad)
            INFO: Cantidad de spools encontrados para el trabajador
        """
        logger.info(
            f"Filtering {operacion.value} spools for completion by '{worker_nombre}'"
        )

        # Obtener todos los spools
        all_spools = self._get_all_spools()

        # Filtrar usando ValidationService con ownership check
        eligible_spools = []

        for spool in all_spools:
            try:
                # Intentar validación según operación (incluye ownership)
                if operacion == ActionType.ARM:
                    self.validation_service.validar_puede_completar_arm(
                        spool,
                        worker_nombre
                    )
                elif operacion == ActionType.SOLD:
                    self.validation_service.validar_puede_completar_sold(
                        spool,
                        worker_nombre
                    )
                else:
                    logger.warning(f"Unknown operation type: {operacion}")
                    continue

                # Si no lanzó excepción, es elegible
                eligible_spools.append(spool)

            except Exception as e:
                # Cualquier excepción significa que no es elegible
                # Esto incluye NoAutorizadoError (ownership violation)
                logger.debug(
                    f"Spool {spool.tag_spool} not eligible for {operacion.value} "
                    f"completion by '{worker_nombre}': "
                    f"{type(e).__name__} - {str(e)}"
                )
                continue

        logger.info(
            f"Worker '{worker_nombre}' has {len(eligible_spools)} spools to complete "
            f"for {operacion.value} (from {len(all_spools)} total)"
        )

        return eligible_spools

    def find_spool_by_tag(self, tag_spool: str) -> Optional[Spool]:
        """
        Busca un spool específico por su TAG.

        Búsqueda case-insensitive con normalización de espacios.

        Args:
            tag_spool: TAG del spool a buscar (ej: "MK-1335-CW-25238-011")

        Returns:
            Spool si se encuentra, None si no existe

        Logs:
            INFO: Inicio de búsqueda con TAG
            DEBUG: Resultado de búsqueda (encontrado/no encontrado)
        """
        logger.info(f"Searching for spool with TAG: '{tag_spool}'")

        # Normalizar TAG para búsqueda case-insensitive
        tag_normalized = tag_spool.strip().upper()

        # Obtener todos los spools
        all_spools = self._get_all_spools()

        # Buscar por TAG normalizado
        for spool in all_spools:
            if spool.tag_spool.upper() == tag_normalized:
                logger.debug(f"Found spool: {spool.tag_spool}")
                return spool

        logger.debug(f"Spool with TAG '{tag_spool}' not found")
        return None
