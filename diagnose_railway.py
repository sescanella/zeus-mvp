#!/usr/bin/env python3
"""
Script de diagnóstico profundo para identificar por qué Railway no carga spools.

Verifica:
1. Conexión a Google Sheets
2. Hojas disponibles en el spreadsheet
3. Existencia de hoja "Roles"
4. Datos en hoja "Roles"
5. RoleRepository funcionalidad
6. WorkerService carga de roles
7. Comparación de datos entre hojas
"""
import os
import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.role_repository import RoleRepository
from backend.services.worker_service import WorkerService
from backend.config import config

def print_section(title: str):
    """Helper para imprimir secciones"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def diagnose_railway():
    """Diagnóstico profundo de Railway vs Local"""

    print_section("DIAGNÓSTICO PROFUNDO - Railway Spools Issue")

    # 1. Validar configuración
    print_section("1. CONFIGURACIÓN")
    try:
        config.validate()
        print(f"✅ Configuración válida")
        print(f"   - GOOGLE_SHEET_ID: {config.GOOGLE_SHEET_ID}")
        print(f"   - Hoja Operaciones: {config.HOJA_OPERACIONES_NOMBRE}")
        print(f"   - Hoja Trabajadores: {config.HOJA_TRABAJADORES_NOMBRE}")
        print(f"   - Hoja Metadata: {config.HOJA_METADATA_NOMBRE}")
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        return

    # 2. Conectar a Google Sheets
    print_section("2. CONEXIÓN A GOOGLE SHEETS")
    repo = SheetsRepository()
    try:
        spreadsheet = repo._get_spreadsheet()
        print(f"✅ Conectado a: {spreadsheet.title}")
        print(f"   URL: {spreadsheet.url}")
    except Exception as e:
        print(f"❌ Error conectando: {str(e)}")
        return

    # 3. Listar todas las hojas disponibles
    print_section("3. HOJAS DISPONIBLES EN SPREADSHEET")
    try:
        all_worksheets = spreadsheet.worksheets()
        print(f"✅ Total de hojas: {len(all_worksheets)}")
        for i, ws in enumerate(all_worksheets, 1):
            print(f"   {i}. '{ws.title}' (ID: {ws.id}, {ws.row_count} filas)")
    except Exception as e:
        print(f"❌ Error listando hojas: {str(e)}")

    # 4. Verificar hoja "Roles"
    print_section("4. VERIFICACIÓN HOJA 'Roles'")
    try:
        roles_sheet = spreadsheet.worksheet("Roles")
        print(f"✅ Hoja 'Roles' EXISTE")
        print(f"   - Título: {roles_sheet.title}")
        print(f"   - Filas: {roles_sheet.row_count}")
        print(f"   - Columnas: {roles_sheet.col_count}")

        # Obtener headers
        headers = roles_sheet.row_values(1)
        print(f"   - Headers: {headers}")

        # Obtener primeros 5 registros
        all_records = roles_sheet.get_all_records()
        print(f"   - Total registros: {len(all_records)}")
        print(f"   - Primeros 3 registros:")
        for i, record in enumerate(all_records[:3], 1):
            print(f"     {i}. {record}")

        roles_sheet_exists = True
    except Exception as e:
        print(f"❌ Hoja 'Roles' NO EXISTE o error al leer")
        print(f"   Error: {str(e)}")
        roles_sheet_exists = False

    # 5. Verificar RoleRepository
    print_section("5. VERIFICACIÓN RoleRepository")
    if roles_sheet_exists:
        try:
            role_repo = RoleRepository(spreadsheet)
            all_roles = role_repo.get_all_roles()
            print(f"✅ RoleRepository funciona")
            print(f"   - Total roles cargados: {len(all_roles)}")

            # Agrupar por worker_id
            roles_by_worker = {}
            for worker_role in all_roles:
                if worker_role.activo:
                    if worker_role.id not in roles_by_worker:
                        roles_by_worker[worker_role.id] = []
                    roles_by_worker[worker_role.id].append(worker_role.rol.value)

            print(f"   - Workers con roles: {len(roles_by_worker)}")
            print(f"   - Ejemplo roles por worker:")
            for worker_id, roles in list(roles_by_worker.items())[:3]:
                print(f"     Worker {worker_id}: {roles}")

        except Exception as e:
            print(f"❌ Error en RoleRepository")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️  Saltando verificación RoleRepository (hoja no existe)")

    # 6. Verificar WorkerService
    print_section("6. VERIFICACIÓN WorkerService")
    try:
        worker_service = WorkerService()
        all_workers = worker_service.get_all_active_workers()
        print(f"✅ WorkerService funciona")
        print(f"   - Total workers activos: {len(all_workers)}")

        # Verificar roles en workers
        workers_with_roles = [w for w in all_workers if w.roles and len(w.roles) > 0]
        workers_without_roles = [w for w in all_workers if not w.roles or len(w.roles) == 0]

        print(f"   - Workers CON roles: {len(workers_with_roles)}")
        print(f"   - Workers SIN roles: {len(workers_without_roles)}")

        if workers_with_roles:
            print(f"   - Ejemplo workers CON roles:")
            for w in workers_with_roles[:3]:
                print(f"     {w.id} - {w.nombre_completo}: {w.roles}")

        if workers_without_roles:
            print(f"   - Ejemplo workers SIN roles:")
            for w in workers_without_roles[:3]:
                print(f"     {w.id} - {w.nombre_completo}: {w.rol} (roles array: {w.roles})")

    except Exception as e:
        print(f"❌ Error en WorkerService")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()

    # 7. Verificar hoja Operaciones
    print_section("7. VERIFICACIÓN Hoja Operaciones")
    try:
        operaciones_sheet = spreadsheet.worksheet(config.HOJA_OPERACIONES_NOMBRE)
        all_data = operaciones_sheet.get_all_values()

        col_index_aj = 35  # Columna AJ (fecha_materiales)
        col_index_ak = 36  # Columna AK (fecha_armado)

        spools_con_ba = 0
        spools_con_bb = 0
        spools_validos = 0

        for i, row in enumerate(all_data[1:], start=2):
            if len(row) > col_index_ak:
                fecha_materiales = row[col_index_aj].strip() if len(row) > col_index_aj else ""
                fecha_armado = row[col_index_ak].strip()

                if fecha_materiales:
                    spools_con_ba += 1
                if fecha_armado:
                    spools_con_bb += 1
                if fecha_materiales and not fecha_armado:
                    spools_validos += 1

        print(f"✅ Análisis de Operaciones")
        print(f"   - Total filas: {len(all_data) - 1}")
        print(f"   - Spools con fecha_materiales (BA): {spools_con_ba}")
        print(f"   - Spools con fecha_armado (BB): {spools_con_bb}")
        print(f"   - Spools VÁLIDOS para INICIAR ARM (BA llena, BB vacía): {spools_validos}")

    except Exception as e:
        print(f"❌ Error verificando Operaciones")
        print(f"   Error: {str(e)}")

    # 8. Conclusión
    print_section("8. CONCLUSIÓN")
    print()
    print("Posibles causas identificadas:")
    print()

    if not roles_sheet_exists:
        print("🔴 CAUSA CRÍTICA: Hoja 'Roles' NO EXISTE")
        print("   → Railway no puede cargar roles desde hoja Roles")
        print("   → Todos los workers tendrán roles: []")
        print("   → Frontend filtra workers y no encuentra ninguno")
        print("   → SOLUCIÓN: Crear hoja 'Roles' con estructura correcta")
    else:
        print("✅ Hoja 'Roles' existe")

        if len(workers_without_roles) > 0:
            print("🟡 ADVERTENCIA: Algunos workers no tienen roles asignados")
            print(f"   → {len(workers_without_roles)} workers sin roles en array")
            print("   → Verificar que hoja Roles tenga datos para todos los workers")
        else:
            print("✅ Todos los workers tienen roles asignados")
            print("   → El problema NO está en la carga de roles")
            print("   → Verificar lógica de filtrado en ValidationService")

    print()
    print("=" * 80)

if __name__ == "__main__":
    diagnose_railway()
