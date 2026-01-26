"""
Tests unitarios para el módulo de cache (SimpleCache).

Tests:
- test_cache_set_and_get: Set y get básico
- test_cache_returns_none_when_empty: Get en cache vacío
- test_cache_expiration: Valores expirados
- test_cache_invalidate: Invalidación manual
- test_cache_clear: Limpieza completa
- test_cache_overwrites_existing_key: Sobrescritura
- test_cache_get_does_not_return_expired: Verificación TTL
"""
import pytest
import time
from backend.utils.cache import SimpleCache, get_cache


class TestSimpleCache:
    """Tests para la clase SimpleCache."""

    def test_cache_set_and_get(self):
        """Test: Set y get básico funciona correctamente."""
        cache = SimpleCache()

        # Set value
        cache.set("test_key", "test_value", ttl_seconds=60)

        # Get value
        result = cache.get("test_key")

        assert result == "test_value"

    def test_cache_returns_none_when_empty(self):
        """Test: Get en cache vacío retorna None."""
        cache = SimpleCache()

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_expiration(self):
        """Test: Valores expirados retornan None."""
        cache = SimpleCache()

        # Set value con TTL muy corto (1 segundo)
        cache.set("expiring_key", "value", ttl_seconds=1)

        # Verificar que existe inmediatamente
        assert cache.get("expiring_key") == "value"

        # Esperar a que expire
        time.sleep(1.1)

        # Verificar que expiró
        result = cache.get("expiring_key")
        assert result is None

    def test_cache_invalidate(self):
        """Test: Invalidación manual funciona correctamente."""
        cache = SimpleCache()

        # Set value
        cache.set("key_to_invalidate", "value", ttl_seconds=60)

        # Verificar que existe
        assert cache.get("key_to_invalidate") == "value"

        # Invalidar
        cache.invalidate("key_to_invalidate")

        # Verificar que fue removido
        assert cache.get("key_to_invalidate") is None

    def test_cache_invalidate_nonexistent_key(self):
        """Test: Invalidar key que no existe no lanza error."""
        cache = SimpleCache()

        # No debería lanzar excepción
        cache.invalidate("nonexistent_key")

    def test_cache_clear(self):
        """Test: Clear limpia todo el cache."""
        cache = SimpleCache()

        # Agregar múltiples valores
        cache.set("key1", "value1", ttl_seconds=60)
        cache.set("key2", "value2", ttl_seconds=60)
        cache.set("key3", "value3", ttl_seconds=60)

        # Verificar que existen
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # Limpiar cache
        cache.clear()

        # Verificar que todo fue removido
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_overwrites_existing_key(self):
        """Test: Set con mismo key sobrescribe el valor anterior."""
        cache = SimpleCache()

        # Set inicial
        cache.set("key", "old_value", ttl_seconds=60)
        assert cache.get("key") == "old_value"

        # Sobrescribir
        cache.set("key", "new_value", ttl_seconds=60)
        assert cache.get("key") == "new_value"

    def test_cache_get_does_not_return_expired(self):
        """Test: TTL funciona correctamente y no retorna valores expirados."""
        cache = SimpleCache()

        # Set valor con TTL corto
        cache.set("test_ttl", "value", ttl_seconds=1)

        # Inmediatamente debe estar disponible
        assert cache.get("test_ttl") == "value"

        # Esperar a que expire
        time.sleep(1.5)

        # No debe retornar valor expirado
        assert cache.get("test_ttl") is None

    def test_cache_handles_different_types(self):
        """Test: Cache maneja diferentes tipos de datos."""
        cache = SimpleCache()

        # String
        cache.set("string", "text", ttl_seconds=60)
        assert cache.get("string") == "text"

        # Int
        cache.set("int", 42, ttl_seconds=60)
        assert cache.get("int") == 42

        # Float
        cache.set("float", 3.14, ttl_seconds=60)
        assert cache.get("float") == 3.14

        # List
        cache.set("list", [1, 2, 3], ttl_seconds=60)
        assert cache.get("list") == [1, 2, 3]

        # Dict
        cache.set("dict", {"key": "value"}, ttl_seconds=60)
        assert cache.get("dict") == {"key": "value"}

        # None
        cache.set("none", None, ttl_seconds=60)
        assert cache.get("none") is None

    def test_cache_different_ttls(self):
        """Test: Diferentes TTLs funcionan independientemente."""
        cache = SimpleCache()

        # Set con diferentes TTLs
        cache.set("short_ttl", "expires_soon", ttl_seconds=1)
        cache.set("long_ttl", "expires_later", ttl_seconds=10)

        # Inmediatamente ambos disponibles
        assert cache.get("short_ttl") == "expires_soon"
        assert cache.get("long_ttl") == "expires_later"

        # Esperar a que expire el corto
        time.sleep(1.5)

        # Solo el corto debe haber expirado
        assert cache.get("short_ttl") is None
        assert cache.get("long_ttl") == "expires_later"


class TestGetCacheSingleton:
    """Tests para la función get_cache (singleton pattern)."""

    def test_get_cache_returns_same_instance(self):
        """Test: get_cache() retorna siempre la misma instancia."""
        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    def test_get_cache_singleton_preserves_data(self):
        """Test: Datos persisten entre llamadas a get_cache()."""
        # Primera llamada
        cache1 = get_cache()
        cache1.set("singleton_test", "value", ttl_seconds=60)

        # Segunda llamada
        cache2 = get_cache()
        assert cache2.get("singleton_test") == "value"

    def test_get_cache_clear_affects_all_references(self):
        """Test: Clear afecta todas las referencias al cache."""
        cache1 = get_cache()
        cache2 = get_cache()

        cache1.set("key", "value", ttl_seconds=60)

        # Clear desde cache2
        cache2.clear()

        # Verificar que cache1 también está vacío
        assert cache1.get("key") is None


if __name__ == "__main__":
    """Ejecutar tests con pytest."""
    pytest.main([__file__, "-v"])
