"""
Configuración del backend ZEUES.

Carga y valida variables de entorno necesarias para el funcionamiento del sistema.
"""
import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env.local
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuración centralizada del backend."""

    # Google Cloud & Sheets
    GOOGLE_CLOUD_PROJECT_ID: str = os.getenv('GOOGLE_CLOUD_PROJECT_ID', '')
    GOOGLE_SHEET_ID: str = os.getenv('GOOGLE_SHEET_ID', '')
    GOOGLE_SERVICE_ACCOUNT_EMAIL: str = os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL', '')
    GOOGLE_PRIVATE_KEY: str = os.getenv('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n')

    # Credenciales desde variable de entorno JSON (Railway/producción)
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    # Path a credenciales JSON del Service Account (desarrollo local)
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = str(
        Path(__file__).parent.parent / 'credenciales' / 'zeus-mvp-81282fb07109.json'
    )

    # Nombres de hojas en Google Sheets
    HOJA_OPERACIONES_NOMBRE: str = os.getenv('HOJA_OPERACIONES_NOMBRE', 'Operaciones')
    HOJA_TRABAJADORES_NOMBRE: str = os.getenv('HOJA_TRABAJADORES_NOMBRE', 'Trabajadores')
    HOJA_METADATA_NOMBRE: str = os.getenv('HOJA_METADATA_NOMBRE', 'Metadata')

    # Cache configuration
    CACHE_TTL_SECONDS: int = int(os.getenv('CACHE_TTL_SECONDS', '300'))  # 5 minutos default

    # Redis configuration (v3.0)
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_LOCK_TTL_SECONDS: int = int(os.getenv('REDIS_LOCK_TTL_SECONDS', '3600'))  # 1 hour default (v3.0 compatibility)
    REDIS_MAX_CONNECTIONS: int = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))

    # v4.0 Persistent Lock Configuration
    REDIS_PERSISTENT_LOCKS: bool = os.getenv('REDIS_PERSISTENT_LOCKS', 'true').lower() == 'true'  # Default True for v4.0
    REDIS_SAFETY_TTL: int = int(os.getenv('REDIS_SAFETY_TTL', '10'))  # Safety TTL for initial acquisition (seconds)

    # Redis Connection Pool Configuration (Phase 2: Crisis Recovery)
    REDIS_POOL_MAX_CONNECTIONS: int = int(os.getenv('REDIS_POOL_MAX_CONNECTIONS', '20'))  # Conservative limit for Railway
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv('REDIS_SOCKET_TIMEOUT', '5'))  # Prevents hanging connections
    REDIS_SOCKET_CONNECT_TIMEOUT: int = int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5'))  # Fail fast if unreachable
    REDIS_HEALTH_CHECK_INTERVAL: int = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))  # Proactive health checks

    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')

    # Timezone - Santiago, Chile (UTC-3 standard, UTC-4 daylight saving)
    TIMEZONE: str = os.getenv('TIMEZONE', 'America/Santiago')

    # API Configuration
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '8000'))

    # CORS - Orígenes permitidos
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
    ]

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # Migration Configuration (v3.0)
    BACKUP_FOLDER_ID: Optional[str] = os.getenv('BACKUP_FOLDER_ID')  # Google Drive folder for backups
    MIGRATION_DRY_RUN: bool = os.getenv('MIGRATION_DRY_RUN', 'false').lower() == 'true'

    # V3.0 Column Definitions
    V3_COLUMNS = [
        {
            "name": "Ocupado_Por",
            "type": "string",
            "description": "Worker currently occupying the spool (format: INICIALES(ID))"
        },
        {
            "name": "Fecha_Ocupacion",
            "type": "date",
            "description": "Date when spool was occupied (format: YYYY-MM-DD)"
        },
        {
            "name": "version",
            "type": "integer",
            "description": "Version token for optimistic locking (starts at 0)"
        },
        {
            "name": "Estado_Detalle",
            "type": "string",
            "description": "Combined state display (occupation + operation progress)"
        }
    ]

    @classmethod
    def get_credentials_dict(cls) -> Optional[dict]:
        """
        Obtiene las credenciales de Google Service Account como diccionario.

        Prioridad:
        1. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS_JSON (Railway/prod)
        2. Archivo JSON local (desarrollo)

        Returns:
            dict con credenciales o None si no se encuentran
        """
        # Opción 1: JSON desde variable de entorno (Railway)
        if cls.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            try:
                return json.loads(cls.GOOGLE_APPLICATION_CREDENTIALS_JSON)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")

        # Opción 2: Archivo JSON local (desarrollo)
        json_path = Path(cls.GOOGLE_SERVICE_ACCOUNT_JSON_PATH)
        if json_path.exists():
            with open(json_path, 'r') as f:
                return json.load(f)

        return None

    @classmethod
    def validate(cls) -> None:
        """
        Valida que todas las variables de entorno críticas estén configuradas.

        Raises:
            ValueError: Si falta alguna variable de entorno requerida.
        """
        required_vars = {
            'GOOGLE_CLOUD_PROJECT_ID': cls.GOOGLE_CLOUD_PROJECT_ID,
            'GOOGLE_SHEET_ID': cls.GOOGLE_SHEET_ID,
        }

        missing = [var for var, value in required_vars.items() if not value]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please check your .env.local file or Railway variables."
            )

        # Validar que tenemos credenciales (JSON o archivo)
        if not cls.get_credentials_dict():
            raise ValueError(
                f"Google Service Account credentials not found. "
                f"Provide either GOOGLE_APPLICATION_CREDENTIALS_JSON env var "
                f"or file at: {cls.GOOGLE_SERVICE_ACCOUNT_JSON_PATH}"
            )

    @classmethod
    def get_scopes(cls) -> list[str]:
        """Retorna los scopes necesarios para Google Sheets API."""
        return [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]


# Instancia global de configuración
config = Config()


if __name__ == '__main__':
    """Script para validar configuración."""
    try:
        config.validate()
        print("✅ Configuración válida")
        print(f"   - Project ID: {config.GOOGLE_CLOUD_PROJECT_ID}")
        print(f"   - Sheet ID: {config.GOOGLE_SHEET_ID}")
        print(f"   - Service Account: {config.GOOGLE_SERVICE_ACCOUNT_EMAIL}")
        print(f"   - Environment: {config.ENVIRONMENT}")
        print(f"   - Timezone: {config.TIMEZONE}")
        print(f"   - Cache TTL: {config.CACHE_TTL_SECONDS}s")
        print(f"   - Allowed Origins: {config.ALLOWED_ORIGINS}")
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        exit(1)
