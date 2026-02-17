# ZEUES Backend - FastAPI

Sistema de Trazabilidad para Manufactura de Cañerías - Backend API

## Stack

- **Framework:** FastAPI 0.121.0
- **Python:** 3.11+
- **Database:** Google Sheets (via gspread)
- **Auth:** Google Service Account
- **Deploy:** Railway

## Setup Local

### 1. Virtual Environment

```bash
# Crear y activar venv
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Credenciales Google

1. Colocar archivo JSON de Service Account en: `credenciales/zeus-mvp-81282fb07109.json`
2. El Service Account debe tener acceso al Google Sheet

### 3. Variables de Entorno

Crear archivo `.env.local`:

```env
# Google Cloud
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp
GOOGLE_SHEET_ID=11v8fD5yGjm4yZU1K9h8tQx9qR2rL6vM3nP4wX7sY5tA

# Environment
ENVIRONMENT=development

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Cache
CACHE_TTL_SECONDS=300
```

### 4. Ejecutar Backend

```bash
# Activar venv
source venv/bin/activate

# Ejecutar con hot-reload
uvicorn backend.main:app --reload

# El servidor estará en: http://localhost:8000
# Docs en: http://localhost:8000/api/docs
```

## Testing

```bash
# Todos los tests
pytest tests/ -v

# Con coverage
pytest tests/ --cov=backend --cov-report=html

# Solo tests unitarios
pytest tests/unit/ -v

# Solo tests E2E
pytest tests/e2e/ -v

# Ver coverage HTML
open htmlcov/index.html
```

## Estructura del Proyecto

```
backend/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Configuración
│   ├── exceptions.py        # Excepciones custom (10)
│   ├── core/
│   │   └── dependency.py    # Dependency injection
│   ├── models/              # Pydantic models
│   │   ├── enums.py
│   │   ├── worker.py
│   │   ├── spool.py
│   │   ├── action.py
│   │   └── error.py
│   ├── repositories/
│   │   └── sheets_repository.py
│   ├── services/
│   │   ├── validation_service.py
│   │   ├── sheets_service.py
│   │   ├── spool_service.py
│   │   ├── worker_service.py
│   │   └── action_service.py
│   ├── routers/
│   │   ├── health.py
│   │   ├── workers.py
│   │   ├── spools.py
│   │   └── actions.py
│   └── utils/
│       ├── logger.py
│       └── cache.py
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

## API Endpoints

### Health Check
- `GET /api/health` - Verificar estado del servicio y conectividad Sheets

### Workers
- `GET /api/workers` - Lista de trabajadores activos

### Spools
- `GET /api/spools/iniciar?operacion=ARM|SOLD` - Spools disponibles para iniciar
- `GET /api/spools/completar?operacion=ARM|SOLD&worker_nombre=...` - Spools para completar

### Actions
- `POST /api/iniciar-accion` - Iniciar acción (asignar spool a trabajador)
- `POST /api/completar-accion` - Completar acción (registrar finalización)

### Documentación Interactiva
- `/api/docs` - Swagger UI (OpenAPI)
- `/api/redoc` - ReDoc

## Deploy en Railway

### 1. Login

```bash
railway login
```

### 2. Inicializar Proyecto

```bash
railway init
# Seleccionar "Create a new project"
# Nombre: zeues-backend-mvp
```

### 3. Configurar Variables de Entorno

```bash
# Variables CRÍTICAS
railway variables set GOOGLE_CLOUD_PROJECT_ID=zeus-mvp
railway variables set GOOGLE_SHEET_ID=11v8fD5yGjm4yZU1K9h8tQx9qR2rL6vM3nP4wX7sY5tA
railway variables set ENVIRONMENT=production
railway variables set ALLOWED_ORIGINS=https://zeues-frontend.vercel.app
railway variables set CACHE_TTL_SECONDS=300

# Service Account JSON (base64)
railway variables set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat credenciales/zeus-mvp-81282fb07109.json)"
```

### 4. Deploy

```bash
railway up
```

### 5. Verificar

```bash
# Ver logs
railway logs

# Obtener URL
railway domain

# Verificar health check
curl https://tu-app.railway.app/api/health
```

## Características Principales

### Ownership Validation (CRÍTICO)
Solo el trabajador que inició una acción puede completarla:
- ARM: Solo el armador (BC) puede completar
- SOLD: Solo el soldador (BE) puede completar
- Error 403 si otro trabajador intenta completar

### Cache Strategy
- TTL: 5 minutos (trabajadores), 1 minuto (spools)
- Invalidación automática después de writes
- Reducción -92% de API calls a Google Sheets

### Error Handling
10 excepciones custom mapeadas a HTTP status codes:
- 404: SpoolNoEncontradoError, WorkerNoEncontradoError
- 400: OperacionYaIniciadaError, OperacionYaCompletadaError, etc.
- 403: NoAutorizadoError (ownership violation)
- 503: SheetsConnectionError, SheetsUpdateError

### Logging
Logs comprehensivos en todos los niveles:
- INFO: Operaciones exitosas
- WARNING: Validaciones fallidas
- ERROR: Errores de sistema

## Métricas

- **Tests:** 123 totales (113 unitarios + 10 E2E)
- **Coverage:** 83% average, 95% en ActionService
- **API Calls:** -92% optimizado con cache
- **Latencia:** -90% con batch operations (500ms → 50ms)

## Troubleshooting

### Error: Google Sheets authentication failed
Verificar que el Service Account tiene permisos en el Sheet:
1. Abrir Google Sheet
2. Compartir con: zeus-mvp@zeus-mvp.iam.gserviceaccount.com
3. Permisos: Editor

### Error: Module not found
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Error: Tests failing
```bash
# Verificar que estás en el directorio raíz
# Navigate to project root
cd "$(git rev-parse --show-toplevel)"

# Ejecutar con PYTHONPATH
PYTHONPATH="$(pwd)" pytest tests/ -v
```

## Documentación Adicional

- **Documentación Completa:** Ver `proyecto-backend.md` en la raíz del proyecto
- **API Docs:** Ver `proyecto-backend-api.md`
- **Google Resources:** Ver `docs/GOOGLE-RESOURCES.md`

## Soporte

Para reportar issues o consultas, contactar al equipo de desarrollo.
