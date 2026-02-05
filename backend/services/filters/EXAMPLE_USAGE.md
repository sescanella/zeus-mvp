# Sistema Unificado de Filtros - Ejemplos de Uso

## 📋 Arquitectura

```
backend/services/filters/
├── __init__.py           # Exports públicos
├── base.py               # SpoolFilter (abstract), FilterResult
├── common_filters.py     # Filtros reutilizables (Prerequisite, Ocupacion, Completion, etc.)
├── registry.py           # FilterRegistry - Configuración centralizada
└── EXAMPLE_USAGE.md      # Este archivo
```

---

## 🎯 Ventajas del Sistema

### 1. **Configuración Centralizada**
Todos los filtros se definen en un solo lugar: `registry.py`

### 2. **Extensible**
Agregar nuevos filtros es simple:
```python
class CustomFilter(SpoolFilter):
    def apply(self, spool: Spool) -> FilterResult:
        # Tu lógica aquí
        pass
```

### 3. **Reutilizable**
Los filtros comunes (Prerequisite, Ocupacion, etc.) se reutilizan con diferentes parámetros

### 4. **Profesional**
- Código limpio y mantenible
- Un solo lugar para modificar reglas de negocio
- Fácil debugging con FilterResult.reason

---

## 🔧 Ejemplo 1: Obtener Filtros por Operación y Acción

```python
from backend.services.filters import FilterRegistry

# ARM - INICIAR
filters_arm_iniciar = FilterRegistry.get_filters("ARM", "INICIAR")
print(len(filters_arm_iniciar))  # 4 filtros

# SOLD - FINALIZAR
filters_sold_finalizar = FilterRegistry.get_filters("SOLD", "FINALIZAR")
print(len(filters_sold_finalizar))  # 3 filtros

# METROLOGIA - INICIAR
filters_metrologia = FilterRegistry.get_filters("METROLOGIA", "INICIAR")
print(len(filters_metrologia))  # 3 filtros
```

---

## 🔧 Ejemplo 2: Aplicar Filtros a un Spool

```python
from backend.services.filters import FilterRegistry
from backend.models.spool import Spool

# Simular un spool
spool = Spool(
    tag_spool="TEST-01",
    fecha_materiales="2026-01-15",
    armador=None,
    ocupado_por=None,
    status_nv="ABIERTA",
    status_spool="EN_PROCESO"
)

# Obtener filtros para ARM - INICIAR
filters = FilterRegistry.get_filters("ARM", "INICIAR")

# Aplicar filtros uno por uno (con logging)
for filter_obj in filters:
    result = filter_obj.apply(spool)
    print(f"[{filter_obj.name}] {'✅ PASS' if result.passed else '❌ FAIL'}: {result.reason}")

# Resultado esperado:
# [Prerequisite_Materiales] ✅ PASS: Materiales completado (fecha_materiales=2026-01-15)
# [Ocupacion_Disponible] ✅ PASS: Spool disponible (ocupado_por=null)
# [StatusNV_ABIERTA] ✅ PASS: NV en estado correcto (STATUS_NV=ABIERTA)
# [StatusSpool_EN_PROCESO] ✅ PASS: Spool en estado correcto (Status_Spool=EN_PROCESO)
```

---

## 🔧 Ejemplo 3: Verificar si un Spool Pasa Todos los Filtros

```python
from backend.services.filters import FilterRegistry

# Spool elegible
spool_elegible = Spool(
    tag_spool="TEST-01",
    fecha_materiales="2026-01-15",
    ocupado_por=None,
    status_nv="ABIERTA",
    status_spool="EN_PROCESO"
)

filters = FilterRegistry.get_filters("ARM", "INICIAR")
passes = FilterRegistry.passes_all_filters(spool_elegible, filters)
print(passes)  # True

# Spool NO elegible (ocupado)
spool_ocupado = Spool(
    tag_spool="TEST-02",
    fecha_materiales="2026-01-15",
    ocupado_por="JD(45)",  # ❌ Ocupado por otro trabajador
    status_nv="ABIERTA",
    status_spool="EN_PROCESO"
)

passes = FilterRegistry.passes_all_filters(spool_ocupado, filters)
print(passes)  # False
```

---

## 🔧 Ejemplo 4: Filtrar Lista de Spools

```python
from backend.services.filters import FilterRegistry

all_spools = [spool1, spool2, spool3, ...]

filters = FilterRegistry.get_filters("ARM", "INICIAR")

# Filtrar spools elegibles
eligible_spools = [
    spool for spool in all_spools
    if FilterRegistry.passes_all_filters(spool, filters)
]

print(f"Spools elegibles: {len(eligible_spools)} / {len(all_spools)}")
```

---

## 🔧 Ejemplo 5: Obtener Descripción de Filtros (para API docs)

```python
from backend.services.filters import FilterRegistry

# Para documentación de API
description = FilterRegistry.get_filter_description("ARM", "INICIAR")
print(description)

# Output:
# ARM - INICIAR - Filtros aplicados:
# 1. Prerequisite_Materiales: Verifica que Materiales esté completado (campo fecha_materiales con dato)
# 2. Ocupacion_Disponible: Verifica que el spool NO esté ocupado (Ocupado_Por vacío o 'DISPONIBLE')
# 3. StatusNV_ABIERTA: Verifica que STATUS_NV sea 'ABIERTA'
# 4. StatusSpool_EN_PROCESO: Verifica que Status_Spool sea 'EN_PROCESO'
```

---

## 🛠️ Cómo Modificar Filtros

### Caso 1: Cambiar filtro de una operación existente

Editar `backend/services/filters/registry.py`:

```python
# Antes: ARM - INICIAR requiere StatusNV=ABIERTA
_ARM_INICIAR_FILTERS = [
    PrerequisiteFilter("fecha_materiales", "Materiales"),
    OcupacionFilter(),
    StatusNVFilter(required_status="ABIERTA"),  # ← Cambiar este filtro
    StatusSpoolFilter(required_status="EN_PROCESO")
]

# Después: ARM - INICIAR ya no requiere StatusNV=ABIERTA (remover filtro)
_ARM_INICIAR_FILTERS = [
    PrerequisiteFilter("fecha_materiales", "Materiales"),
    OcupacionFilter(),
    # StatusNVFilter(required_status="ABIERTA"),  ← Comentar o remover
    StatusSpoolFilter(required_status="EN_PROCESO")
]
```

### Caso 2: Agregar nuevo filtro custom

1. Crear filtro en `common_filters.py`:
```python
class CycleFilter(SpoolFilter):
    """Filtra spools por ciclo de reparación."""

    def __init__(self, max_cycle: int):
        self._max_cycle = max_cycle

    def apply(self, spool: Spool) -> FilterResult:
        # Tu lógica aquí
        pass

    @property
    def name(self) -> str:
        return f"Cycle_Max{self._max_cycle}"

    @property
    def description(self) -> str:
        return f"Verifica que ciclo de reparación sea <= {self._max_cycle}"
```

2. Usar en `registry.py`:
```python
_REPARACION_INICIAR_FILTERS = [
    OcupacionFilter(),
    CycleFilter(max_cycle=3),  # ← Nuevo filtro
]
```

---

## 📊 Comparación: Antes vs Después

### ❌ ANTES (código duplicado)

```python
def get_spools_arm(self):
    spools = []
    for spool in all_spools:
        if spool.fecha_materiales and not spool.ocupado_por:  # Lógica hardcoded
            spools.append(spool)
    return spools

def get_spools_sold(self):
    spools = []
    for spool in all_spools:
        if spool.fecha_armado and not spool.ocupado_por:  # Lógica duplicada
            spools.append(spool)
    return spools

def get_spools_metrologia(self):
    spools = []
    for spool in all_spools:
        if spool.fecha_soldadura and not spool.fecha_qc_metrologia:  # ❌ Falta filtro ocupación!
            spools.append(spool)
    return spools
```

### ✅ DESPUÉS (unificado, configurable)

```python
def get_spools_disponibles(self, operation: str, action: str):
    all_spools = self.sheets_repository.get_all_spools()
    filters = FilterRegistry.get_filters(operation, action)

    eligible_spools = [
        spool for spool in all_spools
        if FilterRegistry.passes_all_filters(spool, filters)
    ]

    return eligible_spools

# Uso:
get_spools_disponibles("ARM", "INICIAR")
get_spools_disponibles("SOLD", "INICIAR")
get_spools_disponibles("METROLOGIA", "INICIAR")  # ✅ Usa misma lógica
```

---

## 🎯 Próximos Pasos

1. ✅ Sistema de filtros implementado
2. ⏳ Refactorizar `SpoolServiceV2` para usar `FilterRegistry`
3. ⏳ Agregar tests unitarios para cada filtro
4. ⏳ Documentar reglas de negocio en `registry.py`
5. ⏳ Implementar filtros para REPARACION
