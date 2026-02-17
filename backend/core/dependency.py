"""
Dependency Injection para FastAPI.

Centraliza la creación y gestión de dependencias (services, repositories)
usando el patrón de Dependency Injection de FastAPI con Depends().

Estrategia:
- Singletons: SheetsRepository, SheetsService, ValidationService
  - Razon: Stateless o necesitan compartir estado (cache)
  - Lazy initialization: Se crean solo al primer uso
- Nuevas instancias: WorkerService, SpoolService, OccupationService
  - Razon: Pueden tener estado en el futuro
  - Reciben dependencias inyectadas automaticamente por FastAPI

v4.0: ActionService removed - v2.1 endpoints deprecated in favor of v4.0 INICIAR/FINALIZAR

Testability:
- Facil mockear dependencias en tests E2E
- Sobreescribir factory functions con app.dependency_overrides

Usage en routers:
    from backend.core.dependency import get_occupation_service_v4
    from fastapi import Depends

    @router.post("/api/v4/occupation/iniciar")
    async def iniciar_spool(
        request: IniciarRequest,
        occupation_service: OccupationService = Depends(get_occupation_service_v4)
    ):
        return occupation_service.iniciar_spool(...)
"""

from typing import Optional
from fastapi import Depends

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.union_repository import UnionRepository
from backend.services.sheets_service import SheetsService
from backend.services.conflict_service import ConflictService
from backend.core.column_map_cache import ColumnMapCache
from backend.services.validation_service import ValidationService
from backend.services.spool_service import SpoolService
from backend.services.spool_service_v2 import SpoolServiceV2
from backend.services.worker_service import WorkerService
# ActionService removed - v2.1 endpoints deprecated in favor of v4.0 INICIAR/FINALIZAR
from backend.services.occupation_service import OccupationService
from backend.services.union_service import UnionService
from backend.services.state_service import StateService
from backend.services.history_service import HistoryService
from backend.services.metrologia_service import MetrologiaService
from backend.services.reparacion_service import ReparacionService
from backend.services.cycle_counter_service import CycleCounterService
from backend.repositories.forms_repository import FormsRepository
from backend.services.forms.no_conformidad_service import NoConformidadService
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
        # v3.0 mode enabled to support reparacion features (estado_detalle, ocupado_por)
        # Force v3.0 compatibility mode for REPARACION endpoint (2026-02-05)
        _sheets_repo_singleton = SheetsRepository(compatibility_mode="v3.0")

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


def get_union_repository(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> UnionRepository:
    """
    Factory para UnionRepository (nueva instancia por request) - v4.0 PHASE 8.

    v4.0 Phase 8: UnionRepository provides union-level CRUD operations.

    UnionRepository handles:
    - Query unions by TAG_SPOOL or OT (foreign keys)
    - Get available unions for ARM/SOLD operations
    - Batch update ARM/SOLD completion for multiple unions
    - Calculate metrics (pulgadas-diámetro, completion counts)
    - Dynamic column mapping via ColumnMapCache

    Args:
        sheets_repo: Repository for Google Sheets access (injected).

    Returns:
        Nueva instancia de UnionRepository.

    Usage:
        union_repo: UnionRepository = Depends(get_union_repository)

    Note:
        v4.0 Phase 8: Union-level tracking foundation for pulgadas-diámetro metrics.
    """
    return UnionRepository(sheets_repo=sheets_repo)


def get_validation_service() -> ValidationService:
    """
    Factory para ValidationService (nueva instancia por request).

    v2.1 Direct Read: ValidationService lee estados directamente desde
    columnas de Operaciones, NO necesita MetadataRepository.

    Returns:
        Nueva instancia de ValidationService (sin dependencias).

    Usage:
        validation_service: ValidationService = Depends(get_validation_service)
    """
    return ValidationService()


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
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> SpoolServiceV2:
    """
    Factory para SpoolServiceV2 (nueva instancia por request).

    v2.1 Direct Read: SpoolServiceV2 con mapeo dinámico de columnas
    y lectura directa de estados desde Operaciones (sin Event Sourcing).

    SpoolServiceV2 implementa:
    - Mapeo dinámico de columnas (lee header row 1)
    - Resistente a cambios de estructura en spreadsheet
    - Direct Read v2.1: Lee estados directamente desde columnas
    - Reglas de negocio basadas en presencia de datos:
      * INICIAR ARM: Fecha_Materiales llena Y Armador vacío
      * COMPLETAR ARM: Armador lleno Y Fecha_Armado vacía
      * INICIAR SOLD: Fecha_Armado llena Y Soldador vacío
      * COMPLETAR SOLD: Soldador lleno Y Fecha_Soldadura vacía

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).

    Returns:
        Nueva instancia de SpoolServiceV2 con dependencias configuradas.

    Usage:
        spool_service_v2: SpoolServiceV2 = Depends(get_spool_service_v2)
    """
    return SpoolServiceV2(sheets_repository=sheets_repo)


# get_action_service removed - v2.1 endpoints deprecated in favor of v4.0 INICIAR/FINALIZAR




def get_conflict_service(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> ConflictService:
    """
    Factory para ConflictService (nueva instancia por request) - v3.0 OPTIMISTIC LOCKING.

    v3.0: ConflictService handles version conflicts with automatic retry.

    ConflictService implementa:
    - Version token generation (UUID4)
    - Exponential backoff retry with jitter
    - Automatic retry on version conflicts (max 3 attempts)
    - Conflict pattern detection (hot spots)
    - Conflict metrics tracking

    Args:
        sheets_repo: Repository for reading/writing sheets with version checks.

    Returns:
        Nueva instancia de ConflictService con retry configuration.

    Usage:
        conflict_service: ConflictService = Depends(get_conflict_service)

    Note:
        Single-user mode: Version tokens provide data consistency for any concurrent operations.
        No distributed locks needed with 1 tablet.
    """
    return ConflictService(sheets_repository=sheets_repo)




def get_occupation_service(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repository: MetadataRepository = Depends(get_metadata_repository),
    conflict_service: ConflictService = Depends(get_conflict_service)
) -> OccupationService:
    """
    Factory para OccupationService (nueva instancia por request) - Single-user mode.

    Single-user: OccupationService orchestrates TOMAR/PAUSAR/COMPLETAR operations
    with direct Sheets validation and optimistic locking.

    OccupationService coordinates:
    - Version-aware updates with retry (ConflictService)
    - Sheets writes to Ocupado_Por/Fecha_Ocupacion (SheetsRepository)
    - Audit logging to Metadata (MetadataRepository)

    Args:
        sheets_repo: Repository for Sheets writes (injected).
        metadata_repository: Repository for audit logging (injected).
        conflict_service: Service for version conflict handling (injected).

    Returns:
        Nueva instancia de OccupationService con todas las dependencias.

    Usage:
        occupation_service: OccupationService = Depends(get_occupation_service)

    Note:
        Single-user mode: No distributed locks needed (1 tablet, 1 worker).
        Version tokens provide data consistency for concurrent operations.
    """
    return OccupationService(
        sheets_repository=sheets_repo,
        metadata_repository=metadata_repository,
        conflict_service=conflict_service
    )


def get_occupation_service_v4(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repository: MetadataRepository = Depends(get_metadata_repository),
    conflict_service: ConflictService = Depends(get_conflict_service),
    union_repo: UnionRepository = Depends(get_union_repository),
    validation_service: ValidationService = Depends(get_validation_service)
) -> OccupationService:
    """
    Factory for OccupationService with v4.0 union support (INICIAR/FINALIZAR workflows).

    Used by POST /api/v4/occupation/iniciar and POST /api/v4/occupation/finalizar.
    Builds UnionService and OccupationService with union_repository, validation_service,
    and union_service for v4.0 operations.

    Single-user mode: No distributed locks or SSE event publishing.
    """
    union_service = UnionService(
        union_repo=union_repo,
        metadata_repo=metadata_repository,
        sheets_repo=sheets_repo,
    )
    return OccupationService(
        sheets_repository=sheets_repo,
        metadata_repository=metadata_repository,
        conflict_service=conflict_service,
        union_repository=union_repo,
        validation_service=validation_service,
        union_service=union_service,
    )


def get_state_service(
    occupation_service: OccupationService = Depends(get_occupation_service),
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repository: MetadataRepository = Depends(get_metadata_repository)
) -> StateService:
    """
    Factory para StateService (nueva instancia por request) - Single-user mode.

    StateService coordinates:
    - ARM and SOLD state machines (per-operation)
    - OccupationService (occupation tracking)
    - Estado_Detalle updates (combined state display)
    - Hydration logic (sync state machines with Sheets columns)

    Args:
        occupation_service: Service for occupation operations (injected).
        sheets_repo: Repository for Sheets reads/writes (injected).
        metadata_repository: Repository for audit logging (injected).

    Returns:
        Nueva instancia de StateService con todas las dependencias.

    Usage:
        state_service: StateService = Depends(get_state_service)

    Note:
        Single-user mode: No SSE event publishing needed.
    """
    return StateService(
        occupation_service=occupation_service,
        sheets_repository=sheets_repo,
        metadata_repository=metadata_repository
    )


def get_history_service(
    metadata_repository: MetadataRepository = Depends(get_metadata_repository),
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> HistoryService:
    """
    Factory para HistoryService (nueva instancia por request) - v3.0 PHASE 3.

    v3.0 Phase 3: HistoryService aggregates Metadata events into occupation history.

    HistoryService provides:
    - Occupation timeline showing which workers worked on each spool
    - Duration calculation between TOMAR and PAUSAR/COMPLETAR events
    - Human-readable duration format (e.g., "2h 15m")

    Args:
        metadata_repository: Repository for reading Metadata events (injected).
        sheets_repo: Repository for spool verification (injected).

    Returns:
        Nueva instancia de HistoryService con todas las dependencias.

    Usage:
        history_service: HistoryService = Depends(get_history_service)

    Note:
        v3.0 Phase 3: HistoryService reads from Metadata for audit trail visibility.
    """
    return HistoryService(
        metadata_repository=metadata_repository,
        sheets_repository=sheets_repo
    )


def get_metrologia_service(
    validation_service: ValidationService = Depends(get_validation_service),
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repository: MetadataRepository = Depends(get_metadata_repository)
) -> MetrologiaService:
    """
    Factory para MetrologiaService (nueva instancia por request) - Single-user mode.

    MetrologiaService provides:
    - Instant completion (no occupation phase, no TOMAR)
    - Binary resultado (APROBADO/RECHAZADO) enforcement
    - Prerequisite validation (ARM + SOLD complete, not occupied)
    - Fecha_QC_Metrologia column updates
    - Metadata audit logging with resultado

    Args:
        validation_service: Service for prerequisite checks (injected).
        sheets_repo: Repository for Sheets reads/writes (injected).
        metadata_repository: Repository for audit logging (injected).

    Returns:
        Nueva instancia de MetrologiaService con todas las dependencias.

    Usage:
        metrologia_service: MetrologiaService = Depends(get_metrologia_service)

    Note:
        Skips occupation workflow entirely - inspection completes atomically.
        Single-user mode: No SSE event publishing needed.
    """
    return MetrologiaService(
        validation_service=validation_service,
        sheets_repository=sheets_repo,
        metadata_repository=metadata_repository
    )


def get_reparacion_service(
    validation_service: ValidationService = Depends(get_validation_service),
    sheets_repo: SheetsRepository = Depends(get_sheets_repository),
    metadata_repository: MetadataRepository = Depends(get_metadata_repository)
) -> ReparacionService:
    """
    Factory para ReparacionService (nueva instancia por request) - Single-user mode.

    ReparacionService provides:
    - TOMAR/PAUSAR/COMPLETAR/CANCELAR operations for RECHAZADO spools
    - Cycle tracking with embedded cycle counter (no dedicated column)
    - BLOQUEADO enforcement after 3 consecutive rejections (HTTP 403)
    - Multi-worker access (no role restriction)
    - Automatic return to PENDIENTE_METROLOGIA after completion

    Args:
        validation_service: Service for prerequisite checks (injected).
        sheets_repo: Repository for Sheets reads/writes (injected).
        metadata_repository: Repository for audit logging (injected).

    Returns:
        Nueva instancia de ReparacionService con todas las dependencias.

    Usage:
        reparacion_service: ReparacionService = Depends(get_reparacion_service)

    Note:
        Cycle tracking embedded in Estado_Detalle (no schema changes).
        Single-user mode: No SSE event publishing needed.
    """
    cycle_counter = CycleCounterService()
    return ReparacionService(
        validation_service=validation_service,
        cycle_counter_service=cycle_counter,
        sheets_repository=sheets_repo,
        metadata_repository=metadata_repository
    )


# ============================================================================
# FACTORY FUNCTIONS - Forms (Modular Monolith)
# ============================================================================


def get_forms_repository(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> FormsRepository:
    """Factory for FormsRepository (new instance per request)."""
    return FormsRepository(sheets_repo=sheets_repo)


def get_no_conformidad_service(
    forms_repo: FormsRepository = Depends(get_forms_repository),
    worker_service: WorkerService = Depends(get_worker_service),
) -> NoConformidadService:
    """Factory for NoConformidadService (new instance per request)."""
    return NoConformidadService(
        forms_repo=forms_repo,
        worker_service=worker_service,
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
    global _sheets_repo_singleton, _sheets_service_singleton

    _sheets_repo_singleton = None
    _sheets_service_singleton = None
