# Auditoría de consistencia TAG ↔ OT — Sheet de PRODUCCIÓN

- **Fecha:** 2026-06-05
- **Sheet:** `__Kronos_Registro_Piping R04` (`17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ`)
- **Hojas leídas:** `Operaciones` (1.993 filas de datos) · `Uniones` (1.002 filas de datos)
- **Tipo:** solo lectura. No se modificó ningún dato.
- **Script:** `backend/scripts/audit_tag_ot_consistency.py`

## Resumen ejecutivo

| Chequeo | Resultado |
|---|---|
| Uniones: TAG con >1 OT | ✅ 0 |
| Operaciones: TAG con >1 OT | ⚠️ 6 |
| Operaciones: filas con OT vacía | ⚠️ 675 |
| Cross-sheet: OT del mismo TAG difiere entre hojas | ⚠️ 15 |
| Huérfanos en Uniones (tag sin spool en Operaciones) | ⚠️ 16 |
| Spools sin uniones (informativo) | 1.665 |

## Hallazgo estructural (revisar con Matías)

La columna del **tag de spool tiene distinto nombre en cada hoja**:

- **Operaciones** → columna **`TAG`** (col. G). _No_ existe `TAG_SPOOL`.
- **Uniones** → columna **`TAG_SPOOL`** (col. D).

Además, la columna **`OT`** de ambas hojas **no contiene un número de OT** (ej. `75119`)
sino un código compuesto tipo `SP-10114-NV0642`. El `backend/core/sheet_schema.py` documenta
`TAG_SPOOL` y `OT` con otra semántica → conviene confirmar el significado real de estas
columnas antes de cualquier corrección automatizada.

La comparación de esta auditoría fue **`OT` (Operaciones) vs `OT` (Uniones)** para el mismo tag.

## 1. Operaciones — un TAG con más de una OT (6)

| TAG | OTs en conflicto |
|---|---|
| `3-ECU-049` | `SP-10056-NV0620` · `SP-10056-NV0620R` |
| `3-ECU-060` | `SP-10057-NV0620` · `SP-10057-NV0620R` |
| `Spool 01` | `KM-NV0574-0001` · `NA` |
| `Spool 02` | `KM-NV0574-0001` · `NA` |
| `SPOOL 2610-SP-32326` | `SP-10555-NV0661` · `SP-10574-NV0661` |
| `SPOOL 2610-SP-32333-E` | `SP-10510-NV0661` · `SP-10511-NV0661` |

> Nota: los `3-ECU-*` parecen el mismo SP con sufijo de revisión `R`. `Spool 01/02` tienen
> una fila con OT real y otra con `NA`.

## 2. Cross-sheet — OT del mismo TAG difiere entre Operaciones y Uniones (15)

Referencias de celda A1 (columna `OT`: Operaciones=`C`, Uniones=`B`).

### Grupo MK-1923 — discrepancia en el sufijo **NV** (Oper=NV0642 vs Uniones=NV0643/0644/0647)

| TAG_SPOOL | OT Operaciones | OT Uniones | Celda Oper | Celda Uniones (1ª) |
|---|---|---|---|---|
| MK-1923-TW-17422-003 | SP-10114-NV0642 | SP-10114-**NV0643** | `Operaciones!C1460` | `Uniones!B64` |
| MK-1923-TW-17422-004 | SP-10115-NV0642 | SP-10115-**NV0643** | `Operaciones!C1461` | `Uniones!B57` |
| MK-1923-TW-17422-005 | SP-10116-NV0642 | SP-10116-**NV0644** | `Operaciones!C1462` | `Uniones!B78` |
| MK-1923-TW-34059-006 | SP-10125-NV0642 | SP-10125-**NV0647** | `Operaciones!C1472` | `Uniones!B28` |
| MK-1923-TW-34059-009 | SP-10127-NV0642 | SP-10127-**NV0647** | `Operaciones!C1474` | `Uniones!B44` |
| MK-1923-TW-34059-010 | SP-10128-NV0642 | SP-10128-**NV0647** | `Operaciones!C1475` | `Uniones!B34` |
| MK-1923-TW-34059-011 | SP-10126-NV0642 | SP-10126-**NV0647** | `Operaciones!C1473` | `Uniones!B32` |

> Patrón: en Operaciones la NV es `NV0642`; en Uniones varía. Sugiere error sistemático de NV
> en una de las dos hojas para el proyecto 1923. Revisar cuál es la NV correcta.

### Grupo 2610 — número **SP** distinto entre hojas

| TAG_SPOOL | OT Operaciones | OT Uniones | Celda Oper | Celda Uniones (1ª) |
|---|---|---|---|---|
| SPOOL 2610-SP-32301 | SP-**10571**-NV0661 | SP-**10477**-NV0661 | `Operaciones!C1991` | `Uniones!B968` |
| SPOOL 2610-SP-32302 | SP-**10572**-NV0661 | SP-**10478**-NV0661 | `Operaciones!C1992` | `Uniones!B956` |
| SPOOL 2610-SP-32311 | SP-**10568**-NV0661 | SP-**10488**-NV0661 | `Operaciones!C1988` | `Uniones!B942` |
| SPOOL 2610-SP-32316 | SP-**10553**-NV0661 | SP-**10493**-NV0661 | `Operaciones!C1971` | `Uniones!B958` |
| SPOOL 2610-SP-32318 | SP-**10548**-NV0661 | SP-**10495**-NV0661 | `Operaciones!C1966` | `Uniones!B948` |
| SPOOL 2610-SP-32319 | SP-**10569**-NV0661 | SP-**10496**-NV0661 | `Operaciones!C1989` | `Uniones!B940` |
| SPOOL 2610-SP-32326 | SP-10555 / SP-10574-NV0661 | SP-**10503**-NV0661 | `Operaciones!C1974`+`C1994` | `Uniones!B982` |
| SPOOL 2610-SP-32327 | SP-**10573**-NV0661 | SP-**10504**-NV0661 | `Operaciones!C1993` | `Uniones!B936` |

> En el grupo 2610 el número interno `SP-#####` no coincide entre hojas. La NV (`NV0661`)
> sí coincide. `SPOOL 2610-SP-32326` además aparece dos veces en Operaciones (ver §1).

## 3. Huérfanos en Uniones — tag con uniones pero sin spool en Operaciones (16)

```
#N/A                       ← fila basura: el TAG_SPOOL literal es "#N/A" (Uniones)
MK-1325-GW-24360-001
MK-1325-GW-24365-007
MK-1325-GW-24365-009
MK-1325-GW-24366-006
MK-1343-TW-26933-007
MK-1343-TW-26933-012
MK-1343-TW-26933-025
MK-1923-TK-34058-001
MK-1923-TK-34143-001
MK-1923-TK-34143-002
MK-1923-TK-34145-001
MK-1923-TK-34145-002
MK-1923-TW-34059-001
MK-1923-TW-34060-006
SPOOL 2610-SP-32361
```

> `#N/A` es un dato corrupto en Uniones (fórmula rota arrastrada como texto). Los `MK-*`
> existen como uniones pero no tienen fila correspondiente en Operaciones — verificar si el
> spool no fue cargado en Operaciones o si el tag está mal escrito en una de las dos hojas.

## 4. Informativo — Spools en Operaciones sin uniones (1.665)

Esperable: la hoja `Uniones` solo cubre los proyectos cargados a nivel de junta. No es un
error en sí; se omite el listado completo por volumen.

## Reproducción

```bash
source venv/bin/activate
python backend/scripts/audit_tag_ot_consistency.py
```

El script apunta directamente al ID de PRODUCCIÓN vía `open_by_key()` (no usa
`config.GOOGLE_SHEET_ID`, que en local apunta a testing). Es read-only.
