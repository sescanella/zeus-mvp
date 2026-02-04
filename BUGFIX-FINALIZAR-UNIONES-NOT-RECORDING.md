# BUG FIX: FINALIZAR no estaba registrando datos en hoja Uniones

**Fecha:** 2026-02-04
**Estado:** ✅ RESUELTO
**Severidad:** CRÍTICA
**Impacto:** Funcionalidad v4.0 FINALIZAR completamente bloqueada

---

## SÍNTOMAS

Cuando el usuario seleccionaba uniones en el frontend y presionaba "CONFIRMAR", la aplicación:

1. ✅ Navegaba exitosamente a la página de éxito (`/exito`)
2. ✅ Liberaba el lock de Redis correctamente
3. ✅ Limpiaba los campos `Ocupado_Por` y `Fecha_Ocupacion` en la hoja Operaciones
4. ❌ **NO escribía los timestamps ARM_FECHA_FIN/ARM_WORKER en la hoja Uniones**

El resultado era que las uniones aparecían como "disponibles" nuevamente, pero sin registro de haberlas completado.

---

## DIAGNÓSTICO

### ROOT CAUSE

**Problema de formato de ID en batch_update_arm() y batch_update_sold():**

1. **Hoja Uniones - Columna ID:** Formato secuencial numérico
   - Ejemplos: `"0011"`, `"0012"`, `"0013"`

2. **Backend - Union model:** Sintetiza IDs como `OT+N_UNION`
   - Ejemplos: `"001+1"`, `"001+2"`, `"001+3"`

3. **Frontend:** Recibe IDs del backend y los envía en request FINALIZAR
   - Payload: `{"selected_unions": ["001+1", "001+2", ...]}`

4. **batch_update_arm():** Comparaba el valor RAW de la columna ID con los IDs del request
   ```python
   # ❌ CÓDIGO INCORRECTO (antes del fix)
   row_id = row_data[id_col_idx]  # Lee "0011"
   if row_id in union_ids:         # Compara "0011" == "001+1" → FALSE
   ```

**Resultado:** `union_id_to_row` quedaba vacío → `batch_update()` nunca se ejecutaba → 0 actualizaciones.

### EVIDENCIA

```bash
$ python inspect_uniones_sheet.py

================================================================================
UNION ID SYNTHESIS VALIDATION
================================================================================

✅ Testing ID synthesis logic:
--------------------------------------------------------------------------------
Row   Sheet ID        OT+N_UNION      TAG_SPOOL            Match?
--------------------------------------------------------------------------------
2     0011            001+1           TEST-02              ❌ NO
3     0012            001+2           TEST-02              ❌ NO
4     0013            001+3           TEST-02              ❌ NO
...

⚠️ EXPECTED BEHAVIOR: Sheet ID column does NOT match OT+N_UNION format
   This is why we MUST synthesize IDs from OT+N_UNION columns.
```

---

## SOLUCIÓN

### Cambios en `backend/repositories/union_repository.py`

#### 1. batch_update_arm() (líneas 584-620)

**ANTES:**
```python
tag_spool_col_idx = column_map.get(normalize("TAG_SPOOL"))
id_col_idx = column_map.get(normalize("ID"))  # ❌ Usaba columna ID secuencial
arm_fecha_fin_col_idx = column_map.get(normalize("ARM_FECHA_FIN"))
arm_worker_col_idx = column_map.get(normalize("ARM_WORKER"))

...

row_id = row_data[id_col_idx]  # Lee "0011"
if row_id in union_ids:         # ❌ Nunca coincide con "001+1"
    union_id_to_row[row_id] = row_idx
```

**DESPUÉS:**
```python
tag_spool_col_idx = column_map.get(normalize("TAG_SPOOL"))
ot_col_idx = column_map.get(normalize("OT"))            # ✅ Nueva columna
n_union_col_idx = column_map.get(normalize("N_UNION"))  # ✅ Nueva columna
arm_fecha_fin_col_idx = column_map.get(normalize("ARM_FECHA_FIN"))
arm_worker_col_idx = column_map.get(normalize("ARM_WORKER"))

...

# CRITICAL FIX: Sintetizar ID desde OT+N_UNION
row_ot = row_data[ot_col_idx]
row_n_union = row_data[n_union_col_idx]
synthesized_union_id = f"{row_ot}+{row_n_union}"  # ✅ Genera "001+1"

if synthesized_union_id in union_ids:             # ✅ Ahora sí coincide
    union_id_to_row[synthesized_union_id] = row_idx
```

#### 2. batch_update_sold() (líneas 705-735)

Mismo fix aplicado con validación adicional de ARM completion.

#### 3. Test actualizado

`tests/unit/test_union_repository.py::test_uses_tag_spool_as_foreign_key`

```python
# ANTES
assert unions[0].id == "SPECIAL-001+1"  # ❌ Esperaba TAG_SPOOL+N_UNION

# DESPUÉS
assert unions[0].id == "SPECIAL+1"      # ✅ Correcto: OT+N_UNION
```

---

## VALIDACIÓN

### Tests Unitarios
```bash
$ ./venv/bin/pytest tests/unit/test_union_repository.py -v
========================== 15 passed, 1 warning in 0.23s ==========================
```

### Simulación con datos reales
```bash
$ python validate_union_id_logic.py

Frontend sends: ['001+1', '001+2', '001+3', '001+4', '001+5', '001+6']

✅ Found 6 unions for TAG_SPOOL=TEST-02:
   Row 2: ID=001+1 (OT=001, N_UNION=1)
   Row 3: ID=001+2 (OT=001, N_UNION=2)
   Row 4: ID=001+3 (OT=001, N_UNION=3)
   Row 5: ID=001+4 (OT=001, N_UNION=4)
   Row 6: ID=001+5 (OT=001, N_UNION=5)
   Row 7: ID=001+6 (OT=001, N_UNION=6)

✅ SUCCESS: batch_update_arm would update 6 rows!
```

---

## ARCHIVOS MODIFICADOS

1. `backend/repositories/union_repository.py`
   - `batch_update_arm()` - síntesis de ID desde OT+N_UNION
   - `batch_update_sold()` - síntesis de ID desde OT+N_UNION

2. `tests/unit/test_union_repository.py`
   - `test_uses_tag_spool_as_foreign_key()` - expectativa correcta de ID

3. Scripts de validación (nuevos):
   - `inspect_uniones_sheet.py` - inspeccionar formato de datos
   - `validate_union_id_logic.py` - simular lógica de batch_update

---

## NOTAS TÉCNICAS

### ¿Por qué OT+N_UNION y no TAG_SPOOL+N_UNION?

**Relación de datos:**
- **OT** (Order de Trabajo): Puede tener múltiples spools
  - Ejemplo: OT "001" → spools "TEST-02", "TEST-03", "TEST-04"

- **TAG_SPOOL**: Identificador único por spool
  - Ejemplo: "TEST-02" pertenece a OT "001"

- **Union ID**: Se compone de **OT+N_UNION** porque:
  1. Una union pertenece a una OT específica (no solo a un spool)
  2. Múltiples spools de la misma OT comparten las mismas uniones
  3. Es el formato estándar en la industria manufacturera

### Diagrama de flujo correcto

```
Frontend Request:
{
  "tag_spool": "TEST-02",
  "selected_unions": ["001+1", "001+2", "001+3"]
}
           ↓
batch_update_arm():
  - Lee hoja Uniones
  - Filtra por TAG_SPOOL = "TEST-02"
  - Para cada fila:
      • Lee OT = "001"
      • Lee N_UNION = 1, 2, 3, ...
      • Sintetiza ID = "001+1", "001+2", "001+3"
      • Compara con selected_unions → ✅ MATCH
  - Ejecuta batch_update() → ✅ ESCRIBE timestamps
```

---

## PRÓXIMOS PASOS

1. ✅ Deploy fix a Railway (backend)
2. ✅ Verificar funcionamiento en producción con TEST-02
3. ⏳ Monitorear logs de Railway para confirmar batch_update exitoso
4. ⏳ Comunicar fix al equipo de QA para retesting de flujo FINALIZAR

---

**FIN DEL REPORTE**
