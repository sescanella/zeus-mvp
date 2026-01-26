# Coding Conventions

**Analysis Date:** 2026-01-26

## Naming Patterns

**Files:**
- Python modules: `snake_case` with underscore separation
  - Services: `{service_name}_service.py` (e.g., `action_service.py`)
  - Repositories: `{entity_name}_repository.py` (e.g., `sheets_repository.py`)
  - Routers: `{entity_name}.py` (e.g., `actions.py`)
  - Models: `{entity_name}.py` (e.g., `worker.py`)
  - Utils: `{function_type}.py` (e.g., `date_formatter.py`, `logger.py`)

- TypeScript/React files: `camelCase` for components, lowercase for utilities
  - Pages: Descriptive route names (e.g., `page.tsx`, `layout.tsx`)
  - Components: PascalCase (e.g., `Button.tsx`, `Card.tsx`)
  - Libraries: lowercase descriptive (e.g., `api.ts`, `types.ts`, `context.tsx`)

**Functions and Methods:**
- Python: `snake_case_with_underscores`
  - Examples: `validar_puede_iniciar_arm()`, `get_workers()`, `find_spool_by_tag()`
  - Boolean methods start with `validar_` or `es_` prefix
  - Example: `validar_puede_completar_arm()`, `es_activo()`

- TypeScript: `camelCase`
  - Examples: `getWorkers()`, `handleSelectOperation()`, `fetchWorkers()`
  - Event handlers: `handle` prefix (e.g., `handleSelectOperation()`)
  - Async functions: `fetch` or `async` prefix (e.g., `fetchWorkers()`, `getSpoolsParaIniciar()`)

**Variables:**
- Python: `snake_case`
  - Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `API_URL = 'http://localhost:8000'`)
  - Examples: `worker_nombre`, `spool_data`, `error_message`

- TypeScript: `camelCase`
  - Constants: Define in UPPERCASE (e.g., `const API_URL = process.env.NEXT_PUBLIC_API_URL`)
  - Examples: `selectedWorker`, `operacion`, `isLoading`

**Types and Interfaces:**
- TypeScript: PascalCase with descriptive names
  - Examples: `Worker`, `Spool`, `ActionPayload`, `BatchActionRequest`
  - Response types: Suffix with `Response` (e.g., `ActionResponse`, `WorkerListResponse`)
  - Request types: Suffix with `Request` (e.g., `ActionRequest`, `BatchActionRequest`)

- Python Enums: PascalCase class names, UPPERCASE members
  ```python
  class ActionType(str, Enum):
      ARM = "ARM"
      SOLD = "SOLD"
      METROLOGIA = "METROLOGIA"
  ```

- Python Pydantic models: PascalCase
  - Examples: `Worker`, `Spool`, `ActionRequest`

## Code Style

**Formatting:**
- Python: 4 spaces indentation (enforced by Python standard)
- TypeScript: Use ESLint and Next.js defaults
  - Max line length: Implicit (follow existing patterns ~100-120 chars)
  - Semicolons: Required by ESLint config

**Linting:**
- Frontend (Next.js/TypeScript):
  - Tool: ESLint with Next.js core-web-vitals + TypeScript support
  - Config: `zeues-frontend/.eslintrc.json`
  - Command: `npm run lint` (must pass with zero errors/warnings)
  - Strict rule: No use of `any` type - ESLint enforces `@typescript-eslint/no-explicit-any`
  - Use `unknown` for truly dynamic types, cast after validation

- Backend (Python):
  - Tool: pytest for testing (implicit style enforcement)
  - Implicit adherence to PEP 8 through project practices
  - Docstrings: Google-style with triple quotes

**Code Quality Enforcements:**
- TypeScript must compile: `npx tsc --noEmit` (must pass)
- ESLint must pass: `npm run lint` (zero errors/warnings)
- Frontend production build must succeed: `npm run build`

## Import Organization

**Order:**
1. Standard library imports (Python: `os`, `sys`, `datetime`, `logging`)
2. Third-party imports (FastAPI, pydantic, gspread, pytest, etc.)
3. Local application imports (relative to project root)
4. Type-only imports (Python `from typing import`, TypeScript `import type`)

**Path Aliases:**
- TypeScript: `@/*` resolves to project root (e.g., `@/lib/api` → `./lib/api.ts`)
  - Used in imports: `import { getWorkers } from '@/lib/api'`
  - Used in components: `import { Button } from '@/components'`

- Python: No alias system; use absolute imports from project root
  - Examples: `from backend.services.action_service import ActionService`
  - Examples: `from backend.models.enums import ActionType`

**Barrel Files:**
- Used in frontend for component exports
  - Example: `components/index.ts` exports all UI components
  - Reduces import complexity: `import { Button, Card } from '@/components'`

## Error Handling

**Patterns:**
- Python backend uses custom exception hierarchy (all inherit from `ZEUSException`)
  - Location: `backend/exceptions.py`
  - Base class provides: `message`, `error_code`, `data` dict for context
  - Examples: `SpoolNoEncontradoError`, `OperacionYaIniciadaError`, `NoAutorizadoError`
  - Each exception includes context data for API responses

```python
class ZEUSException(Exception):
    def __init__(self, message: str, error_code: str, data: Optional[dict] = None):
        self.message = message
        self.error_code = error_code
        self.data = data or {}
```

- FastAPI exception handlers in `main.py` convert ZEUSException subclasses to HTTP status codes
  - 404: SpoolNoEncontradoError, WorkerNoEncontradoError
  - 400: OperacionYaIniciadaError, OperacionYaCompletadaError, DependenciasNoSatisfechasError
  - 403: NoAutorizadoError, RolNoAutorizadoError

- TypeScript/React uses try/catch with Error typing
  - Pattern: `const message = err instanceof Error ? err.message : 'Default message'`
  - Use `unknown` type for caught errors, validate before accessing properties
  - Fallback error messages for user display

```typescript
try {
  const data = await getWorkers();
} catch (err) {
  const message = err instanceof Error ? err.message : 'Error al cargar trabajadores';
  setError(message);
}
```

## Logging

**Framework:** Python `logging` module (standard library)

**Patterns:**
- Get logger at module level: `logger = logging.getLogger(__name__)`
- Use log levels appropriately:
  - `logger.debug()` - Detailed validation steps, state transitions
  - `logger.info()` - Entry/exit of major operations (e.g., "ActionService v2.1 inicializado")
  - `logger.warning()` - Recoverable issues or unexpected states
  - `logger.error()` - Error conditions that may need remediation

- Contextual information in logs:
  ```python
  logger.info(f"[V2.1] Validating ARM start | Spool: {spool.tag_spool}")
  logger.debug(f"[V2.1] ✅ ARM start validation passed | {spool.tag_spool}")
  ```

- Include operation context like `[V2.1]` prefixes for tracking architecture version

**Frontend logging:**
- Use `console.error()` for API errors (logged at runtime)
- Pattern: `console.error('functionName error:', error);`
- Error messages display to user via React state, not console

## Comments

**When to Comment:**
- Complex business logic that isn't self-documenting
- Non-obvious v2.1 architectural decisions (Direct Read vs Event Sourcing)
- Integration points with Google Sheets (volatile column indices)
- Batch operation coordination

**JSDoc/TSDoc:**
- Python: Google-style docstrings with triple quotes
  ```python
  def validar_puede_iniciar_arm(self, spool: Spool, worker_id: Optional[int] = None) -> None:
      """Valida INICIAR ARM (v2.1 Direct Read).

      Args:
          spool: Spool object to validate
          worker_id: Optional worker ID for role validation

      Raises:
          DependenciasNoSatisfechasError: If prerequisites not met
          OperacionYaIniciadaError: If operation already started
      """
  ```

- TypeScript: JSDoc comments for public functions
  ```typescript
  /**
   * GET /api/workers
   * Obtiene lista de trabajadores activos.
   *
   * @returns Promise<Worker[]> - Array de trabajadores activos
   * @throws Error si falla la request o backend no disponible
   */
  export async function getWorkers(): Promise<Worker[]>
  ```

- Parameter descriptions in docstrings required for services/APIs

## Function Design

**Size:**
- Keep functions under 50 lines where possible (hard stop at 100)
- Single responsibility principle: One function = one concept

**Parameters:**
- Python: Use type hints on all parameters and return values
  - Examples: `def find_spool_by_tag(self, tag: str) -> Optional[Spool]:`
  - Use `Optional[T]` for nullable types
  - Use `|` union syntax for multiple types: `operacion: ActionType | str`

- TypeScript: Explicit types required
  - Examples: `async function getWorkers(): Promise<Worker[]>`
  - Component props interface: `interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>`

**Return Values:**
- Explicit return types on all functions (no implicit `any`)
- Nullable returns: `Optional[T]` (Python) or `T | null` (TypeScript)
- Status codes returned in responses consistently

**v2.1 Ownership Pattern:**
- Completed operations DON'T require ownership validation (removed from completar)
- CANCELAR operations require ownership (who started can cancel)
- Pattern seen in `validar_puede_completar_arm()` - no worker name check

## Module Design

**Exports:**
- Python: Implicit (all public functions/classes available via `from module import Name`)
- TypeScript: Explicit `export` declarations on public items
  - Example: `export async function getWorkers(): Promise<Worker[]>`

**Barrel Files:**
- Frontend uses `components/index.ts` for component library
  - Reduces import boilerplate
  - Single point of export for all UI components

**Service Layer Pattern:**
- All business logic encapsulated in services
- Services receive dependencies via constructor injection
- Example from `ActionService.__init__()`:
  ```python
  def __init__(
      self,
      sheets_repository: Optional[SheetsRepository] = None,
      metadata_repository: Optional[MetadataRepository] = None,
      validation_service: Optional[ValidationService] = None,
      spool_service: Optional[SpoolService] = None,
      worker_service: Optional[WorkerService] = None
  ):
  ```

**Repository Pattern:**
- Repositories abstract data source (Google Sheets)
- All Sheets operations go through `SheetsRepository`
- Metadata operations go through `MetadataRepository`
- Repositories return domain models (Spool, Worker, etc.), not raw data

## TypeScript Strict Mode Enforcement

**Critical Rule: NEVER use `any` type**
- ESLint enforces `@typescript-eslint/no-explicit-any`
- Violation will fail `npm run lint`

**Use `unknown` for dynamic data:**
```typescript
// Dynamic data from API response
const data: unknown = await response.json();

// Type guard before using
if (isValidWorker(data)) {
  // Now TypeScript knows data is Worker type
  console.log(data.nombre);
}

function isValidWorker(obj: unknown): obj is Worker {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'nombre' in obj &&
    'activo' in obj
  );
}
```

**Component prop types must be explicit:**
```typescript
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'iniciar' | 'completar' | 'cancelar' | 'cancel';
}

export function Button({
  children,
  variant = 'primary',
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  // Implementation
}
```

---

*Convention analysis: 2026-01-26*
