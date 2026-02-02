# Phase 10: Backend Services & Validation - Research Findings

## Executive Summary

This research provides the technical foundation for implementing Phase 10's backend services that orchestrate union selection workflows with intelligent auto-determination (PAUSAR vs COMPLETAR) and ARM-before-SOLD validation. The services sit between the API layer (Phase 11) and repository layer (Phase 8), enforcing business rules while coordinating batch updates and metadata logging.

## Current Architecture Analysis

### 1. Service Layer Patterns

#### Existing Services Structure
```
backend/services/
├── occupation_service.py      # v3.0 TOMAR/PAUSAR/COMPLETAR (spool-level)
├── state_service.py          # State machine orchestration
├── validation_service.py     # Business rule validation
├── metrologia_service.py     # Instant inspection workflow
├── conflict_service.py       # Optimistic locking with retry
└── redis_lock_service.py     # Redis lock management
```

**Key Patterns Observed:**
- **Dependency Injection**: All services receive repositories via constructor
- **Service Orchestration**: StateService coordinates multiple services
- **Retry Logic**: ConflictService handles version conflicts with exponential backoff
- **Event Publishing**: RedisEventService for real-time SSE updates
- **Audit Trail**: Every operation logs to MetadataRepository

### 2. Union Repository Capabilities

The UnionRepository (Phase 8) already provides:

```python
# Batch update methods with < 1s performance
batch_update_arm(tag_spool, union_ids, worker, timestamp) -> int
batch_update_sold(tag_spool, union_ids, worker, timestamp) -> int

# Query methods using OT as foreign key
get_by_ot(ot: str) -> list[Union]
get_disponibles_arm_by_ot(ot: str) -> list[Union]
get_disponibles_sold_by_ot(ot: str) -> list[Union]

# Metrics calculation
calculate_metrics(ot: str) -> dict  # Single-pass for all metrics
sum_pulgadas_arm(ot: str) -> float  # 2 decimal precision
count_completed_arm(ot: str) -> int
```

**Critical Findings:**
- Uses OT as primary foreign key (not TAG_SPOOL)
- Batch updates use gspread.batch_update() with A1 notation
- ARM validation already built into batch_update_sold()
- No caching - always fresh data for consistency

### 3. State Machine Integration

Current state machines handle spool-level transitions:

```python
# ARM State Machine
pendiente -> en_progreso (iniciar)
en_progreso -> pausado (pausar)
pausado -> en_progreso (reanudar)
en_progreso -> completado (completar)

# SOLD State Machine (similar transitions)
# Metrología State Machine (instant completion)
```

**v4.0 Requirements:**
- Keep state machines at spool level (not union level)
- Trigger state transitions AFTER union selection
- Auto-determination decides which transition to trigger

### 4. Metadata Event Logging

MetadataRepository provides robust event logging:

```python
# Single event logging
log_event(evento_tipo, tag_spool, worker_id, ..., n_union=None)

# Batch logging with auto-chunking
batch_log_events(events: list[MetadataEvent]) -> None

# Union-specific event builder
build_union_events(tag_spool, worker_id, union_ids, union_details)
```

**Key Features:**
- Auto-chunks at 900 rows for Google Sheets safety
- N_UNION column (position 11) added for v4.0
- Event types: UNION_ARM_REGISTRADA, UNION_SOLD_REGISTRADA, SPOOL_CANCELADO

## Implementation Patterns

### 1. Service Method Signatures

Based on existing patterns, the new services should follow:

```python
class UnionService:
    def __init__(self, union_repo, metadata_repo, sheets_repo):
        """Dependency injection pattern"""

    async def process_selection(
        self,
        tag_spool: str,
        worker: str,
        operacion: Literal["ARM", "SOLD"],
        union_ids: list[str],
        timestamp: datetime
    ) -> dict:
        """Process union selection with batch update"""

    def calcular_pulgadas(
        self,
        unions: list[Union]
    ) -> float:
        """Calculate pulgadas-diámetro sum"""

    def build_eventos_metadata(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        operacion: str,
        union_ids: list[str],
        union_details: list[dict]
    ) -> list[MetadataEvent]:
        """Build granular + batch events"""
```

### 2. Auto-Determination Logic

```python
class OccupationService:
    async def finalizar_spool(
        self,
        request: FinalizarRequest
    ) -> OccupationResponse:
        """
        Auto-determine PAUSAR vs COMPLETAR based on:
        - selected_count vs total_count comparison
        - Independent ARM/SOLD evaluation
        - Fresh data query at FINALIZAR time
        """

        # Get fresh totals from Uniones
        all_unions = self.union_repo.get_by_ot(ot)

        # Filter by operation type
        if operacion == "ARM":
            total_available = len(all_unions)
        else:  # SOLD
            # Only count SOLD-required types
            SOLD_REQUIRED = ['BW', 'BR', 'SO', 'FILL', 'LET']
            total_available = len([u for u in all_unions
                                  if u.tipo_union in SOLD_REQUIRED])

        # Determine action
        if len(selected_unions) == total_available:
            action = "COMPLETAR"
        else:
            action = "PAUSAR"
```

### 3. ARM-before-SOLD Validation

```python
async def iniciar_spool(self, request: IniciarRequest):
    """INICIAR with ARM prerequisite check for SOLD"""

    if request.operacion == "SOLD":
        # Query fresh data from Uniones
        unions = self.union_repo.get_by_ot(ot)

        # Check if ANY ARM union is completed
        arm_completed = any(u.arm_fecha_fin is not None
                           for u in unions)

        if not arm_completed:
            raise DependenciasNoSatisfechasError(
                tag_spool=tag_spool,
                operacion="SOLD",
                dependencia_faltante="ARM completion",
                detalle="Complete at least 1 ARM union first"
            )
```

### 4. Metrología Auto-Transition

```python
def should_trigger_metrologia(unions: list[Union]) -> bool:
    """Check if all work is complete"""

    # Separate union types
    fw_unions = [u for u in unions if u.tipo_union == 'FW']
    sold_required = [u for u in unions
                    if u.tipo_union in ['BW','BR','SO','FILL','LET']]

    # Check FW (ARM-only) completion
    fw_complete = all(u.arm_fecha_fin is not None
                     for u in fw_unions)

    # Check SOLD-required completion
    sold_complete = all(u.sol_fecha_fin is not None
                       for u in sold_required)

    return fw_complete and sold_complete
```

## Technical Constraints & Decisions

### 1. Performance Requirements

- **Batch Update Target**: < 1 second for 10 unions
- **Metadata Logging**: Use batch_log_events() for efficiency
- **No Caching**: Always query fresh data for consistency
- **Google Sheets Limits**: 60 writes/min, chunk at 900 rows

### 2. Error Handling Strategy

```python
# Partial success pattern (from UnionRepository)
try:
    updated_count = union_repo.batch_update_arm(...)
    if updated_count < len(union_ids):
        logger.warning(f"Partial update: {updated_count}/{len(union_ids)}")
except SheetsConnectionError:
    # Rollback Redis lock if critical
    raise
```

### 3. Version Conflict Resolution

Use ConflictService pattern:
- 3 retries with exponential backoff
- Version UUID on Uniones sheet
- Optimistic locking for concurrent updates

### 4. Event Types & Audit Trail

New event types for v4.0:
- UNION_ARM_REGISTRADA (granular union tracking)
- UNION_SOLD_REGISTRADA (granular union tracking)
- SPOOL_CANCELADO (0-union cancellation)
- METROLOGIA_AUTO_TRIGGERED (auto-transition)

## Integration Points

### 1. With Phase 8 (UnionRepository)

**Already Available:**
- batch_update_arm() and batch_update_sold()
- get_by_ot() for OT-based queries
- calculate_metrics() for efficient aggregation
- ARM validation in batch_update_sold()

**Service Layer Responsibilities:**
- Orchestrate batch operations
- Build metadata events
- Trigger state transitions
- Enforce business rules

### 2. With Phase 9 (Redis Locks)

**Lock Management:**
```python
# INICIAR creates lock
lock_token = await redis_lock_service.acquire_lock(tag_spool, worker_id)

# FINALIZAR releases lock
await redis_lock_service.release_lock(tag_spool, worker_id, lock_token)

# 0-union cancellation also releases
if len(union_ids) == 0:
    await redis_lock_service.release_lock(tag_spool, worker_id, lock_token)
    metadata_repo.log_event(evento_tipo="SPOOL_CANCELADO", ...)
```

### 3. With State Machines

**Service triggers transitions:**
```python
if action == "COMPLETAR":
    if operacion == "ARM":
        arm_machine.completar(fecha_operacion)
    else:
        sold_machine.completar(fecha_operacion)

    # Check metrología trigger
    if should_trigger_metrologia(all_unions):
        # Trigger state transition
        estado_detalle = "En Cola Metrología"
```

## Risk Mitigation

### 1. Race Conditions

**Risk**: Union becomes unavailable between page load and FINALIZAR

**Mitigation**:
```python
# Validate union availability at FINALIZAR time
available_unions = union_repo.get_disponibles_arm_by_ot(ot)
available_ids = [u.id for u in available_unions]

for selected_id in request.union_ids:
    if selected_id not in available_ids:
        raise VersionConflictError(
            "Union no longer available",
            data={"union_id": selected_id}
        )
```

### 2. Data Consistency

**Risk**: Partial batch update leaves inconsistent state

**Mitigation**:
- Log warnings for partial updates
- Continue with successful unions
- Metadata events track what succeeded

### 3. Performance Degradation

**Risk**: Large batches exceed 1-second target

**Mitigation**:
- Chunk at service layer if > 10 unions
- Use batch_update() single API call
- Monitor with performance logging

## Implementation Checklist

### UnionService Class
- [ ] Constructor with dependency injection
- [ ] process_selection() with batch orchestration
- [ ] calcular_pulgadas() with 2 decimal precision
- [ ] build_eventos_metadata() for audit trail

### OccupationService Enhancements
- [ ] iniciar_spool() - occupation without touching Uniones
- [ ] finalizar_spool() - auto-determination logic
- [ ] ARM validation for SOLD operations
- [ ] 0-union cancellation support

### ValidationService Updates
- [ ] ARM-before-SOLD prerequisite check
- [ ] Union availability validation
- [ ] OT-based validation (two-step)

### Integration Requirements
- [ ] State machine transition triggers
- [ ] Metadata batch logging
- [ ] Redis lock coordination
- [ ] SSE event publishing

## Testing Strategy

### Unit Tests
- Mock UnionRepository responses
- Test auto-determination logic
- Validate ARM-before-SOLD rules
- Test metrología trigger conditions

### Integration Tests
- End-to-end union selection flow
- Batch update performance (<1s)
- Race condition handling
- Partial success scenarios

### Performance Tests
- 10-union batch in <1 second
- 50-union stress test
- Concurrent FINALIZAR operations

## Key Decisions for Planning

1. **Service Separation**: Keep UnionService separate from OccupationService for clear responsibilities
2. **Error Strategy**: Use partial success pattern - update what's possible, log warnings
3. **Performance**: Always use batch operations, never loop individual updates
4. **Validation**: Validate at service layer, not repository layer
5. **Event Logging**: Build all events first, then batch_log_events() in single call
6. **State Transitions**: Service triggers transitions, state machine handles updates
7. **Constants**: Hardcode SOLD_REQUIRED_TYPES in service layer for performance

## Next Steps for Planning

1. Design detailed service interfaces
2. Map error scenarios to exceptions
3. Define request/response models
4. Plan state machine integration points
5. Create performance monitoring strategy
6. Design rollback procedures for failures

---

*Research completed: 2026-02-02*
*Ready for PLAN phase*