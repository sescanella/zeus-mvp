"""
Dependency Injection para FastAPI.

Centraliza la creación y gestión de dependencias (services, repositories)
usando el patrón de Dependency Injection de FastAPI con Depends().

Estrategia:
- Singletons: SheetsRepository, SheetsService, ValidationService
  - Razón: Stateless o necesitan compartir estado (cache)
  - Lazy initialization: Se crean solo al primer uso
- Nuevas instancias: WorkerService, SpoolService, ActionService
  - Razón: Pueden tener estado en el futuro
  - Reciben dependencias inyectadas automáticamente por FastAPI

Testability:
- Fácil mockear dependencias en tests E2E
- Sobreescribir factory functions con app.dependency_overrides

Usage en routers:
    from backend.core.dependency import get_action_service
    from fastapi import Depends

    @router.post("/iniciar-accion")
    async def iniciar_accion(
        request: ActionRequest,
        action_service: ActionService = Depends(get_action_service)
    ):
        return action_service.iniciar_accion(...)
"""

from typing import Optional
from fastapi import Depends

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.services.sheets_service import SheetsService
from backend.core.column_map_cache import ColumnMapCache
from backend.services.validation_service import ValidationService
from backend.services.spool_service import SpoolService
from backend.services.spool_service_v2 import SpoolServiceV2
from backend.services.worker_service import WorkerService
from backend.services.action_service import ActionService
from backend.config import config


# ============================================================================
# SINGLETONS - Instancias compartidas por toda la aplicación
# ============================================================================

_sheets_repo_singleton: Optional[SheetsRepository] = None
_sheets_service_singleton: Optional[SheetsService] = None


# ============================================================================
# FACTORY FUNCTIONS - Singletons
# ============================================================================


def get_sheets_repository() -> SheetsRepository:
    """
    Factory para SheetsRepository (singleton).

    Retorna la misma instancia de SheetsRepository en todos los requests.
    Lazy initialization: se crea solo al primer uso.

    Razón del singleton:
    - Compartir cache entre requests (reduce API calls a Google Sheets)
    - Una sola conexión autenticada a Google Sheets por app
    - State management del cache centralizado

    Returns:
        Instancia singleton de SheetsRepository.

    Usage:
        sheets_repo: SheetsRepository = Depends(get_sheets_repository)
    """
    global _sheets_repo_singleton

    if _sheets_repo_singleton is None:
        _sheets_repo_singleton = SheetsRepository()

    return _sheets_repo_singleton


def get_sheets_service(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> SheetsService:
    """
    Factory para SheetsService (singleton v2.1).

    v2.1: Usa ColumnMapCache para obtener mapeo dinámico de columnas.
    Retorna la misma instancia de SheetsService en todos los requests.

    Razón del singleton:
    - Stateless parser (no tiene estado interno mutable)
    - column_map se obtiene de cache (compartido)
    - Reduce overhead de creación de objetos

    Returns:
        Instancia singleton de SheetsService con column_map.

    Usage:
        sheets_service: SheetsService = Depends(get_sheets_service)
    """
    global _sheets_service_singleton

    if _sheets_service_singleton is None:
        # Obtener column_map desde cache (lazy load)
        column_map = ColumnMapCache.get_or_build(
            config.HOJA_OPERACIONES_NOMBRE,
            sheets_repo
        )
        _sheets_service_singleton = SheetsService(column_map=column_map)

    return _sheets_service_singleton


# ============================================================================
# FACTORY FUNCTIONS - Nuevas Instancias con Dependencias Inyectadas
# ============================================================================


def get_metadata_repository(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> MetadataRepository:
    """
    Factory para MetadataRepository (nueva instancia por request).

    Retorna una nueva instancia de MetadataRepository para Event Sourcing.
    MetadataRepository maneja:
    - Escritura append-only de eventos en hoja "Metadata"
    - Lectura de eventos para reconstrucción de estado

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).

    Returns:
        Nueva instancia de MetadataRepository.

    Usage:
        metadata_repo: MetadataRepository = Depends(get_metadata_repository)
    """
    return MetadataRepository(sheets_repo=sheets_repo)


def get_validation_service(
    metadata_repository: MetadataRepository = Depends(get_metadata_repository)
) -> ValidationService:
    """
    Factory para ValidationService (nueva instancia por request).

    v2.0: ValidationService necesita MetadataRepository para reconstruir
    estados de spools desde eventos antes de aplicar validaciones.

    Ya NO es singleton porque necesita acceso a MetadataRepository que
    contiene estado dinámico por request.

    Returns:
        Nueva instancia de ValidationService con MetadataRepository inyectado.

    Usage:
        validation_service: ValidationService = Depends(get_validation_service)
    """
    return ValidationService(metadata_repository=metadata_repository)


def get_worker_service(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> WorkerService:
    """
    Factory para WorkerService (nueva instancia por request).

    Retorna una nueva instancia de WorkerService con dependencias inyectadas.
    WorkerService requiere:
    - SheetsRepository: Para leer hoja "Trabajadores"

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).

    Returns:
        Nueva instancia de WorkerService con dependencias configuradas.

    Usage:
        worker_service: WorkerService = Depends(get_worker_service)
    """
    return WorkerService(sheets_repository=sheets_repo)


def get_spool_service(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    validation_service: ValidationService = Depends(get_validation_service)
) -> SpoolService:
    """
    Factory para SpoolService (nueva instancia por request).

    Retorna una nueva instancia de SpoolService con dependencias inyectadas.
    SpoolService requiere:
    - SheetsRepository: Para leer hoja "Operaciones"
    - ValidationService: Para validar elegibilidad de spools

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).
        validation_service: Servicio de validación (inyectado automáticamente).

    Returns:
        Nueva instancia de SpoolService con dependencias configuradas.

    Usage:
        spool_service: SpoolService = Depends(get_spool_service)
    """
    return SpoolService(
        sheets_repository=sheets_repo,
        validation_service=validation_service
    )


def get_spool_service_v2(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repository: MetadataRepository = Depends(get_metadata_repository)
) -> SpoolServiceV2:
    """
    Factory para SpoolServiceV2 (nueva instancia por request).

    Retorna una nueva instancia de SpoolServiceV2 con mapeo dinámico de columnas
    y Event Sourcing v2.0 integrado.

    SpoolServiceV2 implementa:
    - Mapeo dinámico de columnas (lee header row 1)
    - Resistente a cambios de estructura en spreadsheet
    - Event Sourcing v2.0: Reconstruye estado ARM/SOLD desde Metadata
    - Reglas de negocio correctas para las 4 operaciones:
      * INICIAR ARM: Fecha_Materiales llena Y ARM PENDIENTE (desde Metadata)
      * COMPLETAR ARM: ARM EN_PROGRESO (desde Metadata)
      * INICIAR SOLD: ARM COMPLETADO Y SOLD PENDIENTE (desde Metadata)
      * COMPLETAR SOLD: SOLD EN_PROGRESO (desde Metadata)

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).
        metadata_repository: Repositorio Metadata para Event Sourcing (inyectado automáticamente).

    Returns:
        Nueva instancia de SpoolServiceV2 con dependencias configuradas.

    Usage:
        spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
    """
    return SpoolServiceV2(
        sheets_repository=sheets_repo,
        metadata_repository=metadata_repository
    )


def get_action_service(
    metadata_repository: MetadataRepository = Depends(get_metadata_repository),
    validation_service: ValidationService = Depends(get_validation_service),
    worker_service: WorkerService = Depends(get_worker_service),
    spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
) -> ActionService:
    """
    Factory para ActionService (nueva instancia por request) - CRÍTICO.

    Retorna una nueva instancia de ActionService con TODAS las dependencias
    inyectadas. ActionService v2.0 usa Event Sourcing con Metadata y
    SpoolServiceV2 con mapeo dinámico de columnas.

    ActionService coordina:
    - Validación de trabajadores (WorkerService)
    - Búsqueda de spools (SpoolServiceV2 - mapeo dinámico)
    - Validación de ownership (ValidationService)
    - Escritura de eventos en Metadata (MetadataRepository)

    Args:
        metadata_repository: Repositorio Metadata para Event Sourcing (v2.0).
        validation_service: Servicio de validación (inyectado automáticamente).
        worker_service: Servicio de trabajadores (inyectado automáticamente).
        spool_service_v2: SpoolServiceV2 con mapeo dinámico (inyectado automáticamente).

    Returns:
        Nueva instancia de ActionService con todas las dependencias configuradas.

    Usage:
        action_service: ActionService = Depends(get_action_service)

    Note:
        Este es el service más importante del sistema. Coordina el workflow
        completo de INICIAR y COMPLETAR acciones de manufactura usando
        Event Sourcing (v2.0) y mapeo dinámico de columnas (SpoolServiceV2).
    """
    return ActionService(
        metadata_repository=metadata_repository,
        validation_service=validation_service,
        spool_service=spool_service_v2,
        worker_service=worker_service
    )


# ============================================================================
# UTILITY FUNCTIONS - Para testing y debugging
# ============================================================================


def reset_singletons() -> None:
    """
    Resetea todos los singletons a None.

    Útil para testing cuando se necesita forzar la recreación de instancias
    con configuraciones diferentes.

    WARNING: NO usar en producción. Solo para tests.

    Usage en tests:
        from backend.core.dependency import reset_singletons

        def test_something():
            reset_singletons()
            # Ahora los singletons se recrearán en el próximo uso
    """
    global _sheets_repo_singleton, _sheets_service_singleton, _validation_service_singleton

    _sheets_repo_singleton = None
    _sheets_service_singleton = None
    _validation_service_singleton = None
