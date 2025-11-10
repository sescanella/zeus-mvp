"""
Cache simple con TTL para reducir llamadas a Google Sheets API.

Proporciona almacenamiento en memoria con tiempo de expiración (TTL)
para optimizar el acceso a datos que cambian poco frecuentemente.
"""
from datetime import datetime, timedelta
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Cache simple en memoria con TTL (Time-To-Live).

    Características:
    - Almacenamiento key-value en memoria
    - TTL configurable por entrada
    - Expiración automática al leer
    - Invalidación manual por key
    - Limpieza completa

    Uso:
        cache = SimpleCache()
        cache.set("key", value, ttl_seconds=300)
        value = cache.get("key")  # None si expiró o no existe
        cache.invalidate("key")   # Invalida manualmente
        cache.clear()             # Limpia todo el cache
    """

    def __init__(self):
        """Inicializa el cache vacío."""
        self._cache: dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene valor del cache si no ha expirado.

        Args:
            key: Clave del valor a obtener

        Returns:
            Valor cacheado si existe y no ha expirado, None en caso contrario

        Example:
            >>> cache = SimpleCache()
            >>> cache.set("foo", "bar", ttl_seconds=60)
            >>> cache.get("foo")
            'bar'
            >>> cache.get("nonexistent")
            None
        """
        if key in self._cache:
            value, expiration = self._cache[key]

            # Verificar si ha expirado
            if datetime.now() < expiration:
                logger.debug(f"✅ Cache hit: {key}")
                return value
            else:
                # Expiró, remover del cache
                del self._cache[key]
                logger.debug(f"⚠️  Cache expired: {key}")

        return None

    def set(self, key: str, value: Any, ttl_seconds: int):
        """
        Guarda valor en cache con TTL especificado.

        Args:
            key: Clave para identificar el valor
            value: Valor a cachear (cualquier tipo)
            ttl_seconds: Tiempo de vida en segundos

        Example:
            >>> cache = SimpleCache()
            >>> cache.set("workers", [worker1, worker2], ttl_seconds=300)
            >>> cache.set("spools", [spool1, spool2], ttl_seconds=60)
        """
        expiration = datetime.now() + timedelta(seconds=ttl_seconds)
        self._cache[key] = (value, expiration)
        logger.debug(f"💾 Cache set: {key} (TTL: {ttl_seconds}s, expires: {expiration.strftime('%H:%M:%S')})")

    def invalidate(self, key: str):
        """
        Invalida cache manualmente (ej: después de actualizar datos).

        Args:
            key: Clave del valor a invalidar

        Example:
            >>> cache = SimpleCache()
            >>> cache.set("data", value, ttl_seconds=300)
            >>> # ... actualizar datos en Sheets ...
            >>> cache.invalidate("data")  # Fuerza re-lectura en próximo get
        """
        if key in self._cache:
            del self._cache[key]
            logger.info(f"🗑️  Cache invalidated: {key}")
        else:
            logger.debug(f"⚠️  Cache invalidate: key '{key}' not found (already expired or never set)")

    def clear(self):
        """
        Limpia todo el cache (útil para testing o reinicio).

        Example:
            >>> cache = SimpleCache()
            >>> cache.set("key1", "value1", ttl_seconds=60)
            >>> cache.set("key2", "value2", ttl_seconds=60)
            >>> cache.clear()
            >>> cache.get("key1")  # None
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"🧹 Cache cleared ({count} entries removed)")


# Singleton global para uso en toda la aplicación
_cache = SimpleCache()


def get_cache() -> SimpleCache:
    """
    Obtiene instancia global del cache (singleton pattern).

    Returns:
        SimpleCache: Instancia global del cache

    Example:
        >>> from backend.utils.cache import get_cache
        >>> cache = get_cache()
        >>> cache.set("key", "value", ttl_seconds=60)
    """
    return _cache
