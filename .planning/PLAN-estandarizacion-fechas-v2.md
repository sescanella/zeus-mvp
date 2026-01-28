# Plan de Estandarización de Fechas - ZEUES v2.1 (v2)

**Objetivo:** Estandarizar todos los formatos de fecha/hora del sistema a:
- **Business dates:** DD-MM-YYYY (e.g., `21-01-2026`)
- **Audit timestamps:** DD-MM-YYYY HH:MM:SS (e.g., `21-01-2026 14:30:00`)
- **Timezone:** America/Santiago (Chile)

**Fecha:** 2026-01-28
**Tiempo estimado:** 4-5 horas (no 2-3h) - incluye análisis, testing y validación
**Archivos afectados:** 15+ archivos (10 backend + 3 frontend + 2+ scripts)

---

## ⚠️ BREAKING CHANGES

**Este plan introduce un BREAKING CHANGE en el contrato de API:**

| Campo | Formato ANTES | Formato DESPUÉS | Impacto |
|-------|---------------|-----------------|---------|
| `fecha_operacion` | YYYY-MM-DD (`2026-01-28`) | DD-MM-YYYY (`28-01-2026`) | 🔴 CRÍTICO - Frontend/Backend deben deployarse juntos |
| `timestamp` (Metadata) | ISO 8601 + Z (`2025-12-10T14:30:00Z`) | DD-MM-YYYY HH:MM:SS (`10-12-2025 14:30:00`) | 🔴 CRÍTICO - Logs/eventos cambian formato |
| `Fecha_Armado` (Sheets) | DD-MM-YYYY (ya correcto) | DD-MM-YYYY (sin cambio) | ✅ Sin impacto |
| `Fecha_Ocupacion` (Sheets) | YYYY-MM-DD (`2026-01-28`) | DD-MM-YYYY (`28-01-2026`) | 🟡 MEDIA - Afecta v3.0 |

**Estrategia de Deploy:**
1. ✅ Backend PRIMERO (acepta ambos formatos temporalmente vía parser)
2. ✅ Frontend DESPUÉS (envía solo DD-MM-YYYY)
3. ⚠️ NO deployar frontend solo sin backend actualizado

---

## 📊 Ejemplos Visuales - ANTES vs DESPUÉS

### Google Sheets - Hoja Operaciones

| Columna | ANTES | DESPUÉS | Notas |
|---------|-------|---------|-------|
| Fecha_Materiales (AJ) | `20-01-2026` | `20-01-2026` | ✅ Ya correcto |
| Fecha_Armado (AK) | `21-01-2026` | `21-01-2026` | ✅ Ya correcto (action_service) |
| Fecha_Soldadura (AM) | `22-01-2026` | `22-01-2026` | ✅ Ya correcto (action_service) |
| Fecha_Ocupacion (65) | `2026-01-28` | `28-01-2026` | 🔴 CAMBIA (occupation_service) |

### Google Sheets - Hoja Metadata

| Columna | ANTES | DESPUÉS | Notas |
|---------|-------|---------|-------|
| B: timestamp | `2025-12-10T14:30:00Z` | `10-12-2025 14:30:00` | 🔴 CAMBIA |
| I: fecha_operacion | `2025-12-10` | `10-12-2025` | 🔴 CAMBIA |

### API Request/Response

```json
// ANTES:
{
  "tag_spool": "MK-1335-CW-25238-011",
  "worker_id": 93,
  "worker_nombre": "MR(93)",
  "fecha_operacion": "2026-01-28"  // ISO format
}

// DESPUÉS:
{
  "tag_spool": "MK-1335-CW-25238-011",
  "worker_id": 93,
  "worker_nombre": "MR(93)",
  "fecha_operacion": "28-01-2026"  // DD-MM-YYYY
}
```

---

## FASE 0: Pre-análisis y Validación de Pre-requisitos

**Prioridad:** 🔴 CRÍTICA
**Tiempo estimado:** 30 minutos
**Objetivo:** Identificar todas las dependencias y validar que el sistema está listo

### Tarea 0.1: Buscar todas las referencias a formatos de fecha

**Comandos:**
```bash
cd /Users/sescanella/Proyectos/KM/ZEUES-by-KM

# Buscar .isoformat() en backend
grep -rn "\.isoformat()" backend/ --include="*.py" | grep -v __pycache__ > .planning/audit-isoformat.txt

# Buscar datetime.utcnow()
grep -rn "datetime\.utcnow" backend/ --include="*.py" | grep -v __pycache__ > .planning/audit-utcnow.txt

# Buscar datetime.now()
grep -rn "datetime\.now\(\)" backend/ --include="*.py" | grep -v __pycache__ > .planning/audit-now.txt

# Buscar .toISOString() en frontend
grep -rn "toISOString\|toLocaleDateString" zeues-frontend/ --include="*.ts" --include="*.tsx" > .planning/audit-frontend-dates.txt

# Ver resultados
wc -l .planning/audit-*.txt
```

**Validar:**
- ✅ Identificar TODOS los archivos que usan formatos de fecha
- ✅ Verificar si hay archivos no contemplados en el plan
- ✅ Revisar scripts de migration/backup

---

### Tarea 0.2: Verificar pre-requisitos

**Comandos:**
```bash
# Verificar pytz instalado
source venv/bin/activate
python -c "import pytz; print(pytz.timezone('America/Santiago'))"

# Verificar date_formatter.py accesible
python -c "from backend.utils.date_formatter import now_chile, today_chile, format_date_for_sheets, format_datetime_for_sheets; print('OK')"

# Verificar config.TIMEZONE
python -c "from backend.config import config; print(config.TIMEZONE)"

# Verificar parse_date() soporta DD-MM-YYYY
python -c "from backend.services.sheets_service import SheetsService; print(SheetsService.parse_date('28-01-2026'))"
```

**Validar:**
- ✅ pytz instalado y funcional
- ✅ date_formatter.py importable desde todos los servicios
- ✅ config.TIMEZONE = 'America/Santiago'
- ✅ parse_date() retorna date(2026, 1, 28) para '28-01-2026'

---

### Tarea 0.3: Revisar scripts de migration y backup

**Archivos a revisar:**
```bash
# Listar scripts con uso de fechas
grep -l "isoformat\|datetime\|date\." backend/scripts/*.py

# Archivos probables:
# - backend/scripts/add_v3_columns.py
# - backend/scripts/rollback_migration.py
# - backend/scripts/migration_coordinator.py
# - backend/scripts/backup_sheet.py
```

**Validar:**
- ✅ Scripts de backup usan timestamp consistente
- ✅ Scripts de migration no hardcodean formato YYYY-MM-DD
- ⚠️ Si scripts usan .isoformat(), añadirlos a la lista de archivos a modificar

---

### ✅ CHECKPOINT 0: Pre-análisis completo

**Antes de continuar:**
- [ ] Archivo `.planning/audit-*.txt` creados y revisados
- [ ] Pre-requisitos verificados (pytz, date_formatter, config)
- [ ] Scripts de migration revisados
- [ ] Lista completa de archivos a modificar documentada

---

## FASE 1: Backend - Models (CRÍTICO)

**Prioridad:** 🔴 CRÍTICA
**Tiempo estimado:** 30 minutos
**Objetivo:** Cambiar formato por defecto en modelos base

### Tarea 1.1: backend/models/metadata.py

**Cambios:**
1. Añadir import (línea ~10):
   ```python
   from backend.utils.date_formatter import now_chile, format_datetime_for_sheets
   ```

2. Línea 47 - Cambiar default_factory:
   ```python
   # ANTES:
   default_factory=datetime.utcnow,

   # DESPUÉS:
   default_factory=now_chile,
   ```

3. Línea 48 - Actualizar descripción:
   ```python
   # ANTES:
   description="Timestamp UTC del evento (ISO 8601)",

   # DESPUÉS:
   description="Timestamp del evento en timezone Santiago (DD-MM-YYYY HH:MM:SS)",
   ```

4. Línea 49 - Actualizar ejemplo:
   ```python
   # ANTES:
   examples=["2025-12-10T14:30:00Z"]

   # DESPUÉS:
   examples=["10-12-2025 14:30:00"]
   ```

5. Línea 110 - Actualizar ejemplo en model_config:
   ```python
   # ANTES:
   "timestamp": "2025-12-10T14:30:00Z",

   # DESPUÉS:
   "timestamp": "10-12-2025 14:30:00",
   ```

6. Línea 125 - Cambiar serialización en to_sheets_row():
   ```python
   # ANTES:
   self.timestamp.isoformat() + "Z",  # ISO 8601 con Z

   # DESPUÉS:
   format_datetime_for_sheets(self.timestamp),
   ```

7. Línea 149 - Actualizar from_sheets_row() para parsear nuevo formato:
   ```python
   # ANTES:
   timestamp=datetime.fromisoformat(row[1].replace("Z", "+00:00")),

   # DESPUÉS:
   timestamp=datetime.strptime(row[1], "%d-%m-%Y %H:%M:%S").replace(tzinfo=pytz.timezone('America/Santiago')),
   ```
   ⚠️ **IMPORTANTE:** También debe soportar formato antiguo para backward compatibility:
   ```python
   # Mejor implementación:
   try:
       # Intentar formato nuevo DD-MM-YYYY HH:MM:SS
       timestamp=datetime.strptime(row[1], "%d-%m-%Y %H:%M:%S").replace(tzinfo=pytz.timezone('America/Santiago'))
   except ValueError:
       # Fallback a formato antiguo ISO 8601
       timestamp=datetime.fromisoformat(row[1].replace("Z", "+00:00"))
   ```

**Impacto:** Todos los eventos de Metadata nuevos usarán formato DD-MM-YYYY HH:MM:SS.

---

### Tarea 1.2: backend/models/action.py

**Cambios:**
1. Añadir import (línea ~5):
   ```python
   from backend.utils.date_formatter import now_chile
   ```

2. Líneas 43 y 170 - Cambiar default en field_validator:
   ```python
   # ANTES:
   return v or datetime.now()

   # DESPUÉS:
   return v or now_chile()
   ```

**Impacto:** Models de request/response usarán timezone Santiago por defecto.

---

### ✅ CHECKPOINT 1: Models actualizados

**Comandos de validación:**
```bash
source venv/bin/activate

# Test específico de metadata model
pytest tests/unit/ -k metadata -v --tb=short

# Test específico de action model
pytest tests/unit/ -k action -v --tb=short

# Verificar imports
python -c "from backend.models.metadata import MetadataEvent; from backend.models.action import IniciarAccionRequest; print('OK')"
```

**Antes de continuar:**
- [ ] Tests de models pasan
- [ ] Imports funcionan correctamente
- [ ] No hay errores de sintaxis

**Si hay errores:** DETENER y revertir cambios antes de continuar.

---

## FASE 2: Backend - Services (ALTA PRIORIDAD)

**Prioridad:** 🟡 ALTA
**Tiempo estimado:** 45 minutos
**Objetivo:** Actualizar servicios que crean eventos de Metadata

### Tarea 2.1: backend/services/metrologia_service.py

**Cambios:**
1. Añadir import (línea ~10):
   ```python
   from backend.utils.date_formatter import format_datetime_for_sheets, format_date_for_sheets, now_chile
   ```

2. Línea 135 - Cambiar timestamp:
   ```python
   # ANTES:
   "timestamp": datetime.utcnow().isoformat() + "Z",

   # DESPUÉS:
   "timestamp": format_datetime_for_sheets(now_chile()),
   ```

3. Líneas 142, 183 - Cambiar fecha_operacion (2 ocurrencias):
   ```python
   # ANTES:
   "fecha_operacion": fecha_operacion.isoformat(),

   # DESPUÉS:
   "fecha_operacion": format_date_for_sheets(fecha_operacion),
   ```

---

### Tarea 2.2: backend/services/reparacion_service.py

**Cambios:**
1. Añadir import:
   ```python
   from backend.utils.date_formatter import format_datetime_for_sheets, format_date_for_sheets, now_chile, today_chile
   ```

2. Líneas 142, 256, 369, 476 - Cambiar timestamp (4 ocurrencias):
   ```python
   # ANTES:
   "timestamp": datetime.utcnow().isoformat() + "Z",

   # DESPUÉS:
   "timestamp": format_datetime_for_sheets(now_chile()),
   ```

3. Líneas 149, 263, 376, 483 - Cambiar fecha_operacion (4 ocurrencias):
   ```python
   # ANTES:
   "fecha_operacion": date.today().isoformat(),

   # DESPUÉS:
   "fecha_operacion": format_date_for_sheets(today_chile()),
   ```

---

### Tarea 2.3: backend/services/estado_detalle_service.py

**Cambios:**
1. Añadir import:
   ```python
   from backend.utils.date_formatter import format_datetime_for_sheets, format_date_for_sheets, now_chile, today_chile
   ```

2. Líneas 123, 129 - Cambiar timestamp (2 ocurrencias):
   ```python
   # ANTES:
   "timestamp": datetime.utcnow().isoformat() + "Z",

   # DESPUÉS:
   "timestamp": format_datetime_for_sheets(now_chile()),
   ```

3. Línea 136 - Cambiar fecha_operacion:
   ```python
   # ANTES:
   "fecha_operacion": datetime.utcnow().date().isoformat(),

   # DESPUÉS:
   "fecha_operacion": format_date_for_sheets(today_chile()),
   ```

---

### Tarea 2.4: backend/services/occupation_service.py

**Prioridad:** 🔴 CRÍTICA (escribe directamente a Google Sheets columna 65)

**Cambios:**
1. Añadir import:
   ```python
   from backend.utils.date_formatter import format_date_for_sheets, today_chile
   ```

2. Línea 152 - Cambiar fecha_ocupacion:
   ```python
   # ANTES:
   fecha_ocupacion_str = date.today().isoformat()

   # DESPUÉS:
   fecha_ocupacion_str = format_date_for_sheets(today_chile())
   ```

3. Línea 468 - Cambiar fecha_operacion:
   ```python
   # ANTES:
   fecha_str = fecha_operacion.isoformat()

   # DESPUÉS:
   fecha_str = format_date_for_sheets(fecha_operacion)
   ```

---

### Tarea 2.5: backend/services/redis_event_service.py

**Cambios:**
1. Añadir import:
   ```python
   from backend.utils.date_formatter import format_datetime_for_sheets, now_chile
   ```

2. Línea 92 - Cambiar timestamp:
   ```python
   # ANTES:
   "timestamp": datetime.utcnow().isoformat() + "Z"

   # DESPUÉS:
   "timestamp": format_datetime_for_sheets(now_chile())
   ```

---

### ✅ CHECKPOINT 2: Services actualizados

**Comandos de validación:**
```bash
source venv/bin/activate

# Tests de servicios específicos
pytest tests/unit/test_metrologia_service.py -v --tb=short
pytest tests/unit/test_occupation_service.py -v --tb=short

# Todos los tests de servicios
pytest tests/unit/ -k service -v --tb=short
```

**Antes de continuar:**
- [ ] Tests de services pasan
- [ ] No hay errores de import
- [ ] Lógica de negocio intacta

---

## FASE 3: Backend - Repositories

**Prioridad:** 🟡 ALTA
**Tiempo estimado:** 15 minutos

### Tarea 3.1: backend/repositories/metadata_repository.py

**Cambios:**
1. Añadir import:
   ```python
   from backend.utils.date_formatter import now_chile
   ```

2. Línea 373 - Cambiar timestamp:
   ```python
   # ANTES:
   timestamp=datetime.now(),

   # DESPUÉS:
   timestamp=now_chile(),
   ```

---

### ✅ CHECKPOINT 3: Backend completo

**Comandos de validación:**
```bash
source venv/bin/activate

# Ejecutar TODOS los tests unitarios de backend
pytest tests/unit/ -v --tb=short

# Verificar coverage en date_formatter
pytest tests/unit/ --cov=backend.utils.date_formatter --cov-report=term-missing
```

**Antes de continuar:**
- [ ] TODOS los tests unitarios pasan
- [ ] No hay warnings de imports
- [ ] Coverage de date_formatter > 80%

**🔴 PUNTO DE NO RETORNO:** Si todos los tests pasan, hacer commit:
```bash
git add backend/
git commit -m "feat: estandarizar formatos de fecha a DD-MM-YYYY con timezone Santiago

- Models: metadata.py, action.py usan now_chile()
- Services: metrologia, reparacion, estado_detalle, occupation, redis_event
- Repositories: metadata_repository.py
- Formato business: DD-MM-YYYY
- Formato timestamps: DD-MM-YYYY HH:MM:SS
- Timezone: America/Santiago

BREAKING CHANGE: fecha_operacion ahora usa DD-MM-YYYY en vez de YYYY-MM-DD
"
```

---

## FASE 4: Frontend

**Prioridad:** 🔴 CRÍTICA (debe sincronizarse con backend)
**Tiempo estimado:** 30 minutos

### Tarea 4.1: zeues-frontend/app/confirmar/page.tsx

**Cambios:**
1. Añadir función helper (después de imports, línea ~10):
   ```typescript
   /**
    * Formatea una fecha en formato DD-MM-YYYY para el backend.
    *
    * @param date - Date object a formatear
    * @returns String en formato DD-MM-YYYY (e.g., "28-01-2026")
    *
    * @example
    * formatDateDDMMYYYY(new Date(2026, 0, 28)) // "28-01-2026"
    */
   const formatDateDDMMYYYY = (date: Date): string => {
     const day = String(date.getDate()).padStart(2, '0');
     const month = String(date.getMonth() + 1).padStart(2, '0');
     const year = date.getFullYear();
     return `${day}-${month}-${year}`;
   };
   ```

2. Línea 67 - Cambiar fecha_operacion en handleConfirm:
   ```typescript
   // ANTES:
   const fecha_operacion = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format

   // DESPUÉS:
   const fecha_operacion = formatDateDDMMYYYY(new Date()); // DD-MM-YYYY format
   ```

3. Línea 154 - Cambiar fecha_operacion en completarOcupacion:
   ```typescript
   // ANTES:
   fecha_operacion: new Date().toISOString().split('T')[0], // YYYY-MM-DD format

   // DESPUÉS:
   fecha_operacion: formatDateDDMMYYYY(new Date()), // DD-MM-YYYY format
   ```

---

### Tarea 4.2: zeues-frontend/lib/types.ts (documentación)

**Cambios:**
1. Línea 130 - Actualizar comentario:
   ```typescript
   // ANTES:
   fecha_operacion: string;  // REQUIRED - Format: "YYYY-MM-DD" (e.g., "2026-01-28")

   // DESPUÉS:
   fecha_operacion: string;  // REQUIRED - Format: "DD-MM-YYYY" (e.g., "28-01-2026")
   ```

---

### Tarea 4.3: zeues-frontend/lib/api.ts (documentación)

**Cambios:**
1. Línea 1020 - Actualizar comentario:
   ```typescript
   // ANTES:
   * - fecha_operacion is REQUIRED (YYYY-MM-DD format)

   # DESPUÉS:
   * - fecha_operacion is REQUIRED (DD-MM-YYYY format)
   ```

2. Línea 1036 - Actualizar ejemplo:
   ```typescript
   // ANTES:
   *   fecha_operacion: '2026-01-28'  // YYYY-MM-DD format

   // DESPUÉS:
   *   fecha_operacion: '28-01-2026'  // DD-MM-YYYY format
   ```

---

### ✅ CHECKPOINT 4: Frontend actualizado

**Comandos de validación:**
```bash
cd zeues-frontend

# TypeScript compilation
npx tsc --noEmit

# ESLint
npm run lint

# Build production
npm run build
```

**Antes de continuar:**
- [ ] TypeScript compila sin errores
- [ ] ESLint pasa sin warnings
- [ ] Build production exitoso

**Commit frontend:**
```bash
git add zeues-frontend/
git commit -m "feat: actualizar frontend para enviar fecha_operacion en formato DD-MM-YYYY

- Añadir función formatDateDDMMYYYY() en confirmar/page.tsx
- Actualizar documentación en types.ts y api.ts
- Sincronizar con backend que espera DD-MM-YYYY

BREAKING CHANGE: fecha_operacion ahora se envía en DD-MM-YYYY
"
```

---

## FASE 5: Testing Exhaustivo

**Prioridad:** 🔴 CRÍTICA
**Tiempo estimado:** 1-2 horas
**Objetivo:** Validar que TODA la funcionalidad sigue funcionando

### Tarea 5.1: Crear tests específicos de formato de fechas

**Archivo nuevo:** `tests/unit/test_date_formatting.py`

```python
"""
Tests específicos para validar estandarización de formatos de fecha.
"""
import pytest
from datetime import date, datetime
import pytz
from backend.utils.date_formatter import (
    now_chile,
    today_chile,
    format_date_for_sheets,
    format_datetime_for_sheets,
    get_timezone
)
from backend.models.metadata import MetadataEvent, EventoTipo, Accion


class TestDateFormatter:
    """Tests para funciones de date_formatter.py"""

    def test_timezone_is_santiago(self):
        """Verificar que timezone es America/Santiago"""
        tz = get_timezone()
        assert tz.zone == 'America/Santiago'

    def test_now_chile_returns_santiago_timezone(self):
        """now_chile() debe retornar datetime con timezone Santiago"""
        dt = now_chile()
        assert dt.tzinfo is not None
        assert dt.tzinfo.zone == 'America/Santiago'

    def test_today_chile_returns_date(self):
        """today_chile() debe retornar date object (sin hora)"""
        d = today_chile()
        assert isinstance(d, date)
        assert not isinstance(d, datetime)

    def test_format_date_for_sheets_dd_mm_yyyy(self):
        """format_date_for_sheets() debe retornar DD-MM-YYYY"""
        d = date(2026, 1, 28)
        result = format_date_for_sheets(d)
        assert result == "28-01-2026"

    def test_format_datetime_for_sheets_dd_mm_yyyy_hh_mm_ss(self):
        """format_datetime_for_sheets() debe retornar DD-MM-YYYY HH:MM:SS"""
        dt = datetime(2026, 1, 28, 14, 30, 45)
        result = format_datetime_for_sheets(dt)
        assert result == "28-01-2026 14:30:45"


class TestMetadataEventFormatting:
    """Tests para MetadataEvent con nuevos formatos"""

    def test_metadata_event_timestamp_uses_santiago_timezone(self):
        """MetadataEvent debe usar timezone Santiago por defecto"""
        event = MetadataEvent(
            evento_tipo=EventoTipo.INICIAR_ARM,
            tag_spool="TEST-001",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM",
            accion=Accion.INICIAR,
            fecha_operacion="28-01-2026"
        )
        assert event.timestamp.tzinfo.zone == 'America/Santiago'

    def test_to_sheets_row_formats_timestamp_dd_mm_yyyy(self):
        """to_sheets_row() debe formatear timestamp como DD-MM-YYYY HH:MM:SS"""
        tz = pytz.timezone('America/Santiago')
        dt = datetime(2026, 1, 28, 14, 30, 0, tzinfo=tz)

        event = MetadataEvent(
            timestamp=dt,
            evento_tipo=EventoTipo.COMPLETAR_ARM,
            tag_spool="TEST-002",
            worker_id=94,
            worker_nombre="CP(94)",
            operacion="ARM",
            accion=Accion.COMPLETAR,
            fecha_operacion="28-01-2026"
        )

        row = event.to_sheets_row()
        # row[1] es el timestamp
        assert row[1] == "28-01-2026 14:30:00"

    def test_to_sheets_row_keeps_fecha_operacion_dd_mm_yyyy(self):
        """to_sheets_row() debe mantener fecha_operacion en DD-MM-YYYY"""
        event = MetadataEvent(
            evento_tipo=EventoTipo.INICIAR_SOLD,
            tag_spool="TEST-003",
            worker_id=95,
            worker_nombre="JP(95)",
            operacion="SOLD",
            accion=Accion.INICIAR,
            fecha_operacion="28-01-2026"
        )

        row = event.to_sheets_row()
        # row[8] es fecha_operacion
        assert row[8] == "28-01-2026"


class TestBackwardCompatibilityParsing:
    """Tests para validar que seguimos leyendo formatos antiguos"""

    def test_from_sheets_row_parses_new_format(self):
        """from_sheets_row() debe parsear nuevo formato DD-MM-YYYY HH:MM:SS"""
        row = [
            "uuid-123",
            "28-01-2026 14:30:00",  # Nuevo formato
            "COMPLETAR_ARM",
            "TEST-004",
            "93",
            "MR(93)",
            "ARM",
            "COMPLETAR",
            "28-01-2026",
            ""
        ]

        event = MetadataEvent.from_sheets_row(row)
        assert event.timestamp.year == 2026
        assert event.timestamp.month == 1
        assert event.timestamp.day == 28
        assert event.timestamp.hour == 14
        assert event.timestamp.minute == 30

    def test_from_sheets_row_parses_old_iso_format(self):
        """from_sheets_row() debe TAMBIÉN parsear formato antiguo ISO 8601"""
        row = [
            "uuid-456",
            "2025-12-10T14:30:00Z",  # Formato antiguo
            "INICIAR_ARM",
            "TEST-005",
            "94",
            "CP(94)",
            "ARM",
            "INICIAR",
            "10-12-2025",
            ""
        ]

        event = MetadataEvent.from_sheets_row(row)
        assert event.timestamp.year == 2025
        assert event.timestamp.month == 12
        assert event.timestamp.day == 10


class TestRoundTripFormatting:
    """Tests de round-trip: write → read → write"""

    def test_round_trip_metadata_event(self):
        """Escribir y leer MetadataEvent debe preservar formato"""
        # Create event
        original = MetadataEvent(
            evento_tipo=EventoTipo.COMPLETAR_SOLD,
            tag_spool="TEST-ROUNDTRIP",
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="SOLD",
            accion=Accion.COMPLETAR,
            fecha_operacion="28-01-2026"
        )

        # to_sheets_row
        row = original.to_sheets_row()

        # from_sheets_row
        parsed = MetadataEvent.from_sheets_row(row)

        # Verify
        assert parsed.fecha_operacion == "28-01-2026"
        assert row[1].count(':') == 2  # DD-MM-YYYY HH:MM:SS tiene 2 ":"
        assert row[1].count('-') == 4  # DD-MM-YYYY HH:MM:SS tiene 4 "-"
```

**Ejecutar:**
```bash
pytest tests/unit/test_date_formatting.py -v --tb=short
```

**Validar:**
- [ ] Todos los tests pasan
- [ ] Round-trip funciona correctamente
- [ ] Backward compatibility validada

---

### Tarea 5.2: Ejecutar tests unitarios completos

**Comandos:**
```bash
source venv/bin/activate

# Ejecutar TODOS los tests unitarios
pytest tests/unit/ -v --tb=short

# Si hay fallos en tests específicos:
pytest tests/unit/test_action_service.py -v --tb=line
pytest tests/unit/test_metadata.py -v --tb=line
pytest tests/unit/test_sheets_service.py -v --tb=line

# Coverage completo
pytest tests/unit/ --cov=backend --cov-report=html
# Ver reporte en htmlcov/index.html
```

**Validar:**
- [ ] TODOS los tests unitarios pasan (>200 tests)
- [ ] Coverage > 80% en módulos modificados
- [ ] No hay warnings de deprecation

---

### Tarea 5.3: Tests de integración E2E

**Comandos:**
```bash
# Tests de integración completos
pytest tests/integration/ -v --tb=short

# Test específico de flujo COMPLETAR
pytest tests/integration/test_metrologia_flow.py -v
```

**Validar:**
- [ ] Tests E2E pasan
- [ ] Flujos completos funcionan end-to-end

---

### Tarea 5.4: Validación manual en Google Sheets (CRÍTICA)

**Objetivo:** Verificar que los datos se escriben correctamente en Google Sheets con formato DD-MM-YYYY

**Pasos:**
1. **Levantar backend local:**
   ```bash
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   ```

2. **Levantar frontend local:**
   ```bash
   cd zeues-frontend
   npm run dev
   # Frontend en http://localhost:3000
   ```

3. **Ejecutar flujo COMPLETAR ARM:**
   - Abrir http://localhost:3000
   - Seleccionar operación: ARM
   - Seleccionar worker: Mauricio Rodriguez (MR(93))
   - Seleccionar acción: COMPLETAR
   - Seleccionar spool en progreso (armador=MR(93), fecha_armado=vacía)
   - CONFIRMAR

4. **Verificar en Google Sheets (Hoja Operaciones):**
   - Buscar el spool modificado
   - ✅ Columna AK (Fecha_Armado) debe tener formato: `28-01-2026`
   - ✅ Verificar que Google Sheets lo interpreta como FECHA (no texto)
   - ✅ Ordenar por columna AK - debe ordenar cronológicamente

5. **Verificar en Google Sheets (Hoja Metadata):**
   - Ir a última fila de Metadata
   - ✅ Columna B (timestamp) debe tener formato: `28-01-2026 14:30:00`
   - ✅ Columna I (fecha_operacion) debe tener formato: `28-01-2026`
   - ✅ Verificar que Google Sheets interpreta como FECHA/DATETIME

6. **Ejecutar flujo TOMAR (v3.0):**
   - Seleccionar operación: ARM
   - Seleccionar worker: Nicolás Rodriguez
   - Seleccionar acción: TOMAR
   - Seleccionar spool PENDIENTE
   - CONFIRMAR

7. **Verificar Fecha_Ocupacion:**
   - ✅ Columna 65 (Fecha_Ocupacion) debe tener formato: `28-01-2026`

**Checklist de validación:**
- [ ] Fecha_Armado en DD-MM-YYYY (e.g., `28-01-2026`)
- [ ] Metadata timestamp en DD-MM-YYYY HH:MM:SS (e.g., `28-01-2026 14:30:00`)
- [ ] Metadata fecha_operacion en DD-MM-YYYY (e.g., `28-01-2026`)
- [ ] Fecha_Ocupacion en DD-MM-YYYY (e.g., `28-01-2026`)
- [ ] Google Sheets interpreta como FECHA (no texto)
- [ ] Ordenamiento cronológico funciona correctamente

---

### Tarea 5.5: Frontend E2E Tests (Playwright)

**Comandos:**
```bash
cd zeues-frontend

# Ejecutar tests E2E completos
npx playwright test

# Test específico con UI
npx playwright test --ui

# Slow motion para debugging
SLOW_MO=2000 npx playwright test --headed --workers=1

# Generar reporte
npx playwright show-report
```

**Validar:**
- [ ] Tests de Playwright pasan
- [ ] Flujo completo funciona en navegador real
- [ ] No hay errores de red (400/500)

---

### ✅ CHECKPOINT 5: Testing completo

**Antes de finalizar:**
- [ ] Tests unitarios: 100% pasan
- [ ] Tests integración: 100% pasan
- [ ] Tests E2E: 100% pasan
- [ ] Validación manual en Sheets: ✅
- [ ] Formato DD-MM-YYYY verificado visualmente
- [ ] Backward compatibility validada

---

## FASE 6: Opcional - Health Endpoints

**Prioridad:** 🟢 BAJA (endpoints de diagnóstico)
**Tiempo estimado:** 10 minutos

### Decisión: ¿Cambiar health endpoints a Santiago timezone?

**Opción A: Mantener UTC (RECOMENDADO)**
- ✅ Consistencia con logs de infraestructura (Railway, Vercel)
- ✅ Estándar internacional para health checks
- ✅ No afecta lógica de negocio
- ❌ Inconsistente con resto del sistema

**Opción B: Cambiar a Santiago**
- ✅ Consistencia total en el sistema
- ❌ Health checks tradicionalmente usan UTC
- ❌ Puede confundir en debugging de infraestructura

**Recomendación:** Mantener UTC en health endpoints.

**Si decides cambiar:**
```python
# backend/routers/health.py
from backend.utils.date_formatter import format_datetime_for_sheets, now_chile

# Líneas 103, 128:
# ANTES:
"timestamp": datetime.utcnow().isoformat() + "Z",

# DESPUÉS:
"timestamp": format_datetime_for_sheets(now_chile()),
```

---

## Resumen Final de Cambios

| Fase | Archivos | Líneas | Tiempo | Prioridad |
|------|----------|--------|--------|-----------|
| FASE 0 - Pre-análisis | Auditoría | N/A | 30min | 🔴 CRÍTICA |
| FASE 1 - Models | 2 | 8 + 2 imports | 30min | 🔴 CRÍTICA |
| FASE 2 - Services | 5 | 19 + 5 imports | 45min | 🟡 ALTA |
| FASE 3 - Repositories | 1 | 1 + 1 import | 15min | 🟡 ALTA |
| FASE 4 - Frontend | 3 | 5 + 1 función | 30min | 🔴 CRÍTICA |
| FASE 5 - Testing | 1 nuevo + validación | ~150 tests | 1-2h | 🔴 CRÍTICA |
| FASE 6 - Health (opcional) | 1 | 2 + 1 import | 10min | 🟢 BAJA |
| **TOTAL** | **13+** | **35+** | **4-5h** | - |

---

## Rollback Plan Detallado

### Rollback por Fase

**Si falla FASE 1 (Models):**
```bash
git diff HEAD backend/models/
git checkout HEAD -- backend/models/metadata.py backend/models/action.py
```

**Si falla FASE 2 (Services):**
```bash
git checkout HEAD -- backend/services/metrologia_service.py
git checkout HEAD -- backend/services/reparacion_service.py
git checkout HEAD -- backend/services/estado_detalle_service.py
git checkout HEAD -- backend/services/occupation_service.py
git checkout HEAD -- backend/services/redis_event_service.py
```

**Si falla FASE 3 (Repositories):**
```bash
git checkout HEAD -- backend/repositories/metadata_repository.py
```

**Si falla FASE 4 (Frontend):**
```bash
git checkout HEAD -- zeues-frontend/app/confirmar/page.tsx
git checkout HEAD -- zeues-frontend/lib/types.ts
git checkout HEAD -- zeues-frontend/lib/api.ts
```

**Rollback completo (NUCLEAR):**
```bash
# Revertir todos los cambios
git reset --hard HEAD

# O revertir commit específico
git revert <commit-hash>
```

### Restaurar Google Sheets desde Backup

**Si los datos en Sheets se corrompen:**
```bash
# Listar backups disponibles
ls -lah /path/to/backups/

# Ejecutar script de restore (si existe)
python backend/scripts/restore_from_backup.py --backup-id=<timestamp>

# Manual: Descargar backup y restaurar manualmente en Google Sheets UI
```

---

## Validación de Backward Compatibility

**CRÍTICO:** El parser `parse_date()` debe soportar AMBOS formatos durante transición.

**Validación actual:**
```python
# backend/services/sheets_service.py línea 212-218
formats = [
    "%d-%m-%Y",     # 21-01-2026 (NUEVO - DD-MM-YYYY)
    "%d/%m/%Y",     # 30/7/2025 (legacy DD/MM/YYYY)
    "%d/%m/%y",     # 30/7/25 (legacy)
    "%Y-%m-%d",     # 2025-11-08 (ANTIGUO - ISO format)
    "%d-%b-%Y",     # 08-Nov-2025
]
```

**Test de validación:**
```python
def test_parse_date_backward_compatibility():
    """parse_date() debe aceptar formatos antiguos Y nuevos"""
    from backend.services.sheets_service import SheetsService

    # Nuevo formato
    assert SheetsService.parse_date("28-01-2026") == date(2026, 1, 28)

    # Formato antiguo ISO
    assert SheetsService.parse_date("2026-01-28") == date(2026, 1, 28)

    # Formato legacy
    assert SheetsService.parse_date("28/01/2026") == date(2026, 1, 28)
```

✅ **CONFIRMADO:** El parser ya soporta múltiples formatos, por lo que datos históricos seguirán siendo válidos.

---

## Notas Finales

### ✅ Lo que YA está correcto:

- `date_formatter.py` ya tiene todas las funciones necesarias
- `action_service.py` (ARM/SOLD) ya usa las funciones correctas
- `parse_date()` ya soporta DD-MM-YYYY como formato principal
- Timezone Santiago ya configurado en `config.py`

### ❌ Lo que necesita corrección:

- Models usan `datetime.utcnow()` en vez de `now_chile()`
- Servicios secundarios no importan utilidades de `date_formatter`
- Frontend envía YYYY-MM-DD en vez de DD-MM-YYYY
- Metadata serializa con `.isoformat()` en vez de `format_datetime_for_sheets()`

### ⚠️ Riesgos y Mitigaciones:

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Tests fallan después de cambios | Media | Alto | Checkpoints después de cada fase |
| Datos en Sheets se corrompen | Baja | Crítico | Backup automático + rollback plan |
| Breaking change rompe producción | Media | Crítico | Deploy sincronizado backend+frontend |
| Formato antiguo no se lee | Baja | Alto | Backward compatibility en parse_date() |

---

**Fin del Plan v2**

**Última actualización:** 2026-01-28
**Autor:** Claude Code
**Estado:** READY FOR EXECUTION
