#!/usr/bin/env python3
"""
Script para verificar el estado real de TEST-02 en Google Sheets y Redis.

Propósito: Confirmar si el Error 400 PAUSAR es causado por estado inconsistente.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config import config
from backend.repositories.sheets_repository import SheetsRepository
from backend.services.redis_lock_service import RedisLockService
from backend.services.state_service import StateService
from backend.repositories.metadata_repository import MetadataRepository
import redis.asyncio as redis


async def main():

    print("=" * 80)
    print("INVESTIGACIÓN: Estado de TEST-02")
    print("=" * 80)
    print()

    # Initialize repositories
    sheets_repo = SheetsRepository(config)
    redis_client = redis.from_url(
        config.REDIS_URL,
        decode_responses=True
    )
    redis_lock_service = RedisLockService(redis_client, config)
    metadata_repo = MetadataRepository(config)
    state_service = StateService(sheets_repo, metadata_repo)

    try:
        # 1. Verificar estado en Google Sheets
        print("📊 PASO 1: Verificando Google Sheets")
        print("-" * 80)

        spool = sheets_repo.get_spool_by_tag("TEST-02")

        if not spool:
            print("❌ ERROR: Spool TEST-02 no encontrado en Google Sheets")
            return

        print(f"✅ Spool encontrado: {spool.tag_spool}")
        print()
        print("Campos relevantes:")
        print(f"  - Armador:         '{spool.armador}' (tipo: {type(spool.armador).__name__})")
        print(f"  - Soldador:        '{spool.soldador}' (tipo: {type(spool.soldador).__name__})")
        print(f"  - Ocupado_Por:     '{spool.ocupado_por}' (tipo: {type(spool.ocupado_por).__name__})")
        print(f"  - Fecha_Ocupacion: '{spool.fecha_ocupacion}'")
        print(f"  - Fecha_Armado:    '{spool.fecha_armado}'")
        print(f"  - Fecha_Soldadura: '{spool.fecha_soldadura}'")
        print(f"  - Estado_Detalle:  '{spool.estado_detalle}'")
        print(f"  - version:         '{spool.version}'")
        print()

        # 2. Verificar lock en Redis
        print("🔒 PASO 2: Verificando Redis Lock")
        print("-" * 80)

        lock_key = f"spool:{spool.tag_spool}:lock"
        lock_value = await redis_client.get(lock_key)

        if lock_value:
            print(f"✅ Lock EXISTE en Redis")
            print(f"  - Key:   {lock_key}")
            print(f"  - Value: {lock_value}")

            # Get TTL
            ttl = await redis_client.ttl(lock_key)
            if ttl > 0:
                minutes = ttl // 60
                seconds = ttl % 60
                print(f"  - TTL:   {ttl} segundos ({minutes}m {seconds}s restantes)")
            else:
                print(f"  - TTL:   {ttl} (sin expiración o error)")

            # Get owner
            lock_owner = await redis_lock_service.get_lock_owner(spool.tag_spool)
            if lock_owner:
                owner_id, token = lock_owner
                print(f"  - Owner: Worker {owner_id}")
                print(f"  - Token: {token[:16]}...")
        else:
            print(f"❌ Lock NO EXISTE en Redis")
            print(f"  - Key buscada: {lock_key}")

        print()

        # 3. Hydrate ARM state machine y verificar estado
        print("🤖 PASO 3: Hydratando ARM State Machine")
        print("-" * 80)

        arm_machine = await state_service._hydrate_arm_machine(spool)
        arm_state = arm_machine.get_state_id()

        print(f"Estado hydratado: {arm_state}")
        print()
        print("Lógica de hydration aplicada:")

        if spool.fecha_armado:
            print("  ✓ spool.fecha_armado existe → Estado: COMPLETADO")
        elif spool.armador:
            print(f"  ✓ spool.armador existe ('{spool.armador}')")
            if spool.ocupado_por is None or spool.ocupado_por == "":
                print(f"  ✓ spool.ocupado_por is None/empty → Estado: PAUSADO")
            else:
                print(f"  ✓ spool.ocupado_por exists ('{spool.ocupado_por}') → Estado: EN_PROGRESO")
        elif spool.ocupado_por and spool.ocupado_por != "":
            print(f"  ✓ EDGE CASE: spool.ocupado_por='{spool.ocupado_por}' but armador=None")
            print(f"  ✓ Fix ac64c55 should hydrate to EN_PROGRESO")
        else:
            print("  ✓ armador=None AND ocupado_por=None/empty → Estado: PENDIENTE")

        print()

        # 4. Analizar inconsistencias
        print("🔍 PASO 4: Análisis de Consistencia")
        print("-" * 80)

        inconsistencies = []

        # Check Redis vs Sheets
        if lock_value and (not spool.ocupado_por or spool.ocupado_por == ""):
            inconsistencies.append(
                "❌ INCONSISTENCIA: Lock existe en Redis pero Ocupado_Por está vacío en Sheets"
            )

        if not lock_value and spool.ocupado_por and spool.ocupado_por != "":
            inconsistencies.append(
                f"❌ INCONSISTENCIA: Lock NO existe en Redis pero Ocupado_Por='{spool.ocupado_por}' en Sheets"
            )

        # Check Armador vs Ocupado_Por
        if spool.armador and (not spool.ocupado_por or spool.ocupado_por == ""):
            inconsistencies.append(
                f"⚠️ Estado válido pero raro: Armador='{spool.armador}' pero Ocupado_Por vacío (spool PAUSADO)"
            )

        if (not spool.armador or spool.armador == "") and spool.ocupado_por and spool.ocupado_por != "":
            inconsistencies.append(
                f"❌ EDGE CASE ac64c55: Ocupado_Por='{spool.ocupado_por}' pero Armador vacío (TOMAR parcialmente fallido)"
            )

        # Check state machine vs expected
        if arm_state == "pendiente" and (spool.armador or spool.ocupado_por):
            inconsistencies.append(
                f"❌ INCONSISTENCIA CRÍTICA: State machine hydrated to PENDIENTE pero spool tiene datos (armador='{spool.armador}', ocupado_por='{spool.ocupado_por}')"
            )

        if inconsistencies:
            print("INCONSISTENCIAS DETECTADAS:")
            print()
            for inc in inconsistencies:
                print(f"  {inc}")
        else:
            print("✅ Estado CONSISTENTE - No se detectaron inconsistencias")

        print()

        # 5. Simular PAUSAR validation
        print("🧪 PASO 5: Simulando Validación de PAUSAR")
        print("-" * 80)

        print(f"Estado actual hydrated: '{arm_state}'")
        print(f"Validación en StateService.pausar() línea 296:")
        print(f"  if current_arm_state != 'en_progreso':")
        print()

        if arm_state != "en_progreso":
            print(f"❌ PAUSAR FALLARÍA con Error 400:")
            print(f"   \"Cannot PAUSAR ARM from state '{arm_state}'.\"")
            print(f"   \"PAUSAR is only allowed from 'en_progreso' state.\"")
            print()
            print("✅ CONFIRMADO: Este es el error que vemos en producción")
        else:
            print(f"✅ PAUSAR PASARÍA la validación (estado correcto)")

        print()

        # 6. Conclusión
        print("=" * 80)
        print("CONCLUSIÓN")
        print("=" * 80)
        print()

        if arm_state == "pendiente":
            print("🎯 HIPÓTESIS CONFIRMADA:")
            print()
            print("El Error 400 'Cannot PAUSAR ARM from state pendiente' es causado por:")
            print()

            if not spool.armador and not spool.ocupado_por:
                print("1. Spool en estado PENDIENTE limpio (nunca fue tomado O fue completamente limpiado)")
                print("2. Usuario intenta PAUSAR un spool que no está ocupado")
                print()
                print("CAUSA RAÍZ PROBABLE:")
                print("  - TOMAR nunca ejecutó exitosamente")
                print("  - O TOMAR + COMPLETAR ya ejecutaron (spool disponible de nuevo)")
                print("  - O Rollback limpió todo correctamente")

            elif not spool.armador and spool.ocupado_por:
                print("1. EDGE CASE: Ocupado_Por existe pero Armador no")
                print("2. Fix ac64c55 debería hydrate a EN_PROGRESO pero NO lo hace")
                print()
                print("CAUSA RAÍZ PROBABLE:")
                print("  - TOMAR falló parcialmente (escribió Ocupado_Por, no Armador)")
                print("  - Fix ac64c55 implementado pero NO funciona correctamente")
                print()
                print("ACCIÓN REQUERIDA:")
                print("  - Revisar por qué fix ac64c55 no está funcionando")
                print("  - Verificar si activate_initial_state() está reseteando el estado")

            elif spool.armador and not spool.ocupado_por:
                print("1. Spool en estado PAUSADO (Armador existe, Ocupado_Por vacío)")
                print("2. Pero state machine hydrated a PENDIENTE (no PAUSADO)")
                print()
                print("CAUSA RAÍZ PROBABLE:")
                print("  - Bug en lógica de hydration (líneas 464-468)")
                print("  - Condición elif spool.armador no se está evaluando correctamente")

        else:
            print(f"Estado hydrated: {arm_state}")
            print()
            if arm_state == "en_progreso":
                print("✅ Estado correcto - PAUSAR debería funcionar")
            else:
                print(f"⚠️ Estado inesperado: {arm_state}")

        print()

    except Exception as e:
        print(f"❌ ERROR durante investigación: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await redis_client.close()
        print()
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
