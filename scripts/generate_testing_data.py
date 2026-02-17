"""
ZEUES - Generador de Dataset de Testing para E2E Tests

Este script:
1. Borra todas las filas de la hoja Operaciones (TESTING) excepto header
2. Inserta 20 spools especializados que cubren todos los casos de testing E2E
3. Valida que los datos se insertaron correctamente

Estructura del dataset:
- 6 spools para tests DESTRUCTIVOS (se consumen)
- 10 spools BUFFER para múltiples ejecuciones
- 2 spools EDGE CASES (estados especiales)
- 2 spools CASOS ESPECIALES (dependencias)

Total: 20 spools = 6-7 ejecuciones completas de tests sin regenerar

Uso:
    python scripts/generate_testing_data.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config
from datetime import datetime


# ============================================================================
# CONSTANTES
# ============================================================================

# Índices de columnas críticas (base 0)
IDX_TAG_SPOOL = 6       # G - TAG_SPOOL
IDX_ARM = 21            # V - ARM (0/0.1/1.0)
IDX_SOLD = 22           # W - SOLD (0/0.1/1.0)
IDX_FECHA_MATERIALES = 52  # BA - FECHA_MATERIALES
IDX_FECHA_ARMADO = 53   # BB - FECHA_ARMADO
IDX_ARMADOR = 54        # BC - ARMADOR
IDX_FECHA_SOLDADURA = 55  # BD - FECHA_SOLDADURA
IDX_SOLDADOR = 56       # BE - SOLDADOR

TOTAL_COLUMNS = 57      # A-BE (57 columnas totales)

# Fecha base para materiales (siempre en pasado)
FECHA_MATERIALES_DEFAULT = "01/11/2025"

# Fecha completado (para spools ya completados)
FECHA_COMPLETADO_DEFAULT = "05/11/2025"


# ============================================================================
# DATASET DEFINITION - 20 SPOOLS
# ============================================================================

def build_dataset():
    """
    Construye el dataset de 20 spools especializados para testing.

    Returns:
        list[dict]: Lista de 20 diccionarios con definición de cada spool
    """
    dataset = []

    # ========================================================================
    # GRUPO 1: Tests DESTRUCTIVOS (6 spools - se consumen por tests)
    # ========================================================================

    # SPOOL 1: Test flujo completo INICIAR → COMPLETAR
    dataset.append({
        "tag_spool": "TEST-ARM-FLUJO-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "Flujo completo iniciar→completar ARM"
    })

    # SPOOL 2: Test ownership violation (CRÍTICO)
    dataset.append({
        "tag_spool": "TEST-ARM-OWNERSHIP-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "Ownership violation - Worker1 inicia, Worker2 intenta completar"
    })

    # SPOOL 3: Test completar sin iniciar
    dataset.append({
        "tag_spool": "TEST-ARM-NO-INICIADA-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "Intentar completar sin iniciar - 400 error"
    })

    # SPOOL 4: Test worker no encontrado
    dataset.append({
        "tag_spool": "TEST-ARM-WORKER-404-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "Worker inválido - 404 error"
    })

    # SPOOL 5: Test iniciar dos veces
    dataset.append({
        "tag_spool": "TEST-ARM-YA-INICIADA-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "Iniciar dos veces - 400 error"
    })

    # SPOOL 6: Test filtro GET /api/spools/iniciar
    dataset.append({
        "tag_spool": "TEST-ARM-INICIAR-FILTER-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "Filtro de spools disponibles para iniciar"
    })

    # ========================================================================
    # GRUPO 2: BUFFER ejecuciones múltiples (10 spools - todos ARM=0)
    # ========================================================================

    for i in range(1, 11):  # BUFFER-01 a BUFFER-10
        dataset.append({
            "tag_spool": f"TEST-ARM-BUFFER-{i:02d}",
            "arm": 0.0,
            "sold": 0.0,
            "fecha_materiales": FECHA_MATERIALES_DEFAULT,
            "fecha_armado": None,
            "armador": None,
            "fecha_soldadura": None,
            "soldador": None,
            "descripcion": f"Buffer para ejecución múltiple #{i}"
        })

    # ========================================================================
    # GRUPO 3: EDGE CASES (2 spools - estados especiales)
    # ========================================================================

    # SPOOL 17: ARM ya completado (ARM=1.0)
    dataset.append({
        "tag_spool": "TEST-ARM-COMPLETADO-01",
        "arm": 1.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": FECHA_COMPLETADO_DEFAULT,
        "armador": "Mauricio Rodriguez",
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "ARM completado - validar filtros no retorna"
    })

    # SPOOL 18: ARM en progreso asignado a Worker2 (ARM=0.1)
    dataset.append({
        "tag_spool": "TEST-ARM-PROGRESO-W2-01",
        "arm": 0.1,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": "Nicolás Rodriguez",
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "ARM en progreso - solo Worker2 puede completar"
    })

    # ========================================================================
    # GRUPO 4: CASOS ESPECIALES (2 spools - dependencias)
    # ========================================================================

    # SPOOL 19: SOLD bloqueado (ARM no completado)
    dataset.append({
        "tag_spool": "TEST-SOLD-BLOQUEADO-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": FECHA_MATERIALES_DEFAULT,
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "SOLD no puede iniciarse (ARM no completado)"
    })

    # SPOOL 20: ARM sin materiales (dependencia no satisfecha)
    dataset.append({
        "tag_spool": "TEST-ARM-SIN-MATERIALES-01",
        "arm": 0.0,
        "sold": 0.0,
        "fecha_materiales": None,  # BA vacía - dependencia no satisfecha
        "fecha_armado": None,
        "armador": None,
        "fecha_soldadura": None,
        "soldador": None,
        "descripcion": "ARM sin materiales - dependencia no satisfecha"
    })

    return dataset


# ============================================================================
# ROW BUILDER
# ============================================================================

def build_spool_row(spool_def: dict) -> list:
    """
    Construye una fila de 57 columnas para Google Sheets.

    Estructura:
    - Columnas A-F: Datos básicos (vacíos en este caso)
    - Columna G (6): TAG_SPOOL
    - Columnas H-U: Datos intermedios (vacíos)
    - Columna V (21): ARM
    - Columna W (22): SOLD
    - Columnas X-AZ: Datos intermedios (vacíos)
    - Columna BA (52): FECHA_MATERIALES
    - Columna BB (53): FECHA_ARMADO
    - Columna BC (54): ARMADOR
    - Columna BD (55): FECHA_SOLDADURA
    - Columna BE (56): SOLDADOR

    Args:
        spool_def: Diccionario con definición del spool

    Returns:
        list: Fila de 57 elementos
    """
    # Inicializar fila con 57 columnas vacías
    row = [""] * TOTAL_COLUMNS

    # Llenar columnas específicas
    row[IDX_TAG_SPOOL] = spool_def["tag_spool"]
    row[IDX_ARM] = spool_def["arm"]
    row[IDX_SOLD] = spool_def["sold"]
    row[IDX_FECHA_MATERIALES] = spool_def["fecha_materiales"] or ""
    row[IDX_FECHA_ARMADO] = spool_def["fecha_armado"] or ""
    row[IDX_ARMADOR] = spool_def["armador"] or ""
    row[IDX_FECHA_SOLDADURA] = spool_def["fecha_soldadura"] or ""
    row[IDX_SOLDADOR] = spool_def["soldador"] or ""

    return row


# ============================================================================
# GOOGLE SHEETS OPERATIONS
# ============================================================================

def clear_and_insert_data(repo: SheetsRepository, dataset: list):
    """
    Borra todas las filas (excepto header) e inserta el nuevo dataset.

    Args:
        repo: Instancia de SheetsRepository
        dataset: Lista de spools a insertar
    """
    sheet_name = config.HOJA_OPERACIONES_NOMBRE

    print("\n[2/4] Conectando a Google Sheets TESTING...")

    # Leer datos actuales para obtener header y contar filas
    current_data = repo.read_worksheet(sheet_name)
    header = current_data[0] if len(current_data) > 0 else []
    current_rows = len(current_data) - 1  # Excluir header

    print(f"  ✅ Conexión exitosa")
    print(f"  ✅ Hoja: {sheet_name}")
    print(f"  📊 Filas actuales: {current_rows} (+ 1 header)")

    # Obtener worksheet de gspread (para operaciones delete/append)
    spreadsheet = repo._get_spreadsheet()
    worksheet = spreadsheet.worksheet(sheet_name)

    # Confirmación de borrado
    print(f"\n[3/4] Borrando filas existentes...")
    if current_rows > 0:
        print(f"  ⚠️  Se borrarán {current_rows} fila(s) (header se preserva)")

        # Pedir confirmación
        confirm = input("  ¿Continuar? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y", "si", "s"]:
            print("  ❌ Operación cancelada por el usuario")
            sys.exit(0)

        # Borrar filas (de la 2 en adelante)
        # gspread usa 1-based indexing
        worksheet.delete_rows(2, current_rows + 1)
        print(f"  ✅ {current_rows} fila(s) borradas")
    else:
        print("  ℹ️  No hay filas para borrar (solo header)")

    # Insertar nuevas filas
    print(f"\n[4/4] Insertando {len(dataset)} nuevas filas...")

    # Construir filas
    rows_to_insert = []
    for spool_def in dataset:
        row = build_spool_row(spool_def)
        rows_to_insert.append(row)

    # Insertar en batch (más eficiente)
    if rows_to_insert:
        # Calcular rango exacto: A2:BE{last_row}
        # BE es la columna 57 (TOTAL_COLUMNS=57, de A=1 a BE=57)
        last_row = 1 + len(rows_to_insert)  # Header es fila 1
        range_notation = f"A2:BE{last_row}"

        # Actualizar en rango específico (evita desplazamiento de columnas)
        worksheet.update(range_notation, rows_to_insert, value_input_option='USER_ENTERED')
        print(f"  ✅ {len(rows_to_insert)} filas insertadas exitosamente en rango {range_notation}")
    else:
        print("  ⚠️  No hay filas para insertar")


# ============================================================================
# VALIDATION
# ============================================================================

def validate_insertion(repo: SheetsRepository, expected_count: int):
    """
    Valida que los datos se insertaron correctamente.

    Args:
        repo: Instancia de SheetsRepository
        expected_count: Número esperado de spools (sin contar header)
    """
    print(f"\n{'='*70}")
    print("VALIDACIÓN POST-INSERCIÓN")
    print(f"{'='*70}")

    # Leer datos actualizados
    data = repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

    # Validar conteo total
    total_rows = len(data) - 1  # Excluir header
    if total_rows == expected_count:
        print(f"✅ Total filas: {len(data)} (1 header + {total_rows} datos)")
    else:
        print(f"❌ ERROR: Esperado {expected_count} filas, encontrado {total_rows}")
        return False

    # Validar TAGs únicos
    tags = []
    for row in data[1:]:  # Skip header
        if len(row) > IDX_TAG_SPOOL and row[IDX_TAG_SPOOL]:
            tags.append(row[IDX_TAG_SPOOL])

    unique_tags = len(set(tags))
    if unique_tags == expected_count:
        print(f"✅ TAGs únicos: {unique_tags}")
    else:
        print(f"⚠️  TAGs únicos: {unique_tags} (esperado {expected_count})")

    # Contar spools por estado ARM
    count_pendiente = 0
    count_progreso = 0
    count_completado = 0

    for row in data[1:]:
        if len(row) > IDX_ARM and row[IDX_ARM] != "":
            arm_value = float(row[IDX_ARM])
            if arm_value == 0.0:
                count_pendiente += 1
            elif arm_value == 0.1:
                count_progreso += 1
            elif arm_value == 1.0:
                count_completado += 1

    print(f"✅ Spools ARM=0 (pendiente): {count_pendiente}")
    print(f"✅ Spools ARM=0.1 (en progreso): {count_progreso}")
    print(f"✅ Spools ARM=1.0 (completado): {count_completado}")

    # Validar distribución esperada (18 pendientes, 1 progreso, 1 completado)
    if count_pendiente == 18 and count_progreso == 1 and count_completado == 1:
        print(f"\n🎉 Dataset generado exitosamente")
        print(f"{'='*70}")
        return True
    else:
        print(f"\n⚠️  Distribución de estados no coincide con lo esperado")
        print(f"   Esperado: 18 pendientes, 1 en progreso, 1 completado")
        print(f"   Encontrado: {count_pendiente} pendientes, {count_progreso} en progreso, {count_completado} completado")
        print(f"{'='*70}")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Función principal - ejecuta el flujo completo.
    """
    print(f"{'='*70}")
    print("ZEUES - Generador de Dataset de Testing")
    print(f"{'='*70}")

    # Paso 1: Construir dataset
    print("\n[1/4] Construyendo dataset de 20 spools...")
    dataset = build_dataset()

    # Contar por grupo
    group1 = [s for s in dataset if "FLUJO" in s["tag_spool"] or "OWNERSHIP" in s["tag_spool"] or
              "NO-INICIADA" in s["tag_spool"] or "WORKER-404" in s["tag_spool"] or
              "YA-INICIADA" in s["tag_spool"] or "INICIAR-FILTER" in s["tag_spool"]]
    group2 = [s for s in dataset if "BUFFER" in s["tag_spool"]]
    group3 = [s for s in dataset if "COMPLETADO" in s["tag_spool"] or "PROGRESO" in s["tag_spool"]]
    group4 = [s for s in dataset if "SOLD-BLOQUEADO" in s["tag_spool"] or "SIN-MATERIALES" in s["tag_spool"]]

    print(f"  ✅ Grupo 1: {len(group1)} spools destructivos")
    print(f"  ✅ Grupo 2: {len(group2)} spools buffer")
    print(f"  ✅ Grupo 3: {len(group3)} edge cases")
    print(f"  ✅ Grupo 4: {len(group4)} casos especiales")
    print(f"  📊 Total: {len(dataset)} spools")

    # Paso 2-4: Actualizar Google Sheets
    repo = SheetsRepository()
    clear_and_insert_data(repo, dataset)

    # Paso 5: Validar
    validate_insertion(repo, expected_count=len(dataset))


if __name__ == "__main__":
    main()
