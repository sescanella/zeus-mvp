"""
Redis repository for connection pool management.

Provides singleton Redis client with async support for FastAPI integration.
Handles connection lifecycle, health checks, and graceful error handling.

Usage:
    redis_repo = RedisRepository()
    await redis_repo.connect()
    # Use redis_repo.client for Redis operations
    await redis_repo.disconnect()
"""
import logging
from typing import Optional
from redis import asyncio as aioredis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from backend.config import config

logger = logging.getLogger(__name__)


class RedisRepository:
    """
    Singleton repository for Redis connection management.

    Manages connection pool with automatic reconnection and health checks.
    Thread-safe singleton pattern ensures single connection pool across application.

    Attributes:
        client: Async Redis client instance (None until connected)
        _pool: Internal connection pool
    """

    _instance: Optional['RedisRepository'] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern: only one instance per application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize repository (only once due to singleton)."""
        if not RedisRepository._initialized:
            self.client: Optional[aioredis.Redis] = None
            self._pool: Optional[aioredis.ConnectionPool] = None
            RedisRepository._initialized = True
            logger.info("RedisRepository initialized (singleton)")

    async def connect(self) -> None:
        """
        Establish connection to Redis with connection pool.

        Creates connection pool with configured max_connections and timeout.
        Verifies connectivity with PING command.

        Raises:
            RedisConnectionError: If connection fails after retries
        """
        if self.client is not None:
            logger.warning("Redis client already connected, skipping reconnect")
            return

        try:
            logger.info(
                f"Connecting to Redis at {config.REDIS_URL} "
                f"(max_connections={config.REDIS_MAX_CONNECTIONS})"
            )

            # Create connection pool
            self._pool = aioredis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_MAX_CONNECTIONS,
                decode_responses=True,  # Auto-decode bytes to str
                encoding='utf-8',
                socket_connect_timeout=5,  # 5 seconds connection timeout
                socket_keepalive=True,
                retry_on_timeout=True
            )

            # Create Redis client with pool
            self.client = aioredis.Redis(connection_pool=self._pool)

            # Verify connection with PING
            await self._verify_connection()

            logger.info("✅ Redis connection established successfully")

        except RedisConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to Redis: {e}")
            raise RedisConnectionError(f"Redis connection failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(RedisConnectionError),
        reraise=True
    )
    async def _verify_connection(self) -> None:
        """
        Verify Redis connection with PING command (with retry).

        Raises:
            RedisConnectionError: If PING fails after 3 attempts
        """
        if self.client is None:
            raise RedisConnectionError("Client not initialized")

        try:
            response = await self.client.ping()
            if not response:
                raise RedisConnectionError("PING returned False")
        except RedisError as e:
            logger.warning(f"Redis PING failed: {e}")
            raise RedisConnectionError(f"PING verification failed: {e}") from e

    async def disconnect(self) -> None:
        """
        Close Redis connection and cleanup resources.

        Closes client connection and disposes connection pool.
        Safe to call multiple times (idempotent).
        """
        if self.client is None:
            logger.debug("Redis client not connected, skipping disconnect")
            return

        try:
            logger.info("Disconnecting from Redis...")
            await self.client.close()
            if self._pool:
                await self._pool.disconnect()
            self.client = None
            self._pool = None
            logger.info("✅ Redis disconnected successfully")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from Redis: {e}")
            # Don't raise - allow graceful shutdown

    async def health_check(self) -> dict:
        """
        Check Redis connection health.

        Returns:
            dict with status and optional error message
            Example: {"status": "healthy"} or {"status": "unhealthy", "error": "..."}
        """
        if self.client is None:
            return {"status": "unhealthy", "error": "Redis client not connected"}

        try:
            await self.client.ping()
            return {"status": "healthy"}
        except RedisError as e:
            logger.warning(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def get_info(self) -> dict:
        """
        Get Redis server information.

        Returns:
            dict with Redis INFO output (memory, clients, stats, etc.)
        """
        if self.client is None:
            raise RedisConnectionError("Redis client not connected")

        try:
            info = await self.client.info()
            return {
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except RedisError as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {"error": str(e)}
