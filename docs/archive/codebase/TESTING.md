# Testing Patterns

**Analysis Date:** 2026-01-26

## Test Framework

**Backend Runner:**
- pytest (Python testing framework)
- Version: Latest in requirements.txt
- Config: Implicit (no pytest.ini, uses defaults with conftest.py)
- Default behavior: Discovers tests in `tests/` directory, runs all `test_*.py` files

**Frontend Runner:**
- Playwright (E2E testing framework)
- Version: `^1.56.1` (from zeues-frontend/package.json)
- Config: `zeues-frontend/playwright.config.ts`

**Assertion Libraries:**
- Backend: pytest built-in assertions with `assert` keyword
  - Also uses custom exception assertions: `with pytest.raises(CustomException):`
- Frontend: Playwright built-in assertions (`expect()`)

**Run Commands:**
```bash
# Backend - run all tests
pytest

# Backend - run with coverage
pytest --cov=backend

# Backend - run specific test file
pytest tests/unit/test_validation_service.py

# Backend - run single test
pytest tests/unit/test_validation_service.py::test_validar_puede_iniciar_arm_success -v

# Backend - run tests by category
pytest tests/unit/          # Unit tests only
pytest tests/e2e/           # E2E integration tests
pytest tests/unit/ -v --tb=short  # Verbose with short traceback

# Backend - list all tests without running
pytest --collect-only

# Frontend - run all E2E tests (headless)
cd zeues-frontend && npx playwright test

# Frontend - run with UI mode (interactive)
cd zeues-frontend && npx playwright test --ui

# Frontend - run in headed mode (see browser)
cd zeues-frontend && npx playwright test --headed

# Frontend - slow motion demo mode (2sec per action)
cd zeues-frontend && SLOW_MO=2000 npx playwright test --headed --workers=1 --max-failures=1

# Frontend - show test report
cd zeues-frontend && npx playwright show-report
```

## Test File Organization

**Location:**
- Backend unit tests: `tests/unit/test_*.py` (co-located with implementation, one test file per service)
- Backend E2E tests: `tests/e2e/test_*.py` (integration tests that hit real Google Sheets or TestClient)
- Frontend E2E tests: `zeues-frontend/e2e/*.spec.ts` (Playwright tests that navigate full UI)

**Naming:**
- Backend: `test_{module_name}.py` (e.g., `test_validation_service.py`, `test_action_service.py`)
- Backend test functions: `test_{function_name}_{scenario}` (e.g., `test_validar_puede_iniciar_arm_success`)
- Frontend: `{flow_name}.spec.ts` (e.g., `01-iniciar-arm.spec.ts`, `03-iniciar-sold.spec.ts`)

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures for all tests
├── unit/
│   ├── test_validation_service.py
│   ├── test_action_service.py
│   ├── test_action_service_batch.py
│   ├── test_worker_service.py
│   ├── test_role_service.py
│   └── ...
├── e2e/
│   └── test_api_flows.py    # Integration tests (HTTP → Services → Sheets)
└── __init__.py

zeues-frontend/
└── e2e/
    ├── 01-iniciar-arm.spec.ts
    ├── 03-iniciar-sold.spec.ts
    ├── 08-search-filter.spec.ts
    └── ...
```

## Test Structure

**Backend Test Suite Organization:**

```python
"""
Tests unitarios para ValidationService.

Prueba la lógica de validación de reglas de negocio sin dependencias externas.
Coverage objetivo: >95%
"""

import pytest
from backend.services.validation_service import ValidationService
from backend.models.spool import Spool
from backend.exceptions import OperacionYaIniciadaError

# ==================== FIXTURES ====================

@pytest.fixture
def mock_column_map_operaciones():
    """Fixture que retorna un column_map mockeado para la hoja Operaciones."""
    return {
        "tagspool": 6,
        "fechamateriales": 32,
        "fechaarmado": 33,
        "armador": 34,
        "fechasoldadura": 35,
        "soldador": 36,
    }

@pytest.fixture
def validation_service(mock_column_map_operaciones):
    """Fixture que retorna ValidationService configurado para tests."""
    return ValidationService(role_service=None)

# ==================== TEST CASES ====================

class TestValidarPuedeIniciarArm:
    """Suite de tests para validar INICIAR ARM."""

    def test_validar_puede_iniciar_arm_success(self, validation_service):
        """Test exitoso: ARM puede iniciarse."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            fecha_materiales="15-11-2025",
            armador=None,
            fecha_armado=None
        )
        # Should not raise exception
        validation_service.validar_puede_iniciar_arm(spool)

    def test_validar_puede_iniciar_arm_already_started(self, validation_service):
        """Test fallido: ARM ya iniciado."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            fecha_materiales="15-11-2025",
            armador="MR(93)",  # Already started
            fecha_armado=None
        )
        with pytest.raises(OperacionYaIniciadaError):
            validation_service.validar_puede_iniciar_arm(spool)

    def test_validar_puede_iniciar_arm_missing_materials(self, validation_service):
        """Test fallido: Fecha_Materiales no registrada."""
        spool = Spool(
            tag_spool="MK-1335-CW-25238-011",
            fecha_materiales=None,  # Missing
            armador=None,
            fecha_armado=None
        )
        with pytest.raises(DependenciasNoSatisfechasError):
            validation_service.validar_puede_iniciar_arm(spool)
```

**Patterns:**
- **Setup:** Fixtures provide mocked dependencies
  - Mock column maps: Normalize Sheets column names to indices
  - Mock repositories: Return domain objects without hitting Sheets
  - Mock services: Return controlled test data

- **Teardown:** pytest automatically cleans up fixtures after each test
  - No explicit teardown needed for mock objects

- **Assertion:** Use pytest assertions and custom exception checks
  - `assert condition` for boolean checks
  - `with pytest.raises(ExceptionType):` for exception validation
  - Custom assertions in exception messages

## Mocking

**Framework:** unittest.mock (built-in Python)

**Patterns:**
```python
from unittest.mock import MagicMock, patch

# Mock an entire service
mock_sheets_repo = MagicMock()
mock_sheets_repo.get_spool = MagicMock(return_value=Spool(...))

# Mock with side_effect for conditional returns
def find_spool_side_effect(tag_spool: str):
    if tag_spool == "MK-1335":
        return Spool(tag_spool=tag_spool, ...)
    return None

service.find_spool = MagicMock(side_effect=find_spool_side_effect)

# Patch at module level
@patch('backend.repositories.sheets_repository.gspread.authorize')
def test_with_patched_gspread(mock_authorize):
    mock_authorize.return_value = mock_client
```

**What to Mock:**
- Google Sheets access (SheetsRepository, gspread client)
- External dependencies not being tested
- Database calls or API calls not in scope

**What NOT to Mock:**
- Domain models (Spool, Worker, etc.) - use real instances
- Validation logic - test it, don't mock it
- Business rules - these are what we're testing
- Exception handling - test real exceptions

**Test Data Pattern (Mock Fixtures):**
```python
@pytest.fixture
def mock_spool_service():
    """SpoolService mockeado con spools de prueba."""
    service = MagicMock()

    def find_spool_side_effect(tag_spool: str):
        if tag_spool.startswith("MK-1335"):
            return Spool(
                tag_spool=tag_spool,
                fecha_materiales="15-11-2025",
                estado_armado=0.0,
                armador=None,
                fecha_armado=None
            )
        return None

    service.find_spool_by_tag = MagicMock(side_effect=find_spool_side_effect)
    return service
```

## Fixtures and Factories

**Test Data Patterns:**

Backend `conftest.py` provides reusable fixtures:
```python
@pytest.fixture
def mock_column_map_operaciones():
    """Normalized column names to indices for Operaciones sheet."""
    return {
        "tagspool": 6,
        "nv": 1,
        "fechamateriales": 32,
        "fechaarmado": 33,
        "armador": 34,
        "fechasoldadura": 35,
        "soldador": 36,
        "fechaqcmetrologia": 37,
    }

@pytest.fixture
def sheets_service_with_mock_map(mock_column_map_operaciones):
    """SheetsService configured with test column mapping."""
    service = SheetsService()
    service.column_map_operaciones = mock_column_map_operaciones
    return service
```

**Location:**
- Shared fixtures: `tests/conftest.py` (accessible to all tests)
- Test-specific fixtures: In individual test files with `@pytest.fixture` decorator
- Domain object builders: Use Pydantic model constructors directly

**Test Data Builders:**
```python
# Create Spool for testing
spool = Spool(
    tag_spool="MK-1335-CW-25238-011",
    fecha_materiales="15-11-2025",
    armador="MR(93)",
    fecha_armado=None
)

# Create Worker for testing
worker = Worker(
    id=93,
    nombre="Mauricio",
    apellido="Rodriguez",
    activo=True
)

# Create ActionRequest for testing
request = ActionRequest(
    worker_id=93,
    operacion=ActionType.ARM,
    tag_spool="MK-1335-CW-25238-011"
)
```

## Coverage

**Requirements:** None enforced (no CI check for coverage percentage)

**View Coverage:**
```bash
# Generate coverage report
pytest --cov=backend --cov-report=html

# View HTML report
open htmlcov/index.html
```

**Target areas for testing:**
- ValidationService: All validation methods (>95% coverage)
- ActionService: INICIAR/COMPLETAR/CANCELAR flows (>90% coverage)
- Exception handling: All custom exceptions (>95% coverage)
- Batch operations: Multi-spool processing (>85% coverage)
- Repository patterns: Data access layers (>80% coverage)

## Test Types

**Unit Tests:**
- Scope: Single service or function in isolation
- Mocks: All external dependencies (repositories, services)
- Location: `tests/unit/test_*.py`
- Examples:
  - `test_validation_service.py` - ValidationService without Google Sheets
  - `test_action_service.py` - ActionService with mocked repositories
  - `test_worker_service.py` - WorkerService logic isolation

- Key files tested:
  - `backend/services/validation_service.py` - Business rules validation
  - `backend/services/action_service.py` - Action orchestration
  - `backend/models/enums.py` - Enum conversions (sheets_value ↔ enum)
  - `backend/models/worker.py` - Worker computed fields (nombre_completo format)

**Integration Tests (Backend E2E):**
- Scope: Full HTTP request → Services → Google Sheets flow
- Mocks: Only Google Sheets (if needed for CI; typically skipped in CI)
- Location: `tests/e2e/test_api_flows.py`
- Uses: TestClient from FastAPI (FastAPI.testclient)
- Examples:
  - Test complete flow: Worker request → ActionService → Sheets update → Response
  - Ownership validation: Worker A can't complete Worker B's action
  - Batch operations: 10 spools processed simultaneously

**E2E Tests (Frontend):**
- Scope: Full user workflow through web UI
- Uses: Playwright for browser automation
- Location: `zeues-frontend/e2e/*.spec.ts`
- Examples:
  - `01-iniciar-arm.spec.ts` - Complete INICIAR ARM flow (P1-P6)
  - `03-iniciar-sold.spec.ts` - INICIAR SOLD flow
  - `08-search-filter.spec.ts` - Spool search/filter functionality

- Flow validation (from playwright.config.ts):
  ```typescript
  /* Timeout por test: 30 segundos (flujo completo < 30s) */
  timeout: 30 * 1000,

  /* Expect timeout: 5 segundos para assertions */
  expect: { timeout: 5000 }
  ```

## Common Patterns

**Async Testing (Backend - pytest):**
```python
# For async functions in FastAPI
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation in backend."""
    result = await async_function()
    assert result is not None

# Common: Use TestClient for sync HTTP requests
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
response = client.post("/api/iniciar-accion", json=payload)
assert response.status_code == 200
```

**Async Testing (Frontend - Playwright):**
```typescript
import { test, expect } from '@playwright/test';

test('debe completar el flujo INICIAR ARM exitosamente', async ({ page }) => {
  // Navigation is awaited
  await page.goto('/');

  // User interactions are awaited
  await page.getByRole('button', { name: /ARMADO/i }).click();

  // Assertions wait for conditions
  await expect(page).toHaveURL('/operacion');
});

// Steps for organizing complex flows
await test.step('P1 - Selección de Operación', async () => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: /ARMADO/i })).toBeVisible();
});
```

**Error Testing (Backend):**
```python
def test_validar_puede_completar_arm_not_started(self, validation_service):
    """Test exception when operation not started."""
    spool = Spool(
        tag_spool="MK-1335",
        armador=None,  # Not started
        fecha_armado=None
    )

    # Assertion using pytest.raises context manager
    with pytest.raises(OperacionNoIniciadaError) as exc_info:
        validation_service.validar_puede_completar_arm(
            spool,
            worker_nombre="MR(93)",
            worker_id=93
        )

    # Validate exception data
    assert exc_info.value.error_code == "OPERACION_NO_INICIADA"
    assert exc_info.value.data["tag_spool"] == "MK-1335"
```

**Error Testing (Frontend):**
```typescript
test('debe mostrar error cuando API falla', async ({ page }) => {
  await page.goto('/');

  // Mock API error response
  await page.route('/api/workers', route => {
    route.abort('failed');
  });

  // Verify error message appears
  await expect(page.getByText(/No se pudieron cargar/i)).toBeVisible();

  // Verify retry button available
  await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible();
});
```

**Batch Testing Pattern:**
```python
# From test_action_service_batch.py
def test_batch_iniciar_success(self, action_service, mock_spools):
    """Test successful batch INICIAR (all spools processed)."""
    request = BatchActionRequest(
        worker_id=93,
        operacion=ActionType.ARM,
        tag_spools=["MK-1335-001", "MK-1335-002", "MK-1335-003"]
    )

    response = action_service.batch_iniciar(request)

    assert response.success is True
    assert response.total == 3
    assert response.exitosos == 3
    assert response.fallidos == 0

def test_batch_partial_failure(self, action_service, mock_spools):
    """Test batch with partial failures (2 success, 1 failure)."""
    request = BatchActionRequest(
        worker_id=93,
        operacion=ActionType.ARM,
        tag_spools=["MK-VALID-1", "MK-INVALID", "MK-VALID-2"]
    )

    response = action_service.batch_iniciar(request)

    # Batch succeeds if at least 1 processed
    assert response.success is True
    assert response.exitosos == 2
    assert response.fallidos == 1
    assert response.total == 3

    # Check individual results
    assert response.resultados[1]["success"] is False
```

## Frontend-Specific Testing

**Playwright Configuration (zeues-frontend/playwright.config.ts):**
- Test timeout: 30 seconds per test
- Expect timeout: 5 seconds for assertions
- Parallel execution: Full parallelism (fullyParallel: true)
- Screenshots: On all tests for documentation
- Video: Retained on failure
- Trace: On first retry for debugging
- Viewport: Tablet (768x1024) - production target

**Test Organization Structure:**
```typescript
test.describe('Flujo 1: INICIAR ARM (Armado) - v2.0', () => {
  test('debe completar el flujo INICIAR ARM exitosamente', async ({ page }) => {
    // ========================================
    // P1 - Selección de Operación
    // ========================================
    await test.step('P1 - Selección de Operación', async () => {
      await page.goto('/');
      await expect(page.getByRole('button', { name: /ARMADO/i })).toBeVisible();
      await page.getByRole('button', { name: /ARMADO/i }).click();
      await expect(page).toHaveURL('/operacion');
    });

    // ========================================
    // P2 - Selección de Trabajador
    // ========================================
    await test.step('P2 - Selección de Trabajador', async () => {
      // ... assertions and interactions
    });
  });
});
```

**Selectors Used in Tests:**
- Role-based: `page.getByRole('button', { name: /pattern/i })`
- Text-based: `page.getByText(/pattern/i)`
- Regex: Case-insensitive matching with `/pattern/i`
- URL assertions: `expect(page).toHaveURL(/\/path\?param=value/)`

---

*Testing analysis: 2026-01-26*
