"""
Configuración del backend ZEUES.

Carga y valida variables de entorno necesarias para el funcionamiento del sistema.
"""
import os
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

    # Path a credenciales JSON del Service Account
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = str(
        Path(__file__).parent.parent / 'credenciales' / 'zeus-mvp-81282fb07109.json'
    )

    # Nombres de hojas en Google Sheets
    HOJA_OPERACIONES_NOMBRE: str = os.getenv('HOJA_OPERACIONES_NOMBRE', 'Operaciones')
    HOJA_TRABAJADORES_NOMBRE: str = os.getenv('HOJA_TRABAJADORES_NOMBRE', 'Trabajadores')

    # Cache configuration
    CACHE_TTL_SECONDS: int = int(os.getenv('CACHE_TTL_SECONDS', '300'))  # 5 minutos default

    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')

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
            'GOOGLE_SERVICE_ACCOUNT_EMAIL': cls.GOOGLE_SERVICE_ACCOUNT_EMAIL,
        }

        missing = [var for var, value in required_vars.items() if not value]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please check your .env.local file."
            )

        # Validar que el archivo de credenciales existe
        if not Path(cls.GOOGLE_SERVICE_ACCOUNT_JSON_PATH).exists():
            raise ValueError(
                f"Google Service Account JSON file not found at: "
                f"{cls.GOOGLE_SERVICE_ACCOUNT_JSON_PATH}"
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
        print(f"   - Cache TTL: {config.CACHE_TTL_SECONDS}s")
        print(f"   - Allowed Origins: {config.ALLOWED_ORIGINS}")
    except ValueError as e:
        print(f"❌ Error de configuración: {e}")
        exit(1)
