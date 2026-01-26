# Technology Stack

**Analysis Date:** 2026-01-26

## Languages

**Primary:**
- Python 3.9 - Backend REST API with FastAPI
- TypeScript 5.4 - Frontend React components and Next.js pages
- JavaScript - Next.js configuration and build tooling

**Secondary:**
- HTML5 - Rendered by Next.js
- CSS3 - Tailwind CSS utility classes

## Runtime

**Environment:**
- Node.js (unspecified version, latest LTS compatible with Next.js 14.2.0)
- Python 3.9-slim (Docker image for production)

**Package Manager:**
- npm (Node/frontend) - lockfile: `zeues-frontend/package-lock.json` present
- pip (Python/backend) - lockfile: `requirements.txt` present

## Frameworks

**Core:**
- FastAPI 0.121.0 - REST API framework with automatic OpenAPI documentation
- Next.js 14.2.0 - React framework with App Router for frontend
- React 18.3.0 - UI component library

**Testing:**
- Playwright 1.56.1 - E2E testing framework for frontend
- pytest 8.4.2 - Python unit/integration testing framework
- pytest-cov 7.0.0 - Code coverage reporting for tests
- pytest-mock 3.15.1 - Mocking fixtures for pytest

**Build/Dev:**
- TypeScript 5.4.0 - Static type checking
- ESLint 8.57.0 - Linting (via next lint)
- Tailwind CSS 3.4.0 - Utility-first CSS framework
- PostCSS 8.4.38 - CSS transformation pipeline
- Autoprefixer 10.4.19 - Vendor prefix management

## Key Dependencies

**Critical Backend:**
- gspread 6.2.1 - Google Sheets API Python client (data source integration)
- google-auth 2.41.1 - Google OAuth 2.0 authentication
- google-auth-oauthlib 1.2.3 - OAuth flow support
- pydantic 2.12.4 - Data validation and serialization (request/response models)
- uvicorn 0.38.0 - ASGI application server for production

**Critical Frontend:**
- lucide-react 0.562.0 - Icon component library
- @types/react 18.3.0 - TypeScript types for React

**Infrastructure/Utilities:**
- python-dotenv 1.2.1 - Environment variable loading from `.env.local`
- requests 2.32.5 - HTTP client for external APIs
- httpx 0.28.1 - Async HTTP client with retry support
- pandas 2.3.3 - Data frame manipulation (used in tests/utilities)
- numpy 2.0.2 - Numerical computing
- coverage 7.10.7 - Test coverage measurement

**Timezone/Date Handling:**
- pytz 2025.2 - Timezone database (Santiago, Chile: America/Santiago)
- python-dateutil 2.9.0.post0 - Date/time parsing and manipulation
- tzdata 2025.2 - IANA timezone data

**Security/Cryptography:**
- PyYAML 6.0.3 - YAML parsing (configuration files)
- rsa 4.9.1 - RSA encryption (Service Account private key handling)
- pyasn1 0.6.1 - ASN.1 encoding/decoding

## Configuration

**Environment:**
Backend loads from `.env.local` (via python-dotenv):
```
GOOGLE_CLOUD_PROJECT_ID=zeus-mvp
GOOGLE_SHEET_ID=17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ
GOOGLE_SERVICE_ACCOUNT_EMAIL=zeus-mvp@zeus-mvp.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY=(Service Account private key)
GOOGLE_APPLICATION_CREDENTIALS_JSON=(Railway production - JSON env var)
ENVIRONMENT=development|production
TIMEZONE=America/Santiago
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,https://zeues-frontend.vercel.app
LOG_LEVEL=INFO
CACHE_TTL_SECONDS=300
HOJA_OPERACIONES_NOMBRE=Operaciones
HOJA_TRABAJADORES_NOMBRE=Trabajadores
HOJA_METADATA_NOMBRE=Metadata
```

Frontend environment (Next.js):
```
NEXT_PUBLIC_API_URL=http://localhost:8000 (or production URL)
```

**Build:**
- `next.config.js` - Next.js build configuration (SWC minification enabled)
- `tsconfig.json` - TypeScript compiler configuration with `@/*` path alias
- `zeues-frontend/tailwind.config.ts` - Tailwind CSS configuration
- `backend/config.py` - Centralized Python configuration class
- `.env.local` - Development environment variables (gitignored)

## Platform Requirements

**Development:**
- Node.js (LTS, compatible with Next.js 14.2.0)
- Python 3.9+ with venv virtual environment
- Git for version control
- Docker (optional, for local backend containerization)

**Production:**
- Docker - Backend deployed as Python 3.9-slim container
- Railway.app - Backend hosting and deployment platform
- Vercel - Frontend deployment platform for Next.js
- Google Cloud Platform - Service Account credentials for Sheets API access

## Deployment Architecture

**Backend:**
- Dockerfile builds Python 3.9-slim image
- uvicorn ASGI server listening on port 8000
- Environment variable `PORT` respected (Railway compatibility)
- PYTHONPATH=/app for module imports

**Frontend:**
- Deployed to Vercel (Next.js native hosting)
- Production URL: https://zeues-frontend.vercel.app
- API endpoint in production: https://zeues-backend-mvp-production.up.railway.app

**CI/CD:**
- GitHub Actions workflow (`.github/workflows/backend.yml`)
  - Runs pytest tests on push to main (paths: backend/**, tests/**, requirements.txt)
  - Enforces 80% code coverage
  - Deploys to Railway via Railway CLI (`@railway/cli`)

---

*Stack analysis: 2026-01-26*
