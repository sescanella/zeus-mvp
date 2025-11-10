"""
Logger configuration for ZEUES Backend API.

Proporciona configuración centralizada de logging con formato consistente
y niveles apropiados según el ambiente (development/production).

Características:
- Nivel DEBUG en local, INFO en producción
- Handler a stdout (Railway muestra logs)
- Formato: [TIMESTAMP] [LEVEL] [MODULE] MESSAGE
- Factory de loggers por módulo
"""

import logging
import sys
from backend.config import config


def setup_logger() -> None:
    """
    Configura logging global del sistema.

    Configura el nivel de logging según el ambiente:
    - ENVIRONMENT=local → DEBUG (máxima verbosidad para desarrollo)
    - Otros ambientes → INFO (logs de producción)

    Formato de log:
        [2025-11-10 14:30:00] [INFO] [routers.actions] Iniciando ARM para spool MK-123

    Componentes del formato:
        - TIMESTAMP: Fecha y hora del log (YYYY-MM-DD HH:MM:SS)
        - LEVEL: Nivel del log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - MODULE: Nombre del módulo que generó el log
        - MESSAGE: Mensaje descriptivo del log

    Handler:
        - StreamHandler a stdout para que Railway/Cloud capture logs
        - Sin archivos locales (logs efímeros en cloud)

    Usage:
        >>> from backend.utils.logger import setup_logger
        >>> setup_logger()
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("API iniciada correctamente")
    """
    # Determinar nivel de logging según ambiente
    level = logging.DEBUG if config.ENVIRONMENT == "local" else logging.INFO

    # Configurar logging global
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Log de confirmación de setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado: nivel={logging.getLevelName(level)}, ambiente={config.ENVIRONMENT}")


def get_logger(name: str) -> logging.Logger:
    """
    Factory de loggers por módulo.

    Retorna un logger configurado con el nombre del módulo especificado.
    Evita duplicación de configuración y asegura que todos los loggers
    usen la misma configuración global establecida por setup_logger().

    Args:
        name: Nombre del módulo (típicamente __name__).
              Ejemplo: "backend.routers.actions"

    Returns:
        Logger configurado listo para uso.

    Usage:
        >>> from backend.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Procesando request")
        [2025-11-10 14:30:00] [INFO] [backend.routers.actions] Procesando request

    Note:
        - setup_logger() debe ser llamado ANTES de usar get_logger()
        - Típicamente setup_logger() se llama en el startup event de FastAPI
        - get_logger() puede ser llamado múltiples veces sin problema
    """
    return logging.getLogger(name)


# Ejemplo de uso si se ejecuta directamente
if __name__ == '__main__':
    """Script de prueba de configuración de logging."""
    setup_logger()

    logger = get_logger(__name__)

    logger.debug("Este es un mensaje DEBUG (solo visible en local)")
    logger.info("Este es un mensaje INFO (visible en todos los ambientes)")
    logger.warning("Este es un mensaje WARNING (alerta de atención)")
    logger.error("Este es un mensaje ERROR (algo falló)")
    logger.critical("Este es un mensaje CRITICAL (fallo crítico del sistema)")

    print("\n✅ Logger configurado y testeado correctamente")
    print(f"   - Nivel actual: {logging.getLevelName(logging.root.level)}")
    print(f"   - Ambiente: {config.ENVIRONMENT}")
    print(f"   - Handler: stdout (Railway-compatible)")
