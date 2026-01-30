#!/usr/bin/env python3
"""
Script simplificado para verificar el estado de TEST-02 directamente.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config import config
from backend.repositories.sheets_repository import SheetsRepository

print("=" * 80)
print("VERIFICACIÓN RÁPIDA: Estado de TEST-02 en Google Sheets")
print("=" * 80)
print()

# Initialize repository
sheets_repo = SheetsRepository(config)

# Get spool
spool = sheets_repo.get_spool_by_tag("TEST-02")

if not spool:
    print("❌ ERROR: Spool TEST-02 no encontrado")
    sys.exit(1)

print(f"✅ Spool encontrado: {spool.tag_spool}")
print()
print("📊 ESTADO ACTUAL EN GOOGLE SHEETS:")
print("-" * 80)
print(f"  Armador:           '{spool.armador}'")
print(f"  Soldador:          '{spool.soldador}'")
print(f"  Ocupado_Por:       '{spool.ocupado_por}'")
print(f"  Fecha_Ocupacion:   '{spool.fecha_ocupacion}'")
print(f"  Fecha_Armado:      '{spool.fecha_armado}'")
print(f"  Fecha_Soldadura:   '{spool.fecha_soldadura}'")
print(f"  Estado_Detalle:    '{spool.estado_detalle}'")
print(f"  version:           '{spool.version}'")
print()

# Analyze state based on hydration logic
print("🤖 ANÁLISIS DE ESTADO (Lógica de Hydration):")
print("-" * 80)

# Check what state would be hydrated
if spool.fecha_armado:
    estado_esperado = "COMPLETADO"
    razon = f"fecha_armado existe ({spool.fecha_armado})"
elif spool.armador:
    if spool.ocupado_por is None or spool.ocupado_por == "":
        estado_esperado = "PAUSADO"
        razon = f"armador='{spool.armador}' AND ocupado_por is empty"
    else:
        estado_esperado = "EN_PROGRESO"
        razon = f"armador='{spool.armador}' AND ocupado_por='{spool.ocupado_por}'"
elif spool.ocupado_por and spool.ocupado_por != "":
    estado_esperado = "EN_PROGRESO (EDGE CASE FIX)"
    razon = f"ocupado_por='{spool.ocupado_por}' but armador is None (fix ac64c55)"
else:
    estado_esperado = "PENDIENTE"
    razon = "armador is None AND ocupado_por is None/empty"

print(f"Estado que se hydrata: {estado_esperado}")
print(f"Razón: {razon}")
print()

# Check if PAUSAR would fail
print("🧪 SIMULACIÓN: ¿PAUSAR funcionaría?")
print("-" * 80)

if estado_esperado == "EN_PROGRESO" or estado_esperado == "EN_PROGRESO (EDGE CASE FIX)":
    print("✅ SÍ - PAUSAR debería funcionar")
    print(f"   Estado '{estado_esperado}' permite transición a PAUSAR")
else:
    print(f"❌ NO - PAUSAR FALLARÍA con Error 400")
    print(f"   Estado '{estado_esperado}' NO permite PAUSAR")
    print()
    print("   Error esperado:")
    print(f"   'Cannot PAUSAR ARM from state {estado_esperado.lower()}'")
    print(f"   'PAUSAR is only allowed from en_progreso state.'")

print()

# Detect inconsistencies
print("🔍 DETECCIÓN DE INCONSISTENCIAS:")
print("-" * 80)

inconsistencias = []

# Armador vs Ocupado_Por mismatch
if (not spool.armador or spool.armador == "") and spool.ocupado_por and spool.ocupado_por != "":
    inconsistencias.append({
        "tipo": "EDGE CASE ac64c55",
        "descripcion": f"Ocupado_Por='{spool.ocupado_por}' pero Armador=None",
        "causa": "TOMAR falló parcialmente (escribió Ocupado_Por pero no Armador)",
        "impacto": "Fix ac64c55 debería hydrate a EN_PROGRESO"
    })

if spool.armador and spool.armador != "" and (not spool.ocupado_por or spool.ocupado_por == ""):
    inconsistencias.append({
        "tipo": "Estado PAUSADO válido",
        "descripcion": f"Armador='{spool.armador}' pero Ocupado_Por vacío",
        "causa": "Spool fue pausado correctamente (PAUSAR exitoso anterior)",
        "impacto": "Estado esperado: PAUSADO"
    })

# Both empty but estado_detalle suggests occupation
if (not spool.armador or spool.armador == "") and (not spool.ocupado_por or spool.ocupado_por == ""):
    if spool.estado_detalle and "progreso" in spool.estado_detalle.lower():
        inconsistencias.append({
            "tipo": "INCONSISTENCIA Estado_Detalle",
            "descripcion": f"Estado_Detalle='{spool.estado_detalle}' pero datos vacíos",
            "causa": "Limpieza incompleta de datos",
            "impacto": "Estado real: PENDIENTE (limpio)"
        })

if inconsistencias:
    for inc in inconsistencias:
        print(f"⚠️ {inc['tipo']}:")
        print(f"   Descripción: {inc['descripcion']}")
        print(f"   Causa:       {inc['causa']}")
        print(f"   Impacto:     {inc['impacto']}")
        print()
else:
    print("✅ No se detectaron inconsistencias obvias")
    print()

# Summary
print("=" * 80)
print("RESUMEN:")
print("=" * 80)

if estado_esperado == "PENDIENTE":
    print()
    print("🎯 HIPÓTESIS CONFIRMADA:")
    print()
    print("  El spool TEST-02 está en estado PENDIENTE.")
    print()

    if not spool.armador and not spool.ocupado_por:
        print("  CAUSA MÁS PROBABLE:")
        print("  - El spool NUNCA fue tomado exitosamente, O")
        print("  - Fue completamente limpiado (COMPLETAR o rollback exitoso)")
        print()
        print("  ACCIÓN:")
        print("  - Usuario debe hacer TOMAR antes de PAUSAR")
        print("  - Si intentó TOMAR y falló, revisar logs del error")

elif estado_esperado == "PAUSADO":
    print()
    print("  El spool TEST-02 está en estado PAUSADO.")
    print()
    print("  PROBLEMA:")
    print("  - La validación de PAUSAR rechaza estado PAUSADO")
    print("  - Solo acepta EN_PROGRESO")
    print()
    print("  CAUSA:")
    print("  - Validación es demasiado estricta")
    print("  - PAUSAR debería ser idempotente (permitir PAUSAR → PAUSAR)")

elif estado_esperado == "EN_PROGRESO (EDGE CASE FIX)":
    print()
    print("  El spool TEST-02 debería hydrate a EN_PROGRESO (fix ac64c55).")
    print()
    print("  PERO si el error persiste:")
    print("  - El fix ac64c55 NO está funcionando correctamente")
    print("  - Posible causa: activate_initial_state() reseteando el estado")
    print("  - El fix 9e747d6 intentó resolver esto")

else:
    print()
    print(f"  Estado: {estado_esperado}")

print()
print("=" * 80)
