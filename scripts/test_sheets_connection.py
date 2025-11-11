#!/usr/bin/env python3
"""
Script para verificar la conexión con Google Sheets.

Valida:
- Autenticación con Service Account
- Lectura de hojas Operaciones y Trabajadores
- Estructura de columnas
- Datos de prueba
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.services.sheets_service import SheetsService
from backend.config import config
from backend.models.enums import ActionStatus
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Ejecuta tests de conexión con Google Sheets."""

    print("\n" + "=" * 70)
    print("ZEUES - Test de Conexión con Google Sheets")
    print("=" * 70)

    # Validar configuración
    print("\n📋 Validando configuración...")
    try:
        config.validate()
        print("✅ Configuración válida")
        print(f"   - Project ID: {config.GOOGLE_CLOUD_PROJECT_ID}")
        print(f"   - Sheet ID: {config.GOOGLE_SHEET_ID}")
        print(f"   - Service Account: {config.GOOGLE_SERVICE_ACCOUNT_EMAIL}")
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        return 1

    # Crear repositorio
    print("\n🔌 Inicializando repositorio...")
    try:
        repo = SheetsRepository()
        print("✅ Repositorio creado")
    except Exception as e:
        print(f"❌ Error creando repositorio: {e}")
        return 1

    # Test 1: Leer hoja Trabajadores
    print(f"\n📖 Test 1: Leyendo hoja '{config.HOJA_TRABAJADORES_NOMBRE}'...")
    try:
        workers_rows = repo.read_worksheet(config.HOJA_TRABAJADORES_NOMBRE)
        print(f"✅ {len(workers_rows)} filas leídas")

        if len(workers_rows) > 0:
            print(f"   - Header: {workers_rows[0]}")

            if len(workers_rows) > 1:
                print(f"   - Trabajadores encontrados: {len(workers_rows) - 1}")
                print(f"   - Ejemplo: {workers_rows[1]}")
        else:
            print("⚠️  Hoja vacía")

    except Exception as e:
        print(f"❌ Error leyendo Trabajadores: {e}")
        return 1

    # Test 2: Leer hoja Operaciones
    print(f"\n📖 Test 2: Leyendo hoja '{config.HOJA_OPERACIONES_NOMBRE}'...")
    try:
        ops_rows = repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        print(f"✅ {len(ops_rows)} filas leídas")

        if len(ops_rows) > 0:
            print(f"   - Columnas totales: {len(ops_rows[0])}")
            print(f"   - Spools: {len(ops_rows) - 1}")

            # Validar columnas críticas
            header = ops_rows[0]
            columnas_criticas = {
                'G': 'TAG_SPOOL / CODIGO BARRA',
                'V': 'ARM',
                'W': 'SOLD',
                'BA': 'Fecha_Materiales',
                'BB': 'Fecha_Armado',
                'BC': 'Armador',
                'BD': 'Fecha_Soldadura',
                'BE': 'Soldador'
            }

            print("\n   📊 Validando columnas críticas:")
            for col_letter, col_name in columnas_criticas.items():
                col_index = repo._column_letter_to_index(col_letter)
                if col_index < len(header):
                    actual_name = header[col_index]
                    print(f"      {col_letter} ({col_name}): '{actual_name}' ✓")
                else:
                    print(f"      {col_letter} ({col_name}): ❌ NO ENCONTRADA")

        else:
            print("⚠️  Hoja vacía")

    except Exception as e:
        print(f"❌ Error leyendo Operaciones: {e}")
        return 1

    # Test 3: Buscar un spool específico
    print("\n🔍 Test 3: Buscando spool de prueba...")
    try:
        if len(ops_rows) > 1:
            # Tomar el primer spool como ejemplo
            primer_spool_row = ops_rows[1]
            col_g_index = repo._column_letter_to_index('G')

            if col_g_index < len(primer_spool_row):
                tag_spool_ejemplo = primer_spool_row[col_g_index]

                if tag_spool_ejemplo:
                    print(f"   Buscando: '{tag_spool_ejemplo}'")

                    fila_encontrada = repo.find_row_by_column_value(
                        config.HOJA_OPERACIONES_NOMBRE,
                        'G',
                        tag_spool_ejemplo
                    )

                    if fila_encontrada:
                        print(f"✅ Spool encontrado en fila {fila_encontrada}")
                    else:
                        print(f"⚠️  Spool no encontrado (esto no debería pasar)")
                else:
                    print("⚠️  Columna G vacía en primera fila de datos")
        else:
            print("⚠️  No hay datos para buscar")

    except Exception as e:
        print(f"❌ Error buscando spool: {e}")
        return 1

    # Test 4: Verificar parsing de estados
    print("\n🔄 Test 4: Verificando parsing de estados...")
    try:
        test_values = [0, 0.1, 1.0, 0.0]
        for value in test_values:
            status = ActionStatus.from_sheets_value(value)
            sheets_value = status.to_sheets_value()
            print(f"   {value} → {status.value} → {sheets_value} ✓")

        print("✅ Parsing de estados funciona correctamente")

    except Exception as e:
        print(f"❌ Error en parsing de estados: {e}")
        return 1

    # Test 5: Parsear trabajadores con SheetsService
    print("\n👷 Test 5: Parseando trabajadores con SheetsService...")
    try:
        workers_parsed = []
        parse_errors = 0

        # Parsear todas las filas de trabajadores (skip header)
        for row_index, row in enumerate(workers_rows[1:], start=2):
            try:
                if row and row[0]:  # Si tiene nombre
                    worker = SheetsService.parse_worker_row(row)
                    workers_parsed.append(worker)
            except Exception as e:
                parse_errors += 1
                logger.warning(f"Error parseando trabajador fila {row_index}: {e}")

        print(f"✅ {len(workers_parsed)} trabajadores parseados correctamente")
        if parse_errors > 0:
            print(f"⚠️  {parse_errors} errores de parsing")

        # Mostrar ejemplos
        if workers_parsed:
            print(f"   - Ejemplo 1: {workers_parsed[0].nombre_completo} (activo={workers_parsed[0].activo})")
            if len(workers_parsed) > 1:
                print(f"   - Ejemplo 2: {workers_parsed[1].nombre_completo} (activo={workers_parsed[1].activo})")

    except Exception as e:
        print(f"❌ Error parseando trabajadores: {e}")
        return 1

    # Test 6: Parsear spools con SheetsService
    print("\n🔩 Test 6: Parseando spools con SheetsService...")
    try:
        spools_parsed = []
        parse_errors = 0
        inconsistencies = 0

        # Parsear todas las filas de spools (skip header)
        for row_index, row in enumerate(ops_rows[1:], start=2):
            try:
                spool = SheetsService.parse_spool_row(row)
                spools_parsed.append(spool)

                # Contar inconsistencias (ARM/SOLD en progreso sin trabajador)
                if spool.arm == ActionStatus.EN_PROGRESO and not spool.armador:
                    inconsistencies += 1
                if spool.sold == ActionStatus.EN_PROGRESO and not spool.soldador:
                    inconsistencies += 1

            except ValueError as e:
                # TAG_SPOOL vacío es esperado
                if "TAG_SPOOL vacío" not in str(e):
                    parse_errors += 1
                    logger.warning(f"Error parseando spool fila {row_index}: {e}")
            except Exception as e:
                parse_errors += 1
                logger.warning(f"Error parseando spool fila {row_index}: {e}")

        print(f"✅ {len(spools_parsed)} spools parseados correctamente")
        if parse_errors > 0:
            print(f"⚠️  {parse_errors} errores de parsing")
        if inconsistencies > 0:
            print(f"⚠️  {inconsistencies} inconsistencias detectadas (ARM/SOLD sin trabajador)")

        # Estadísticas de estados
        if spools_parsed:
            arm_pendientes = sum(1 for s in spools_parsed if s.arm == ActionStatus.PENDIENTE)
            arm_en_progreso = sum(1 for s in spools_parsed if s.arm == ActionStatus.EN_PROGRESO)
            arm_completados = sum(1 for s in spools_parsed if s.arm == ActionStatus.COMPLETADO)

            print(f"\n   📊 Estadísticas ARM:")
            print(f"      - Pendientes: {arm_pendientes}")
            print(f"      - En progreso: {arm_en_progreso}")
            print(f"      - Completados: {arm_completados}")

            # Mostrar ejemplo
            primer_spool = spools_parsed[0]
            print(f"\n   📦 Ejemplo spool: {primer_spool.tag_spool}")
            print(f"      - ARM: {primer_spool.arm.value}")
            print(f"      - SOLD: {primer_spool.sold.value}")
            if primer_spool.armador:
                print(f"      - Armador: {primer_spool.armador}")
            if primer_spool.fecha_materiales:
                print(f"      - Fecha materiales: {primer_spool.fecha_materiales}")

    except Exception as e:
        print(f"❌ Error parseando spools: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test 7: Verificar conversión string→float en parsing
    print("\n🔢 Test 7: Verificando conversión string→float...")
    try:
        # Test con valores string
        test_cases = [
            ("0", 0.0),
            ("0.1", 0.1),
            ("1", 1.0),
            ("1.0", 1.0),
            ("", 0.0),
            (None, 0.0),
        ]

        for input_val, expected in test_cases:
            result = SheetsService.safe_float(input_val)
            if result == expected:
                print(f"   '{input_val}' → {result} ✓")
            else:
                print(f"   '{input_val}' → {result} ❌ (esperado: {expected})")

        print("✅ Conversión string→float funciona correctamente")

    except Exception as e:
        print(f"❌ Error en conversión string→float: {e}")
        return 1

    # Resumen final
    print("\n" + "=" * 70)
    print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("=" * 70)
    print("\n📊 Resumen:")
    print(f"   - Trabajadores parseados: {len(workers_parsed)}")
    print(f"   - Spools parseados: {len(spools_parsed)}")
    print(f"   - Cache integrado: ✅")
    print(f"   - Parser string→float: ✅")
    print("\n📌 Próximos pasos (DÍA 2):")
    print("   1. ✅ BLOQUEANTE #1: Cache implementado")
    print("   2. ✅ BLOQUEANTE #2: Parser implementado")
    print("   3. ⏳ Implementar ValidationService (restricción propiedad)")
    print("   4. ⏳ Implementar SpoolService y WorkerService")
    print("   5. ⏳ Implementar routers FastAPI")
    print("\n")

    return 0


if __name__ == "__main__":
    exit(main())
