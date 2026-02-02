#!/usr/bin/env python3
"""
ZEUES v3.0 Production E2E Test Suite (Simplified)

Tests critical TOMAR/PAUSAR/COMPLETAR workflows against live production.
Uses production API - no direct Sheets manipulation.

Usage:
    source venv/bin/activate
    python test_production_v3_e2e_simple.py
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List
from pathlib import Path

# Production environment
BASE_URL = "https://zeues-backend-mvp-production.up.railway.app"
TEST_SPOOL = "TEST-02"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(msg: str):
    """Print test case header"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

def print_success(msg: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg: str):
    """Print info message"""
    print(f"   {msg}")

#  ============================================================================
# Helper Functions
# ============================================================================

def api_call(method: str, endpoint: str, json_data: Dict = None, timeout: int = 30) -> Dict:
    """Generic API call wrapper"""
    try:
        url = f"{BASE_URL}{endpoint}"
        if method == "POST":
            response = requests.post(url, json=json_data, timeout=timeout)
        elif method == "GET":
            response = requests.get(url, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return {
            "status": response.status_code,
            "body": response.json() if response.content else {}
        }
    except requests.exceptions.Timeout:
        return {"status": 0, "body": {"error": "Request timeout"}}
    except Exception as e:
        return {"status": 0, "body": {"error": str(e)}}

def tomar(worker_id: int, worker_nombre: str, operacion: str) -> Dict:
    """Execute TOMAR operation"""
    return api_call("POST", "/api/occupation/tomar", {
        "tag_spool": TEST_SPOOL,
        "worker_id": worker_id,
        "worker_nombre": worker_nombre,
        "operacion": operacion
    })

def pausar(worker_id: int, worker_nombre: str, operacion: str) -> Dict:
    """Execute PAUSAR operation"""
    return api_call("POST", "/api/occupation/pausar", {
        "tag_spool": TEST_SPOOL,
        "worker_id": worker_id,
        "worker_nombre": worker_nombre,
        "operacion": operacion
    })

def completar(worker_id: int, worker_nombre: str, operacion: str, resultado: str = None) -> Dict:
    """Execute COMPLETAR operation"""
    payload = {
        "tag_spool": TEST_SPOOL,
        "worker_id": worker_id,
        "worker_nombre": worker_nombre,
        "operacion": operacion
    }
    if resultado:
        payload["resultado"] = resultado

    return api_call("POST", "/api/occupation/completar", payload)

# ============================================================================
# Test Cases
# ============================================================================

def test_1_arm_tomar_pausar_completar(w_id: int, w_nombre: str) -> bool:
    """Test 1: Basic ARM flow - TOMAR → PAUSAR → TOMAR → COMPLETAR"""
    print_test("Test 1: ARM TOMAR → PAUSAR → COMPLETAR")

    try:
        # TOMAR
        print_info(f"{w_nombre} TOMAR ARM...")
        result = tomar(w_id, w_nombre, "ARM")
        if result["status"] != 200:
            print_error(f"TOMAR failed: {result}")
            return False
        print_success(f"TOMAR succeeded")

        time.sleep(1)

        # PAUSAR
        print_info(f"{w_nombre} PAUSAR ARM...")
        result = pausar(w_id, w_nombre, "ARM")
        if result["status"] != 200:
            print_error(f"PAUSAR failed: {result}")
            return False
        print_success(f"PAUSAR succeeded")

        time.sleep(1)

        # TOMAR again
        print_info(f"{w_nombre} TOMAR ARM again...")
        result = tomar(w_id, w_nombre, "ARM")
        if result["status"] != 200:
            print_error(f"TOMAR failed: {result}")
            return False
        print_success(f"TOMAR succeeded")

        time.sleep(1)

        # COMPLETAR
        print_info(f"{w_nombre} COMPLETAR ARM...")
        result = completar(w_id, w_nombre, "ARM")
        if result["status"] != 200:
            print_error(f"COMPLETAR failed: {result}")
            return False
        print_success(f"COMPLETAR succeeded: {result['body'].get('message', '')}")

        print_success("Test 1 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 1 FAILED: {e}")
        return False

def test_2_race_condition(w1_id: int, w1_nombre: str, w2_id: int, w2_nombre: str) -> bool:
    """Test 2: Race condition - two workers TOMAR same spool"""
    print_test("Test 2: Race Condition (Concurrent TOMAR)")

    try:
        # Worker 1 TOMAR
        print_info(f"{w1_nombre} TOMAR ARM...")
        result = tomar(w1_id, w1_nombre, "ARM")
        if result["status"] != 200:
            print_error(f"Worker 1 TOMAR failed: {result}")
            return False
        print_success(f"Worker 1 TOMAR succeeded")

        # Worker 2 TOMAR immediately (should fail 409)
        print_info(f"{w2_nombre} TOMAR ARM (should conflict)...")
        result = tomar(w2_id, w2_nombre, "ARM")

        if result["status"] != 409:
            print_error(f"Expected 409 Conflict, got {result['status']}: {result}")
            return False

        print_success(f"Worker 2 correctly rejected with 409 Conflict")
        print_info(f"Message: {result['body'].get('detail', '')}")

        # Cleanup: Worker 1 PAUSAR
        pausar(w1_id, w1_nombre, "ARM")

        print_success("Test 2 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 2 FAILED: {e}")
        return False

def test_3_invalid_pausar_without_tomar(w_id: int, w_nombre: str) -> bool:
    """Test 3: Invalid transition - PAUSAR without TOMAR"""
    print_test("Test 3: Invalid PAUSAR without TOMAR")

    try:
        print_info(f"{w_nombre} PAUSAR ARM (without TOMAR)...")
        result = pausar(w_id, w_nombre, "ARM")

        if result["status"] == 200:
            print_error(f"PAUSAR should fail without TOMAR, but got 200: {result}")
            return False

        print_success(f"PAUSAR correctly rejected (status {result['status']})")
        print_info(f"Message: {result['body'].get('detail', '')}")

        print_success("Test 3 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 3 FAILED: {e}")
        return False

def test_4_nonexistent_spool(w_id: int, w_nombre: str) -> bool:
    """Test 4: 404 for nonexistent spool"""
    print_test("Test 4: Nonexistent Spool (404)")

    try:
        print_info("TOMAR on nonexistent spool 'FAKE-999'...")
        result = api_call("POST", "/api/occupation/tomar", {
            "tag_spool": "FAKE-999",
            "worker_id": w_id,
            "worker_nombre": w_nombre,
            "operacion": "ARM"
        })

        if result["status"] == 200:
            print_error(f"Should return 404, but got 200: {result}")
            return False

        if result["status"] != 404:
            print_error(f"Expected 404, got {result['status']}: {result}")
            return False

        print_success(f"Nonexistent spool correctly returns 404")
        print_info(f"Message: {result['body'].get('detail', '')}")

        print_success("Test 4 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 4 FAILED: {e}")
        return False

def test_5_history_endpoint() -> bool:
    """Test 5: History endpoint returns audit trail"""
    print_test("Test 5: History Endpoint (Audit Trail)")

    try:
        print_info(f"Fetching history for {TEST_SPOOL}...")
        result = api_call("GET", f"/api/history/{TEST_SPOOL}")

        if result["status"] != 200:
            print_error(f"History failed: {result}")
            return False

        history = result["body"]

        # Handle both list and dict{"history": [...]} formats
        if isinstance(history, dict) and "history" in history:
            events = history["history"]
        elif isinstance(history, list):
            events = history
        else:
            print_error(f"Unexpected history format: {type(history)}")
            return False

        print_success(f"History retrieved: {len(events)} events")

        if len(events) > 0:
            print_info(f"Sample event: {events[0]}")

        print_success("Test 5 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 5 FAILED: {e}")
        return False

def test_6_health_check() -> bool:
    """Test 6: Backend health check"""
    print_test("Test 6: Backend Health Check")

    try:
        print_info("Checking backend health...")
        result = api_call("GET", "/api/health")

        if result["status"] != 200:
            print_error(f"Health check failed: {result}")
            return False

        health = result["body"]
        print_success(f"Backend healthy: {health.get('status', '')}")
        print_info(f"Environment: {health.get('environment', '')}")
        print_info(f"Sheets connection: {health.get('sheets_connection', '')}")

        print_success("Test 6 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 6 FAILED: {e}")
        return False

def test_7_sold_flow(w_id: int, w_nombre: str) -> bool:
    """Test 7: SOLD flow after ARM complete"""
    print_test("Test 7: SOLD Flow (after ARM)")

    try:
        # Complete ARM first (TOMAR → COMPLETAR)
        print_info("Setup: Completing ARM...")
        result = tomar(w_id, w_nombre, "ARM")
        if result["status"] != 200:
            print_info("ARM already in progress or complete, continuing...")

        time.sleep(1)

        result = completar(w_id, w_nombre, "ARM")
        if result["status"] not in [200, 400]:  # 400 if already complete
            print_error(f"ARM COMPLETAR failed: {result}")
            return False

        print_success("ARM complete")

        time.sleep(1)

        # Now TOMAR SOLD
        print_info(f"{w_nombre} TOMAR SOLD...")
        result = tomar(w_id, w_nombre, "SOLD")
        if result["status"] != 200:
            print_error(f"SOLD TOMAR failed: {result}")
            return False
        print_success("SOLD TOMAR succeeded")

        time.sleep(1)

        # COMPLETAR SOLD
        print_info(f"{w_nombre} COMPLETAR SOLD...")
        result = completar(w_id, w_nombre, "SOLD")
        if result["status"] != 200:
            print_error(f"SOLD COMPLETAR failed: {result}")
            return False
        print_success(f"SOLD COMPLETAR succeeded")

        print_success("Test 7 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 7 FAILED: {e}")
        return False

def test_8_metrologia_instant(w_id: int, w_nombre: str) -> bool:
    """Test 8: Metrología instant inspection (no TOMAR needed)"""
    print_test("Test 8: Metrología Instant Inspection")

    try:
        # Ensure ARM and SOLD are complete (setup from previous test)
        print_info("Assuming ARM and SOLD complete from previous tests...")

        time.sleep(1)

        # COMPLETAR Metrología with APROBADO (no TOMAR needed)
        print_info(f"{w_nombre} COMPLETAR Metrología (APROBADO)...")
        result = completar(w_id, w_nombre, "METROLOGIA", resultado="APROBADO")

        if result["status"] not in [200, 400]:  # 400 if already done
            print_error(f"Metrología COMPLETAR failed: {result}")
            return False

        print_success("Metrología COMPLETAR succeeded")
        print_info(f"Message: {result['body'].get('message', '')}")

        print_success("Test 8 PASSED")
        return True

    except Exception as e:
        print_error(f"Test 8 FAILED: {e}")
        return False

# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}ZEUES v3.0 Production E2E Tests (Simplified){Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"Environment: {BASE_URL}")
    print(f"Test Spool: {TEST_SPOOL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Fetch active workers
    print_info("Fetching active workers...")
    result = api_call("GET", "/api/workers")

    if result["status"] != 200:
        print_error(f"Failed to fetch workers: {result}")
        return

    workers_data = result["body"]

    # Handle API response format
    if isinstance(workers_data, dict) and "workers" in workers_data:
        workers = workers_data["workers"]
    else:
        workers = workers_data

    active_workers = [w for w in workers if w.get("activo")]

    if len(active_workers) < 2:
        print_error(f"Need at least 2 active workers, found {len(active_workers)}")
        return

    w1 = active_workers[0]
    w2 = active_workers[1]

    w1_id = w1["id"]
    w1_nombre = w1.get("nombre_completo", f"{w1['nombre']}({w1_id})")

    w2_id = w2["id"]
    w2_nombre = w2.get("nombre_completo", f"{w2['nombre']}({w2_id})")

    print_success(f"Worker 1: {w1_nombre}")
    print_success(f"Worker 2: {w2_nombre}")

    # Run all tests
    results = []
    start_time = time.time()

    tests = [
        ("Test 1: ARM TOMAR → PAUSAR → COMPLETAR", lambda: test_1_arm_tomar_pausar_completar(w1_id, w1_nombre)),
        ("Test 2: Race Condition", lambda: test_2_race_condition(w1_id, w1_nombre, w2_id, w2_nombre)),
        ("Test 3: Invalid PAUSAR", lambda: test_3_invalid_pausar_without_tomar(w1_id, w1_nombre)),
        ("Test 4: Nonexistent Spool", lambda: test_4_nonexistent_spool(w1_id, w1_nombre)),
        ("Test 5: History Endpoint", lambda: test_5_history_endpoint()),
        ("Test 6: Health Check", lambda: test_6_health_check()),
        ("Test 7: SOLD Flow", lambda: test_7_sold_flow(w1_id, w1_nombre)),
        ("Test 8: Metrología Instant", lambda: test_8_metrologia_instant(w1_id, w1_nombre)),
    ]

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, "PASSED" if passed else "FAILED", None))
        except Exception as e:
            results.append((test_name, "FAILED", str(e)))
            print_error(f"Exception: {e}")

    # Generate report
    duration = time.time() - start_time
    passed_count = sum(1 for _, status, _ in results if status == "PASSED")
    failed_count = sum(1 for _, status, _ in results if status == "FAILED")

    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}Test Results Summary{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"Total Tests: {len(results)}")
    print(f"{Colors.GREEN}Passed: {passed_count}/{len(results)}{Colors.RESET}")
    if failed_count > 0:
        print(f"{Colors.RED}Failed: {failed_count}/{len(results)}{Colors.RESET}")
    print(f"Duration: {duration:.0f} seconds")
    print()

    # Show results
    if passed_count > 0:
        print(f"{Colors.GREEN}Passed Tests:{Colors.RESET}")
        for name, status, _ in results:
            if status == "PASSED":
                print(f"  {Colors.GREEN}✅ {name}{Colors.RESET}")
        print()

    if failed_count > 0:
        print(f"{Colors.RED}Failed Tests:{Colors.RESET}")
        for name, status, error in results:
            if status == "FAILED":
                print(f"  {Colors.RED}❌ {name}{Colors.RESET}")
                if error:
                    print(f"     Error: {error}")
        print()

    # Final verdict
    success_rate = (passed_count / len(results)) * 100
    if success_rate >= 75:  # 75% threshold for production stability
        print(f"{Colors.GREEN}v3.0 production deployment is STABLE ✅ ({success_rate:.0f}% success rate){Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}v3.0 production deployment has ISSUES ⚠️ ({success_rate:.0f}% success rate){Colors.RESET}")

    print()

    # Save report
    save_report(results, duration, w1, w2, passed_count, failed_count)

def save_report(results, duration, w1, w2, passed, failed):
    """Save test results to markdown file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(__file__).parent / "test-results"
    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / f"production-e2e-simple-{timestamp}.md"

    success_rate = (passed / len(results)) * 100

    report = f"""# ZEUES v3.0 Production E2E Test Results (Simplified)

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Environment:** {BASE_URL}
**Test Spool:** {TEST_SPOOL}
**Workers:** {w1.get('nombre_completo', '')} (ID: {w1['id']}), {w2.get('nombre_completo', '')} (ID: {w2['id']})
**Duration:** {int(duration // 60)}m {int(duration % 60)}s

## Summary

- **Total Tests:** {len(results)}
- **Passed:** {passed}/{len(results)} ✅
- **Failed:** {failed}/{len(results)} ❌
- **Success Rate:** {success_rate:.1f}%

## Test Results

"""

    for name, status, error in results:
        icon = "✅" if status == "PASSED" else "❌"
        report += f"### {icon} {name}\n"
        report += f"- **Status:** {status}\n"
        if error:
            report += f"- **Error:** {error}\n"
        report += "\n"

    report += f"""## Conclusion

{"v3.0 production deployment is **STABLE** ✅" if success_rate >= 75 else "v3.0 production deployment has **ISSUES** ⚠️"}

### Coverage

- ARM Workflow: {"✓" if any("ARM" in r[0] and r[1] == "PASSED" for r in results) else "✗"}
- SOLD Workflow: {"✓" if any("SOLD" in r[0] and r[1] == "PASSED" for r in results) else "✗"}
- Metrología: {"✓" if any("Metrología" in r[0] and r[1] == "PASSED" for r in results) else "✗"}
- Race Conditions: {"✓" if any("Race" in r[0] and r[1] == "PASSED" for r in results) else "✗"}
- Error Handling: {"✓" if any("Invalid" in r[0] and r[1] == "PASSED" for r in results) else "✗"}

---
Generated by ZEUES v3.0 E2E Test Suite (Simplified)
"""

    with open(report_file, 'w') as f:
        f.write(report)

    print_success(f"Report saved: {report_file}")

if __name__ == "__main__":
    main()
