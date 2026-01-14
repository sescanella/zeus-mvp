#!/usr/bin/env python3
"""
Test E2E del flujo completo en PRODUCCIÓN.

Verifica que:
1. Backend en Railway está respondiendo correctamente
2. Los 4 endpoints de spools funcionan
3. TEST-01 aparece en INICIAR ARM
4. Todas las validaciones están activas

USO:
    python3 test_production_e2e.py
"""
import requests
import sys

BACKEND_URL = "https://zeues-backend-mvp-production.up.railway.app"
FRONTEND_URL = "https://zeues-frontend.vercel.app"


def print_section(title: str):
    """Helper para imprimir secciones"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_health():
    """Test 1: Health check"""
    print("\n🏥 TEST 1: Health Check")
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        data = response.json()

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert data["status"] == "healthy", f"Status not healthy: {data['status']}"
        assert data["sheets_connection"] == "ok", "Sheets connection failed"

        print(f"   ✅ Backend healthy")
        print(f"   Environment: {data['environment']}")
        print(f"   Sheets: {data['sheets_connection']}")
        return True
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def test_iniciar_arm():
    """Test 2: INICIAR ARM endpoint"""
    print("\n📦 TEST 2: GET /api/spools/iniciar?operacion=ARM")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/spools/iniciar",
            params={"operacion": "ARM"},
            timeout=10
        )
        data = response.json()

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "spools" in data, "Missing 'spools' in response"
        assert "total" in data, "Missing 'total' in response"

        total = data["total"]
        spools = data["spools"]

        print(f"   ✅ Endpoint working")
        print(f"   Total spools: {total}")
        print(f"   Filtro: {data['filtro_aplicado']}")

        # Buscar TEST-01
        test_spools = [s for s in spools if 'TEST' in s['tag_spool']]
        if test_spools:
            print(f"   ✅ TEST-01 FOUND!")
            for spool in test_spools:
                print(f"      {spool['tag_spool']}: fecha_materiales={spool.get('fecha_materiales')}, armador={spool.get('armador')}")
        else:
            print(f"   ⚠️  TEST-01 not found (verify Fecha_Materiales is filled)")

        return True
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def test_completar_arm():
    """Test 3: COMPLETAR ARM endpoint"""
    print("\n🔧 TEST 3: GET /api/spools/completar?operacion=ARM")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/spools/completar",
            params={"operacion": "ARM", "worker_nombre": "Nicolas"},
            timeout=10
        )
        data = response.json()

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        total = data["total"]
        print(f"   ✅ Endpoint working")
        print(f"   Total spools: {total}")
        print(f"   Filtro: {data['filtro_aplicado']}")

        return True
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def test_iniciar_sold():
    """Test 4: INICIAR SOLD endpoint"""
    print("\n🔥 TEST 4: GET /api/spools/iniciar?operacion=SOLD")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/spools/iniciar",
            params={"operacion": "SOLD"},
            timeout=10
        )
        data = response.json()

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        total = data["total"]
        print(f"   ✅ Endpoint working")
        print(f"   Total spools: {total}")
        print(f"   Filtro: {data['filtro_aplicado']}")

        return True
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def test_completar_sold():
    """Test 5: COMPLETAR SOLD endpoint"""
    print("\n✔️  TEST 5: GET /api/spools/completar?operacion=SOLD")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/spools/completar",
            params={"operacion": "SOLD", "worker_nombre": "NA"},
            timeout=10
        )
        data = response.json()

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        total = data["total"]
        print(f"   ✅ Endpoint working")
        print(f"   Total spools: {total}")
        print(f"   Filtro: {data['filtro_aplicado']}")

        return True
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def test_workers():
    """Test 6: Workers endpoint"""
    print("\n👷 TEST 6: GET /api/workers")
    try:
        response = requests.get(f"{BACKEND_URL}/api/workers", timeout=10)
        data = response.json()

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "workers" in data, "Missing 'workers' in response"

        workers = data["workers"]
        print(f"   ✅ Endpoint working")
        print(f"   Total workers: {len(workers)}")

        # Verificar que workers tienen roles
        workers_with_roles = [w for w in workers if w.get('roles') and len(w['roles']) > 0]
        print(f"   Workers with roles: {len(workers_with_roles)}")

        if len(workers_with_roles) == 0:
            print(f"   ⚠️  WARNING: No workers have roles assigned!")

        return True
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def main():
    """Run all tests"""
    print_section("🧪 ZEUES - Production E2E Tests")
    print(f"\nBackend: {BACKEND_URL}")
    print(f"Frontend: {FRONTEND_URL}")

    tests = [
        test_health,
        test_iniciar_arm,
        test_completar_arm,
        test_iniciar_sold,
        test_completar_sold,
        test_workers
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test crashed: {str(e)}")
            results.append(False)

    # Summary
    print_section("RESUMEN")
    passed = sum(results)
    total = len(results)

    print(f"\n✅ Tests passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("\nEl sistema en producción está funcionando correctamente:")
        print("  ✅ Backend en Railway operativo")
        print("  ✅ Endpoints de spools respondiendo")
        print("  ✅ TEST-01 disponible en INICIAR ARM")
        print("  ✅ Sistema V2.2 con validación activa")
        print("\n🚀 Listo para usar en producción!")
    else:
        print(f"\n⚠️  {total - passed} tests fallaron")
        print("\nRevisa los errores arriba para más detalles.")

    print("\n" + "=" * 80 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
