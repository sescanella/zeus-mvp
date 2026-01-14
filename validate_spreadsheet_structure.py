#!/usr/bin/env python3
"""
Script de validación de estructura del spreadsheet.

Verifica que todas las columnas críticas existen y están correctamente nombradas.
Ejecutar este script ANTES de hacer cambios en la estructura del spreadsheet.

USO:
    python3 validate_spreadsheet_structure.py

CUÁNDO USAR:
- Antes de eliminar columnas del spreadsheet
- Después de reorganizar columnas
- Si sospechas que la estructura cambió y puede causar errores
- Como verificación rutinaria mensual

El script te dirá exactamente qué columnas están OK y cuáles faltan.
"""
import sys
from pathlib import Path

# Agregar backend al path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.services.spool_service_v2 import SpoolServiceV2
from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config
import logging

# Configurar logging para ver detalles
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Helper para imprimir secciones"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def validate_structure():
    """Valida la estructura del spreadsheet"""

    print_section("VALIDACIÓN DE ESTRUCTURA - Spreadsheet ZEUES")

    # 1. Conectar a Google Sheets
    print("\n🔌 1. CONEXIÓN A GOOGLE SHEETS")
    try:
        repo = SheetsRepository()
        spreadsheet = repo._get_spreadsheet()
        print(f"   ✅ Conectado a: {spreadsheet.title}")
        print(f"   📊 ID: {config.GOOGLE_SHEET_ID}")
    except Exception as e:
        print(f"   ❌ Error conectando: {str(e)}")
        return False

    # 2. Listar hojas disponibles
    print("\n📋 2. HOJAS DISPONIBLES")
    try:
        all_worksheets = spreadsheet.worksheets()
        print(f"   Total: {len(all_worksheets)} hojas")
        for i, ws in enumerate(all_worksheets, 1):
            print(f"   {i}. {ws.title}")
    except Exception as e:
        print(f"   ❌ Error listando hojas: {str(e)}")

    # 3. Verificar hoja Operaciones
    print("\n🔍 3. VERIFICACIÓN HOJA 'Operaciones'")
    try:
        operaciones_sheet = spreadsheet.worksheet(config.HOJA_OPERACIONES_NOMBRE)
        print(f"   ✅ Hoja encontrada")
        print(f"   📏 Filas: {operaciones_sheet.row_count}")
        print(f"   📐 Columnas: {operaciones_sheet.col_count}")

        # Leer header (row 1)
        header_row = operaciones_sheet.row_values(1)
        print(f"\n   📝 Header (primeras 10 columnas):")
        for idx, col_name in enumerate(header_row[:10], 1):
            if col_name:
                print(f"      Col {idx:2d}: {col_name}")

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

    # 4. VALIDAR COLUMNAS CRÍTICAS (lo más importante)
    print_section("⚠️  4. VALIDACIÓN DE COLUMNAS CRÍTICAS")

    try:
        # Intentar crear SpoolServiceV2 (esto ejecuta la validación)
        service = SpoolServiceV2()

        # Forzar inicialización (ejecuta _validate_critical_columns)
        service._ensure_column_map()

        print("\n   🎉 ¡TODAS LAS COLUMNAS CRÍTICAS ENCONTRADAS!")
        print("\n   Columnas validadas:")

        # Mostrar mapeo de columnas críticas
        critical_cols = [
            "TAG_SPOOL", "Fecha_Materiales", "Fecha_Armado",
            "Armador", "Fecha_Soldadura", "Soldador"
        ]

        for col_name in critical_cols:
            normalized = col_name.lower().replace("_", "").replace(" ", "")
            if normalized in service.column_map:
                col_idx = service.column_map[normalized]
                # Convertir índice a letra de columna Excel (A, B, C...)
                col_letter = chr(65 + col_idx) if col_idx < 26 else f"A{chr(65 + col_idx - 26)}"
                print(f"      ✅ {col_name:20s} → Columna {col_letter} (índice {col_idx})")
            else:
                print(f"      ❌ {col_name:20s} → NO ENCONTRADA")

        # Test rápido de spools disponibles
        print("\n   🧪 Test de spools disponibles:")
        spools_iniciar_arm = service.get_spools_disponibles_para_iniciar_arm()
        spools_completar_arm = service.get_spools_disponibles_para_completar_arm()
        spools_iniciar_sold = service.get_spools_disponibles_para_iniciar_sold()
        spools_completar_sold = service.get_spools_disponibles_para_completar_sold()

        print(f"      INICIAR ARM: {len(spools_iniciar_arm)} spools")
        print(f"      COMPLETAR ARM: {len(spools_completar_arm)} spools")
        print(f"      INICIAR SOLD: {len(spools_iniciar_sold)} spools")
        print(f"      COMPLETAR SOLD: {len(spools_completar_sold)} spools")

        return True

    except ValueError as e:
        print(f"\n   ❌ ERROR: Faltan columnas críticas\n")
        print(str(e))
        return False
    except Exception as e:
        print(f"\n   ❌ ERROR INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal"""
    print_section("🛡️  ZEUES - Validación de Estructura del Spreadsheet v2.2")

    success = validate_structure()

    # Resumen final
    print_section("RESUMEN")
    if success:
        print("\n✅ ¡ESTRUCTURA VÁLIDA!")
        print("\nTu spreadsheet tiene todas las columnas críticas necesarias.")
        print("Es seguro continuar usando el sistema.")
        print("\n⚠️  RECOMENDACIONES:")
        print("   - NO elimines las columnas críticas listadas arriba")
        print("   - Si necesitas eliminar columnas, elimina solo las no críticas")
        print("   - Ejecuta este script después de cualquier cambio en la estructura")
    else:
        print("\n❌ ¡ESTRUCTURA INVÁLIDA!")
        print("\nEl spreadsheet tiene problemas de estructura.")
        print("Revisa los errores arriba y corrige antes de continuar.")
        print("\n💡 SOLUCIONES POSIBLES:")
        print("   1. Restaura las columnas faltantes desde el historial de Google Sheets")
        print("   2. Verifica que el header (row 1) tenga los nombres correctos")
        print("   3. Si renombraste una columna, usa el nombre original")

    print("\n" + "=" * 80 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
