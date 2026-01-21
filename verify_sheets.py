#!/usr/bin/env python3
"""
Script de verificación para diagnosticar por qué no aparecen spools en INICIAR ARM
"""
import os
import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config

def verificar_sheets():
    """Verifica las 3 causas probables del problema"""
    print("=" * 80)
    print("VERIFICACIÓN DE GOOGLE SHEETS - DIAGNÓSTICO INICIAR ARM")
    print("=" * 80)
    print()

    # Validar configuración
    try:
        config.validate()
        print(f"✅ Configuración válida")
        print(f"   - Sheet ID: {config.GOOGLE_SHEET_ID}")
        print(f"   - Hoja Operaciones: {config.HOJA_OPERACIONES_NOMBRE}")
        print(f"   - Hoja Trabajadores: {config.HOJA_TRABAJADORES_NOMBRE}")
        print(f"   - Hoja Metadata: {config.HOJA_METADATA_NOMBRE}")
        print()
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        return

    repo = SheetsRepository()

    # Obtener el spreadsheet
    try:
        spreadsheet = repo._get_spreadsheet()
        print(f"✅ Conectado a: {spreadsheet.title}")
        print()
    except Exception as e:
        print(f"❌ Error conectando a Google Sheets: {str(e)}")
        return

    # CAUSA 1: Verificar si existe la hoja "Metadata"
    print("📊 CAUSA 1: Verificando si existe la hoja 'Metadata'...")
    try:
        # Intentar acceder a la hoja Metadata
        sheet = spreadsheet.worksheet(config.HOJA_METADATA_NOMBRE)
        print(f"✅ La hoja '{config.HOJA_METADATA_NOMBRE}' EXISTE")
        metadata_existe = True

        # Obtener todas las filas de metadata
        all_metadata = sheet.get_all_records()
        print(f"   - Total de eventos en Metadata: {len(all_metadata)}")

        if len(all_metadata) > 0:
            print(f"   - Primeros 3 eventos:")
            for i, evento in enumerate(all_metadata[:3]):
                print(f"     {i+1}. {evento.get('evento_tipo')} - Spool: {evento.get('tag_spool')} - Worker: {evento.get('worker_nombre')}")
        else:
            print(f"   - ⚠️ La hoja Metadata está vacía (sin eventos)")

    except Exception as e:
        print(f"❌ La hoja '{config.HOJA_METADATA_NOMBRE}' NO EXISTE")
        print(f"   Error: {str(e)}")
        metadata_existe = False

    print()

    # CAUSA 2: Verificar columna AJ (fecha_materiales) en Operaciones
    print("📅 CAUSA 2: Verificando columna AJ (fecha_materiales) en 'Operaciones'...")
    try:
        operaciones_sheet = spreadsheet.worksheet(config.HOJA_OPERACIONES_NOMBRE)
        all_data = operaciones_sheet.get_all_values()

        # Columna AJ = índice 35 (fecha_materiales / BA)
        # Columna AK = índice 36 (fecha_armado / BB)
        col_index_aj = 35  # Columna AJ (fecha_materiales)
        col_index_ak = 36  # Columna AK (fecha_armado)

        spools_validos_iniciar_arm = 0  # BA llena Y BB vacía
        spools_con_fecha_materiales = 0
        spools_con_fecha_armado = 0
        ejemplos_validos = []
        ejemplos_invalidos = []

        # Saltar header (fila 0)
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) > col_index_ak:
                fecha_materiales = row[col_index_aj].strip() if len(row) > col_index_aj else ""
                fecha_armado = row[col_index_ak].strip()
                tag_spool = row[6].strip() if len(row) > 6 else f"Row {i}"  # Columna G = índice 6

                # Contar spools con fecha_materiales
                if fecha_materiales:
                    spools_con_fecha_materiales += 1

                # Contar spools con fecha_armado
                if fecha_armado:
                    spools_con_fecha_armado += 1

                # Validar condición completa: BA llena Y BB vacía
                if fecha_materiales and not fecha_armado:
                    spools_validos_iniciar_arm += 1
                    if len(ejemplos_validos) < 3:
                        ejemplos_validos.append(f"{tag_spool} (BA: {fecha_materiales}, BB: vacío)")
                elif fecha_materiales and fecha_armado:
                    # Este es el problema: ya tiene fecha_armado (BB llena)
                    if len(ejemplos_invalidos) < 3:
                        ejemplos_invalidos.append(f"{tag_spool} (BA: {fecha_materiales}, BB: {fecha_armado})")

        print(f"✅ Análisis de columnas BA (fecha_materiales) y BB (fecha_armado):")
        print(f"   - Spools CON fecha_materiales (BA llena): {spools_con_fecha_materiales}")
        print(f"   - Spools CON fecha_armado (BB llena): {spools_con_fecha_armado}")
        print()
        print(f"   🎯 Spools VÁLIDOS para INICIAR ARM (BA llena Y BB vacía): {spools_validos_iniciar_arm}")

        if ejemplos_validos:
            print(f"      Ejemplos de spools válidos:")
            for ejemplo in ejemplos_validos:
                print(f"        ✅ {ejemplo}")

        if ejemplos_invalidos:
            print()
            print(f"      Ejemplos de spools NO válidos (BB ya llena):")
            for ejemplo in ejemplos_invalidos:
                print(f"        ❌ {ejemplo}")

        if spools_validos_iniciar_arm == 0:
            print()
            print(f"   ❌ PROBLEMA ENCONTRADO:")
            print(f"      Todos los spools con fecha_materiales (BA) YA tienen fecha_armado (BB)")
            print(f"      → El ARM ya fue completado anteriormente")
            print(f"      → NO aparecerán en INICIAR ARM")
            print(f"      → Solución: Usar COMPLETAR ARM o limpiar columna BB para spools pendientes")

    except Exception as e:
        print(f"❌ Error al verificar columna AJ: {str(e)}")

    print()

    # CAUSA 3: Verificar eventos INICIAR_ARM en Metadata
    if metadata_existe:
        print("🔄 CAUSA 3: Verificando eventos INICIAR_ARM en Metadata...")
        try:
            sheet = spreadsheet.worksheet(config.HOJA_METADATA_NOMBRE)
            all_metadata = sheet.get_all_records()

            # Filtrar eventos INICIAR_ARM
            eventos_iniciar_arm = [
                e for e in all_metadata
                if e.get('evento_tipo') == 'INICIAR_ARM'
            ]

            # Filtrar eventos COMPLETAR_ARM
            eventos_completar_arm = [
                e for e in all_metadata
                if e.get('evento_tipo') == 'COMPLETAR_ARM'
            ]

            print(f"✅ Análisis de eventos ARM:")
            print(f"   - INICIAR_ARM: {len(eventos_iniciar_arm)} eventos")
            print(f"   - COMPLETAR_ARM: {len(eventos_completar_arm)} eventos")

            if len(eventos_iniciar_arm) > 0:
                # Mostrar spools con INICIAR_ARM
                spools_iniciados = set(e.get('tag_spool') for e in eventos_iniciar_arm)
                spools_completados = set(e.get('tag_spool') for e in eventos_completar_arm)
                spools_en_progreso = spools_iniciados - spools_completados

                print(f"   - Spools EN PROGRESO (iniciados pero no completados): {len(spools_en_progreso)}")
                if spools_en_progreso:
                    print(f"     Ejemplos (primeros 5):")
                    for spool in list(spools_en_progreso)[:5]:
                        print(f"       • {spool}")

                if len(spools_en_progreso) > 0:
                    print(f"   ⚠️ Estos spools NO aparecerán en INICIAR ARM")
                    print(f"      → Debes usar COMPLETAR ARM para estos spools")

        except Exception as e:
            print(f"❌ Error al verificar eventos: {str(e)}")

    print()
    print("=" * 80)
    print("RESUMEN DEL DIAGNÓSTICO")
    print("=" * 80)
    print()

    if not metadata_existe:
        print("❌ PROBLEMA PRINCIPAL: La hoja 'Metadata' no existe")
        print("   SOLUCIÓN: Crear la hoja 'Metadata' con 10 columnas:")
        print("   A: id | B: timestamp | C: evento_tipo | D: tag_spool | E: worker_id")
        print("   F: worker_nombre | G: operacion | H: accion | I: fecha_operacion | J: metadata_json")
    else:
        print("✅ La arquitectura Event Sourcing está configurada correctamente")

if __name__ == "__main__":
    verificar_sheets()
