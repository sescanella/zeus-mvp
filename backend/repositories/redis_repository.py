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

    Manages TWO connection pools:
    1. Main pool: For short-lived operations (locks, pub commands) - max 20 connections
    2. Pubsub pool: For long-lived SSE subscriptions - max 60 connections (30-50 workers + headroom)

    Thread-safe singleton pattern ensures single instance across application.

    Attributes:
        client: Async Redis client for operations (locks, pub)
        pubsub_client: Async Redis client for pubsub subscriptions (SSE)
        _pool: Main connection pool for operations
        _pubsub_pool: Dedicated connection pool for pubsub
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
            self.pubsub_client: Optional[aioredis.Redis] = None
            self._pool: Optional[aioredis.ConnectionPool] = None
            self._pubsub_pool: Optional[aioredis.ConnectionPool] = None
            RedisRepository._initialized = True
            logger.info("RedisRepository initialized (singleton)")

    def get_client(self) -> Optional[aioredis.Redis]:
        """
        Get the main Redis client instance for operations (locks, pub).

        Returns None if client not yet connected. This is the expected interface
        for FastAPI dependency injection (used in backend/core/dependency.py).

        Returns:
            Redis client instance if connected, None otherwise

        Warning:
            If client is None, caller must handle gracefully or wait for
            FastAPI startup event to complete connection.

        Usage:
            # In dependency.py
            redis_client = redis_repo.get_client()
            lock_service = RedisLockService(redis_client=redis_client)
        """
        if self.client is None:
            logger.warning(
                "Redis client requested but not yet connected. "
                "Ensure FastAPI startup event has completed."
            )
        return self.client

    def get_pubsub_client(self) -> Optional[aioredis.Redis]:
        """
        Get the dedicated Redis client for pubsub subscriptions (SSE).

        Uses separate connection pool to prevent SSE long-lived connections
        from exhausting the main pool used for lock operations.

        Returns:
            Redis pubsub client instance if connected, None otherwise

        Warning:
            If pubsub_client is None, caller must handle gracefully or wait for
            FastAPI startup event to complete connection.

        Usage:
            # In sse_router.py
            redis_pubsub = redis_repo.get_pubsub_client()
            async with redis_pubsub.pubsub() as pubsub:
                await pubsub.subscribe("spools:updates")
        """
        if self.pubsub_client is None:
            logger.warning(
                "Redis pubsub client requested but not yet connected. "
                "Ensure FastAPI startup event has completed."
            )
        return self.pubsub_client

    async def connect(self) -> None:
        """
        Establish connections to Redis with TWO connection pools:
        1. Main pool (20 connections) for short-lived operations (locks, pub)
        2. Pubsub pool (60 connections) for long-lived SSE subscriptions

        Verifies connectivity with PING commands.

        Raises:
            RedisConnectionError: If connection fails after retries
        """
        if self.client is not None and self.pubsub_client is not None:
            logger.warning("Redis clients already connected, skipping reconnect")
            return

        try:
            logger.info(
                f"Connecting to Redis at {config.REDIS_URL} "
                f"(main pool: {config.REDIS_POOL_MAX_CONNECTIONS} connections, "
                f"pubsub pool: 60 connections)"
            )

            # Create MAIN connection pool for operations (locks, pub commands)
            # Conservative limit (20) for short-lived operations
            self._pool = aioredis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_POOL_MAX_CONNECTIONS,  # 20 for Railway safety
                decode_responses=True,  # Auto-decode bytes to str
                encoding='utf-8',
                socket_connect_timeout=config.REDIS_SOCKET_CONNECT_TIMEOUT,  # Fail fast if unreachable
                socket_timeout=config.REDIS_SOCKET_TIMEOUT,  # Prevents hanging connections
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=config.REDIS_HEALTH_CHECK_INTERVAL  # Proactive health checks every 30s
            )

            # Create PUBSUB connection pool for SSE subscriptions
            # Larger pool (60) to accommodate 30-50 concurrent workers + headroom
            # Long-lived connections: each SSE client holds one connection until disconnect
            self._pubsub_pool = aioredis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=60,  # Support 50 workers + 10 headroom
                decode_responses=True,
                encoding='utf-8',
                socket_connect_timeout=config.REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=config.REDIS_SOCKET_TIMEOUT,
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=config.REDIS_HEALTH_CHECK_INTERVAL
            )

            # Create Redis clients with pools
            self.client = aioredis.Redis(connection_pool=self._pool)
            self.pubsub_client = aioredis.Redis(connection_pool=self._pubsub_pool)

            # Verify connections with PING
            await self._verify_connection()
            await self._verify_pubsub_connection()

            logger.info(
                "✅ Redis connections established successfully "
                "(main pool: 20, pubsub pool: 60)"
            )

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
        Verify main Redis connection with PING command (with retry).

        Raises:
            RedisConnectionError: If PING fails after 3 attempts
        """
        if self.client is None:
            raise RedisConnectionError("Main client not initialized")

        try:
            response = await self.client.ping()
            if not response:
                raise RedisConnectionError("Main client PING returned False")
        except RedisError as e:
            logger.warning(f"Redis main client PING failed: {e}")
            raise RedisConnectionError(f"Main client PING verification failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(RedisConnectionError),
        reraise=True
    )
    async def _verify_pubsub_connection(self) -> None:
        """
        Verify pubsub Redis connection with PING command (with retry).

        Raises:
            RedisConnectionError: If PING fails after 3 attempts
        """
        if self.pubsub_client is None:
            raise RedisConnectionError("Pubsub client not initialized")

        try:
            response = await self.pubsub_client.ping()
            if not response:
                raise RedisConnectionError("Pubsub client PING returned False")
        except RedisError as e:
            logger.warning(f"Redis pubsub client PING failed: {e}")
            raise RedisConnectionError(f"Pubsub client PING verification failed: {e}") from e

    async def disconnect(self) -> None:
        """
        Close Redis connections and cleanup resources for both pools.

        Closes both main and pubsub clients and disposes connection pools.
        Safe to call multiple times (idempotent).
        """
        try:
            logger.info("Disconnecting from Redis...")

            # Close main client
            if self.client is not None:
                await self.client.close()
                self.client = None

            # Close pubsub client
            if self.pubsub_client is not None:
                await self.pubsub_client.close()
                self.pubsub_client = None

            # Disconnect pools
            if self._pool:
                await self._pool.disconnect()
                self._pool = None

            if self._pubsub_pool:
                await self._pubsub_pool.disconnect()
                self._pubsub_pool = None

            logger.info("✅ Redis disconnected successfully (both pools)")
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

    def get_connection_stats(self) -> dict:
        """
        Get connection pool statistics for monitoring (both main and pubsub pools).

        Returns:
            dict with pool statistics for both pools.
            Example: {
                "status": "ok",
                "main_pool": {
                    "max_connections": 20,
                    "pool_created": true
                },
                "pubsub_pool": {
                    "max_connections": 60,
                    "pool_created": true
                },
                "alert": null
            }
        """
        try:
            main_pool_info = {
                "max_connections": 0,
                "pool_created": False
            }
            pubsub_pool_info = {
                "max_connections": 0,
                "pool_created": False
            }

            if self._pool is not None:
                main_pool_info = {
                    "max_connections": self._pool.max_connections,
                    "pool_created": True
                }

            if self._pubsub_pool is not None:
                pubsub_pool_info = {
                    "max_connections": self._pubsub_pool.max_connections,
                    "pool_created": True
                }

            # Determine alert status
            if not main_pool_info["pool_created"] or not pubsub_pool_info["pool_created"]:
                alert = "CRITICAL"
                status = "pool_not_initialized"
            else:
                alert = None
                status = "ok"

            return {
                "status": status,
                "main_pool": main_pool_info,
                "pubsub_pool": pubsub_pool_info,
                "alert": alert
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {
                "status": "error",
                "error": str(e),
                "alert": "ERROR"
            }
