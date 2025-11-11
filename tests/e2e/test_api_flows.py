"""
End-to-end tests for ZEUES API - Complete workflow validation.

Tests validate complete HTTP → FastAPI → Services → Google Sheets flows,
with CRITICAL focus on ownership validation (403 FORBIDDEN).

Prerequisites:
- Google Sheets TESTING must be configured and accessible
- At least 2 active workers in Trabajadores sheet
- At least 1 spool with ARM=PENDIENTE (0.0, BA filled, BB empty)
- Tests may modify Google Sheets data (TESTING sheet only)

Run with:
    pytest tests/e2e/test_api_flows.py -v
    pytest tests/e2e/test_api_flows.py -v -k "flujo_completo or ownership"
    pytest tests/e2e/test_api_flows.py -v --cov=backend.routers
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Dict, Any, Tuple

from backend.main import app
from backend.models.enums import ActionType


# ============================================================================
# TEST CLIENT SETUP
# ============================================================================

client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def active_worker() -> str:
    """
    Returns nombre completo of an active worker for tests.

    Calls GET /api/workers and returns first active worker.
    Skips test if no workers available.

    Returns:
        str: Worker nombre completo (e.g., "Juan Pérez")

    Raises:
        pytest.skip: If no active workers found
    """
    response = client.get("/api/workers")
    assert response.status_code == 200, f"Workers endpoint failed: {response.text}"

    data = response.json()
    workers = data.get("workers", [])

    if len(workers) == 0:
        pytest.skip("No active workers available in Trabajadores sheet")

    first_worker = workers[0]
    nombre_completo = f"{first_worker['nombre']} {first_worker['apellido']}"

    return nombre_completo


@pytest.fixture
def spool_arm_pendiente() -> str:
    """
    Returns TAG_SPOOL of a spool eligible to start ARM.

    Calls GET /api/spools/iniciar?operacion=ARM and returns first spool.
    Skips test if no eligible spools available.

    Eligibility criteria:
    - ARM = PENDIENTE
    - Fecha_Materiales != null (BA filled)
    - Fecha_Armado = null (BB empty)

    Returns:
        str: TAG_SPOOL (e.g., "MK-1335-CW-25238-011")

    Raises:
        pytest.skip: If no eligible spools found
    """
    response = client.get("/api/spools/iniciar", params={"operacion": "ARM"})
    assert response.status_code == 200, f"Spools iniciar endpoint failed: {response.text}"

    data = response.json()
    spools = data.get("spools", [])

    if len(spools) == 0:
        pytest.skip(
            "No spools available for ARM iniciar. "
            "Ensure TESTING sheet has spools with ARM=PENDIENTE, BA filled, BB empty"
        )

    first_spool = spools[0]
    tag_spool = first_spool["tag_spool"]

    # Validate spool meets criteria
    assert first_spool["arm"] == "PENDIENTE", f"Spool {tag_spool} not PENDIENTE"
    assert first_spool["fecha_materiales"] is not None, f"Spool {tag_spool} BA empty"
    assert first_spool["fecha_armado"] is None, f"Spool {tag_spool} BB not empty"

    return tag_spool


@pytest.fixture
def two_different_workers() -> Tuple[str, str]:
    """
    Returns tuple of (worker1, worker2) for ownership violation tests.

    Calls GET /api/workers and returns first two distinct workers.
    Skips test if less than 2 workers available.

    This fixture is CRITICAL for test_ownership_violation_arm().

    Returns:
        tuple[str, str]: (worker1_nombre_completo, worker2_nombre_completo)

    Raises:
        pytest.skip: If less than 2 active workers found

    Example:
        ("Juan Pérez", "María González")
    """
    response = client.get("/api/workers")
    assert response.status_code == 200, f"Workers endpoint failed: {response.text}"

    data = response.json()
    workers = data.get("workers", [])

    if len(workers) < 2:
        pytest.skip(
            f"Need at least 2 active workers for ownership test. "
            f"Found only {len(workers)}. Add more workers to Trabajadores sheet."
        )

    worker1 = f"{workers[0]['nombre']} {workers[0]['apellido']}"
    worker2 = f"{workers[1]['nombre']} {workers[1]['apellido']}"

    # Ensure workers are different
    assert worker1 != worker2, "Workers must be distinct for ownership test"

    return (worker1, worker2)


def assert_error_response(
    response,
    expected_status: int,
    expected_error_code: str,
    message_contains: str = None
):
    """
    Helper function to assert error responses consistently.

    Validates:
    - HTTP status code
    - success = False
    - error code matches
    - message contains substring (optional)

    Args:
        response: TestClient response object
        expected_status: Expected HTTP status code
        expected_error_code: Expected error code string
        message_contains: Optional substring to check in message
    """
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["success"] is False, "Expected success=False in error response"
    assert data["error"] == expected_error_code, \
        f"Expected error={expected_error_code}, got {data.get('error')}"

    if message_contains:
        assert message_contains.lower() in data["message"].lower(), \
            f"Expected message to contain '{message_contains}', got: {data['message']}"


# ============================================================================
# PRIORITY 1 TESTS - MUST HAVE (CRÍTICOS)
# ============================================================================


def test_flujo_completo_iniciar_completar_arm(active_worker, spool_arm_pendiente):
    """
    Test CRÍTICO: Flujo completo INICIAR ARM → COMPLETAR ARM happy path.

    Validates complete workflow:
    1. GET eligible spool for iniciar
    2. POST iniciar-accion (worker assigns spool)
    3. Verify response (200 OK, valor_nuevo=0.1)
    4. GET spools to completar (verify spool appears in worker's list)
    5. POST completar-accion (worker completes work)
    6. Verify response (200 OK, valor_nuevo=1.0)

    This test validates:
    - Eligibility filtering works (INICIAR shows correct spools)
    - State transitions work (PENDIENTE → EN_PROGRESO → COMPLETADO)
    - Metadata updates work (BC written on iniciar, BB written on completar)
    - Ownership works (same worker can complete own spool)
    - Google Sheets updates persist

    Prerequisites:
    - At least 1 spool with ARM=PENDIENTE, BA filled, BB empty
    - At least 1 active worker

    Data modification:
    - Changes spool state from PENDIENTE → EN_PROGRESO → COMPLETADO
    - Writes worker nombre to BC
    - Writes current date to BB
    """
    worker_nombre = active_worker
    tag_spool = spool_arm_pendiente

    # ===== STEP 1: GET eligible spool =====
    response = client.get("/api/spools/iniciar", params={"operacion": "ARM"})
    assert response.status_code == 200
    data = response.json()
    spools = data["spools"]
    assert len(spools) > 0, "No spools available for iniciar"
    assert tag_spool in [s["tag_spool"] for s in spools]

    # ===== STEP 2: POST iniciar-accion =====
    iniciar_payload = {
        "worker_nombre": worker_nombre,
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/iniciar-accion", json=iniciar_payload)

    # ===== STEP 3: Verify iniciar response =====
    assert response.status_code == 200, f"Iniciar failed: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert "iniciada exitosamente" in data["message"].lower()

    action_data = data["data"]
    assert action_data["tag_spool"] == tag_spool
    assert action_data["operacion"] == "ARM"
    assert action_data["trabajador"] == worker_nombre
    assert action_data["valor_nuevo"] == 0.1  # EN_PROGRESO
    assert action_data["columna_actualizada"] == "V"

    metadata = action_data["metadata_actualizada"]
    assert metadata["armador"] == worker_nombre
    assert metadata["fecha_armado"] is None  # Not written yet

    # ===== STEP 4: GET spools to completar (verify appears) =====
    response = client.get(
        "/api/spools/completar",
        params={"operacion": "ARM", "worker_nombre": worker_nombre}
    )
    assert response.status_code == 200
    data = response.json()

    completar_spools = data["spools"]
    assert len(completar_spools) > 0, "Spool should appear in completar list"

    spool_found = False
    for spool in completar_spools:
        if spool["tag_spool"] == tag_spool:
            spool_found = True
            assert spool["arm"] == "EN_PROGRESO"
            assert spool["armador"] == worker_nombre
            break

    assert spool_found, f"Spool {tag_spool} not found in completar list"

    # ===== STEP 5: POST completar-accion =====
    completar_payload = {
        "worker_nombre": worker_nombre,
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/completar-accion", json=completar_payload)

    # ===== STEP 6: Verify completar response =====
    assert response.status_code == 200, f"Completar failed: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert "completada exitosamente" in data["message"].lower()

    action_data = data["data"]
    assert action_data["tag_spool"] == tag_spool
    assert action_data["operacion"] == "ARM"
    assert action_data["trabajador"] == worker_nombre
    assert action_data["valor_nuevo"] == 1.0  # COMPLETADO
    assert action_data["columna_actualizada"] == "V"

    metadata = action_data["metadata_actualizada"]
    assert metadata["fecha_armado"] is not None  # Now written
    # Validate date format DD/MM/YYYY
    fecha_armado = metadata["fecha_armado"]
    assert "/" in fecha_armado, f"Date format invalid: {fecha_armado}"


def test_ownership_violation_arm(two_different_workers, spool_arm_pendiente):
    """
    Test CRÍTICO: Validación ownership - Solo quien inició puede completar.

    This is THE MOST IMPORTANT SECURITY TEST in the entire system.
    Validates that the API prevents workers from completing each other's work,
    which is a CRITICAL compliance/audit requirement.

    Test flow:
    1. Worker1 starts ARM on spool X → 200 OK
    2. Worker2 (different) tries to complete ARM on spool X → 403 FORBIDDEN
    3. Verify error response contains correct error code and message
    4. Verify error data includes both worker names

    Expected behavior:
    - HTTP 403 FORBIDDEN
    - error = "NO_AUTORIZADO"
    - message contains "Solo {worker1} puede completar"
    - data includes: trabajador_esperado, trabajador_solicitante, operacion

    Business rule:
    Only the worker who started an action (nombre in BC/BE) can complete it.
    This prevents unauthorized work completion and maintains audit trail.

    Prerequisites:
    - At least 2 active workers (different names)
    - At least 1 spool with ARM=PENDIENTE, BA filled, BB empty

    Data modification:
    - Changes spool state from PENDIENTE → EN_PROGRESO (stays EN_PROGRESO)
    - Writes worker1 nombre to BC (remains worker1 after test)
    """
    worker1, worker2 = two_different_workers
    tag_spool = spool_arm_pendiente

    # ===== STEP 1: Worker1 starts ARM =====
    iniciar_payload = {
        "worker_nombre": worker1,
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/iniciar-accion", json=iniciar_payload)

    assert response.status_code == 200, f"Iniciar failed: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["data"]["valor_nuevo"] == 0.1  # EN_PROGRESO
    assert data["data"]["metadata_actualizada"]["armador"] == worker1

    # ===== STEP 2: Worker2 (DIFFERENT) tries to complete ARM =====
    completar_payload = {
        "worker_nombre": worker2,  # WRONG WORKER
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/completar-accion", json=completar_payload)

    # ===== STEP 3: Verify 403 FORBIDDEN =====
    assert response.status_code == 403, \
        f"Expected 403 FORBIDDEN, got {response.status_code}: {response.text}"

    data = response.json()

    # Validate error structure
    assert data["success"] is False, "Expected success=False"
    assert data["error"] == "NO_AUTORIZADO", \
        f"Expected error=NO_AUTORIZADO, got {data.get('error')}"

    # Validate error message
    message = data["message"]
    assert "solo" in message.lower(), "Message should contain 'solo'"
    assert worker1.lower() in message.lower(), \
        f"Message should mention worker who started ({worker1})"
    assert "puede completar" in message.lower(), \
        "Message should say 'puede completar'"

    # Validate error data
    error_data = data.get("data", {})
    assert error_data.get("tag_spool") == tag_spool
    assert error_data.get("trabajador_esperado") == worker1
    assert error_data.get("trabajador_solicitante") == worker2
    assert error_data.get("operacion") == "ARM"

    # ===== STEP 4: Verify spool still EN_PROGRESO (not completed) =====
    response = client.get(
        "/api/spools/completar",
        params={"operacion": "ARM", "worker_nombre": worker1}
    )
    assert response.status_code == 200
    data = response.json()

    # Spool should still be in worker1's completar list
    spools = data["spools"]
    spool_found = any(s["tag_spool"] == tag_spool for s in spools)
    assert spool_found, \
        f"Spool {tag_spool} should still be EN_PROGRESO for {worker1}"


def test_completar_accion_no_iniciada(active_worker, spool_arm_pendiente):
    """
    Test: Cannot complete an action that hasn't been started.

    Validates that attempting to complete a PENDIENTE spool
    returns 400 BAD REQUEST with error=OPERACION_NO_INICIADA.

    Business rule:
    Actions must follow sequence: PENDIENTE → INICIAR (EN_PROGRESO) → COMPLETAR
    Cannot skip INICIAR step.

    Test flow:
    1. GET eligible spool (ARM=PENDIENTE, not started)
    2. POST completar-accion directly (skip iniciar)
    3. Verify 400 BAD REQUEST
    4. Verify error = "OPERACION_NO_INICIADA"

    Prerequisites:
    - At least 1 spool with ARM=PENDIENTE, BA filled, BB empty
    - At least 1 active worker

    Data modification: None (action rejected)
    """
    worker_nombre = active_worker
    tag_spool = spool_arm_pendiente

    # ===== STEP 1: Verify spool is PENDIENTE =====
    response = client.get("/api/spools/iniciar", params={"operacion": "ARM"})
    data = response.json()
    spools = data["spools"]
    spool = next((s for s in spools if s["tag_spool"] == tag_spool), None)
    assert spool is not None, f"Spool {tag_spool} not found"
    assert spool["arm"] == "PENDIENTE"

    # ===== STEP 2: Try to complete without iniciar =====
    completar_payload = {
        "worker_nombre": worker_nombre,
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/completar-accion", json=completar_payload)

    # ===== STEP 3: Verify 400 BAD REQUEST =====
    assert_error_response(
        response,
        expected_status=400,
        expected_error_code="OPERACION_NO_INICIADA",
        message_contains="no ha sido iniciada"
    )


# ============================================================================
# PRIORITY 2 TESTS - SHOULD HAVE
# ============================================================================


def test_iniciar_accion_spool_no_encontrado(active_worker):
    """
    Test: 404 error when spool doesn't exist.

    Validates that attempting to start action on invalid tag_spool
    returns 404 NOT FOUND with error=SPOOL_NO_ENCONTRADO.

    Prerequisites:
    - At least 1 active worker

    Data modification: None
    """
    worker_nombre = active_worker

    iniciar_payload = {
        "worker_nombre": worker_nombre,
        "operacion": "ARM",
        "tag_spool": "INVALID-TAG-99999"
    }
    response = client.post("/api/iniciar-accion", json=iniciar_payload)

    assert_error_response(
        response,
        expected_status=404,
        expected_error_code="SPOOL_NO_ENCONTRADO",
        message_contains="no encontrado"
    )


def test_iniciar_accion_trabajador_no_encontrado(spool_arm_pendiente):
    """
    Test: 404 error when worker doesn't exist.

    Validates that attempting to start action with invalid worker_nombre
    returns 404 NOT FOUND with error=WORKER_NO_ENCONTRADO.

    Prerequisites:
    - At least 1 spool with ARM=PENDIENTE

    Data modification: None
    """
    tag_spool = spool_arm_pendiente

    iniciar_payload = {
        "worker_nombre": "INVALID WORKER NAME",
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/iniciar-accion", json=iniciar_payload)

    assert_error_response(
        response,
        expected_status=404,
        expected_error_code="WORKER_NO_ENCONTRADO",
        message_contains="no encontrado"
    )


def test_iniciar_accion_ya_iniciada(active_worker, spool_arm_pendiente):
    """
    Test: Cannot start same action twice.

    Validates that attempting to iniciar an action that's already EN_PROGRESO
    returns 400 BAD REQUEST with error=OPERACION_YA_INICIADA.

    Test flow:
    1. Worker starts ARM → 200 OK
    2. Worker tries to start ARM again → 400 BAD REQUEST

    Prerequisites:
    - At least 1 spool with ARM=PENDIENTE
    - At least 1 active worker

    Data modification:
    - Changes spool state from PENDIENTE → EN_PROGRESO (first call)
    """
    worker_nombre = active_worker
    tag_spool = spool_arm_pendiente

    # ===== STEP 1: First iniciar (should succeed) =====
    iniciar_payload = {
        "worker_nombre": worker_nombre,
        "operacion": "ARM",
        "tag_spool": tag_spool
    }
    response = client.post("/api/iniciar-accion", json=iniciar_payload)
    assert response.status_code == 200

    # ===== STEP 2: Second iniciar (should fail) =====
    response = client.post("/api/iniciar-accion", json=iniciar_payload)

    assert_error_response(
        response,
        expected_status=400,
        expected_error_code="OPERACION_YA_INICIADA",
        message_contains="está iniciada"
    )


# ============================================================================
# PRIORITY 3 TESTS - NICE TO HAVE
# ============================================================================


def test_health_check():
    """
    Test: Health check endpoint returns OK.

    Validates GET /api/health returns 200 with sheets_connection=ok.

    Prerequisites: None

    Data modification: None
    """
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["sheets_connection"] == "ok"
    assert "timestamp" in data
    assert "version" in data


def test_get_workers():
    """
    Test: Workers endpoint returns active workers.

    Validates GET /api/workers returns list with nombre, apellido, activo=True.

    Prerequisites: None (can handle empty list)

    Data modification: None
    """
    response = client.get("/api/workers")

    assert response.status_code == 200
    data = response.json()

    assert "workers" in data
    assert "total" in data
    assert data["total"] >= 0

    if data["total"] > 0:
        first_worker = data["workers"][0]
        assert "nombre" in first_worker
        assert "apellido" in first_worker
        assert first_worker["activo"] is True


def test_get_spools_iniciar_arm():
    """
    Test: Spools iniciar endpoint filters correctly.

    Validates GET /api/spools/iniciar?operacion=ARM returns only eligible spools.
    All returned spools should be PENDIENTE with BA filled and BB empty.

    Prerequisites: None (can handle empty list)

    Data modification: None
    """
    response = client.get("/api/spools/iniciar", params={"operacion": "ARM"})

    assert response.status_code == 200
    data = response.json()

    assert "spools" in data
    assert "total" in data
    assert "filtro_aplicado" in data

    # If spools exist, validate filtering
    if data["total"] > 0:
        for spool in data["spools"]:
            assert spool["arm"] == "PENDIENTE", \
                f"Spool {spool['tag_spool']} should be PENDIENTE, got {spool['arm']}"
            assert spool["fecha_materiales"] is not None, \
                f"Spool {spool['tag_spool']} BA should be filled"
            assert spool["fecha_armado"] is None, \
                f"Spool {spool['tag_spool']} BB should be empty"


def test_get_spools_iniciar_invalid_operation():
    """
    Test: 400 error when operation is invalid.

    Validates that invalid operacion value is rejected.

    Prerequisites: None

    Data modification: None
    """
    response = client.get("/api/spools/iniciar", params={"operacion": "INVALID"})

    # Should return 400 BAD REQUEST
    assert response.status_code == 400
    data = response.json()

    # HTTPException returns 'detail' field (FastAPI native format)
    assert "detail" in data
    assert "inválida" in data["detail"].lower() or "invalid" in data["detail"].lower()
