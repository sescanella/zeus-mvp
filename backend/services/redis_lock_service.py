"""
Redis lock service for atomic spool occupation.

Implements distributed locking pattern using Redis SET NX EX for atomic operations.
Prevents race conditions in concurrent TOMAR operations.

Key patterns:
- SET NX EX: Atomic lock acquisition with automatic expiration
- Lua script: Safe lock release with ownership verification
- Lock tokens: UUID-based tokens prevent accidental release

Reference:
- Research: .planning/phases/02-core-location-tracking/02-RESEARCH.md
- Pattern: SET with NX (if not exists) and EX (expiration) flags
"""
import logging
import uuid
from typing import Optional
from redis import asyncio as aioredis
from redis.exceptions import RedisError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from backend.config import config
from backend.exceptions import SpoolOccupiedError, LockExpiredError
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets
from datetime import datetime

logger = logging.getLogger(__name__)

# Lua script for safe lock release with ownership verification
# Source: Redis lock best practices (02-RESEARCH.md lines 233-240)
RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisLockService:
    """
    Service for atomic Redis lock operations on spool occupation.

    Implements distributed locking with:
    - Atomic lock acquisition (SET NX EX)
    - Safe lock release (Lua script with ownership check)
    - Lock extension for long operations
    - Lock owner query for error messages

    Attributes:
        redis: Async Redis client instance
        default_ttl: Default lock TTL in seconds (from config)
    """

    def __init__(self, redis_client: aioredis.Redis, sheets_repository=None):
        """
        Initialize lock service with Redis client.

        Args:
            redis_client: Connected async Redis client (from RedisRepository.get_client())
            sheets_repository: SheetsRepository instance for lazy cleanup queries (optional)

        Note:
            The redis_client should be obtained via RedisRepository.get_client() method,
            typically through FastAPI dependency injection. The client must be connected
            (not None) for lock operations to work properly. Connection is established
            during FastAPI startup event lifecycle.

        Usage in FastAPI:
            ```python
            # In dependency.py
            redis_repo = RedisRepository()
            sheets_repo = SheetsRepository()
            lock_service = RedisLockService(redis_client=redis_repo.get_client(), sheets_repository=sheets_repo)
            ```

        Warning:
            If redis_client is None (not connected), all lock operations will fail.
            Ensure FastAPI startup event has completed before making lock requests.
        """
        self.redis = redis_client
        self.default_ttl = config.REDIS_LOCK_TTL_SECONDS
        self.sheets_repository = sheets_repository

    def _lock_key(self, tag_spool: str) -> str:
        """
        Generate Redis key for spool lock.

        Format: "spool_lock:{tag_spool}"

        Args:
            tag_spool: Spool identifier

        Returns:
            Redis key string
        """
        return f"spool_lock:{tag_spool}"

    def _lock_value(self, worker_id: int) -> str:
        """
        Generate unique lock value with worker ID, UUID token, and timestamp.

        Format: "{worker_id}:{uuid4}:{timestamp}"
        Example: "93:550e8400-e29b-41d4-a716-446655440000:21-01-2026 14:30:00"

        Args:
            worker_id: Worker identifier

        Returns:
            Lock value string with embedded worker_id, unique token, and timestamp
        """
        timestamp = format_datetime_for_sheets(now_chile())
        return f"{worker_id}:{uuid.uuid4()}:{timestamp}"

    def _parse_lock_value(self, lock_value: str) -> tuple[int, str]:
        """
        Parse lock value into worker_id and token.

        Args:
            lock_value: Lock value string (format: "{worker_id}:{token}:{timestamp}" or legacy "{worker_id}:{token}")

        Returns:
            Tuple of (worker_id, token)

        Raises:
            ValueError: If lock_value format is invalid

        Note:
            Supports both legacy format (worker_id:token) and new format (worker_id:token:timestamp).
            Timestamp is ignored in this method - see _parse_lock_timestamp for timestamp extraction.
        """
        try:
            parts = lock_value.split(":", 2)
            worker_id_str = parts[0]
            token = parts[1] if len(parts) >= 2 else ""
            return int(worker_id_str), token
        except (ValueError, AttributeError, IndexError) as e:
            raise ValueError(f"Invalid lock value format: {lock_value}") from e

    def _parse_lock_timestamp(self, lock_value: str) -> Optional[datetime]:
        """
        Parse timestamp from lock value.

        Args:
            lock_value: Lock value string (format: "{worker_id}:{token}:{timestamp}")

        Returns:
            datetime object if timestamp present, None for legacy locks

        Note:
            Legacy locks (format: worker_id:token) return None.
            New locks (format: worker_id:token:timestamp) return parsed datetime.
        """
        try:
            parts = lock_value.split(":", 2)
            if len(parts) >= 3:
                timestamp_str = parts[2]
                # Parse DD-MM-YYYY HH:MM:SS format
                return datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
            return None
        except (ValueError, AttributeError, IndexError) as e:
            logger.warning(f"Failed to parse timestamp from lock value: {lock_value}, error: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(RedisError),
        reraise=True
    )
    async def acquire_lock(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Acquire atomic lock on spool.

        v4.0 (persistent mode): Two-step acquisition with PERSIST command
        v3.0 (TTL mode): Traditional SET NX EX with expiration

        Atomic operation prevents race conditions:
        - If lock doesn't exist: set lock and return token
        - If lock exists: raise SpoolOccupiedError with current owner

        Args:
            tag_spool: Spool identifier
            worker_id: Worker attempting to acquire lock
            worker_nombre: Worker name for error messages
            ttl_seconds: Lock TTL (only used in v3.0 mode, ignored in v4.0 persistent mode)

        Returns:
            Lock token (UUID) for safe release

        Raises:
            SpoolOccupiedError: If spool already locked by another worker
            RedisError: If Redis operation fails (after retries)
        """
        lock_key = self._lock_key(tag_spool)
        lock_value = self._lock_value(worker_id)

        try:
            # Check if persistent locks enabled (v4.0) or TTL mode (v3.0)
            if config.REDIS_PERSISTENT_LOCKS:
                # v4.0: Two-step persistent lock acquisition
                # Step 1: Acquire with safety TTL (prevents orphaned locks if crash between SET and PERSIST)
                acquired = await self.redis.set(
                    lock_key,
                    lock_value,
                    nx=True,  # Only set if key doesn't exist
                    ex=config.REDIS_SAFETY_TTL  # 10-second safety TTL
                )

                if not acquired:
                    # Lock already exists
                    current_owner = await self.get_lock_owner(tag_spool)
                    if current_owner:
                        owner_id, _ = current_owner
                        raise SpoolOccupiedError(
                            tag_spool=tag_spool,
                            owner_id=owner_id,
                            owner_name=f"Worker {owner_id}"
                        )
                    else:
                        raise RedisError("Lock state changed during acquisition")

                # Step 2: Remove TTL to make persistent
                persist_result = await self.redis.persist(lock_key)

                if persist_result != 1:
                    # PERSIST failed (key disappeared between SET and PERSIST)
                    await self.redis.delete(lock_key)
                    raise RedisError("PERSIST command failed - key may have expired during acquisition")

                # Extract token from lock_value for return
                _, token = self._parse_lock_value(lock_value)

                logger.info(
                    f"✅ Persistent lock acquired: {tag_spool} by worker {worker_id} "
                    f"(no TTL, token: {token[:8]}...)"
                )

                return token

            else:
                # v3.0: Traditional TTL-based lock (backward compatibility)
                ttl = ttl_seconds or self.default_ttl

                acquired = await self.redis.set(
                    lock_key,
                    lock_value,
                    nx=True,  # Only set if key doesn't exist
                    ex=ttl    # Auto-expire after TTL seconds
                )

                if not acquired:
                    current_owner = await self.get_lock_owner(tag_spool)
                    if current_owner:
                        owner_id, _ = current_owner
                        raise SpoolOccupiedError(
                            tag_spool=tag_spool,
                            owner_id=owner_id,
                            owner_name=f"Worker {owner_id}"
                        )
                    else:
                        raise RedisError("Lock state changed during acquisition")

                # Extract token from lock_value for return
                _, token = self._parse_lock_value(lock_value)

                logger.info(
                    f"✅ Lock acquired: {tag_spool} by worker {worker_id} "
                    f"(TTL: {ttl}s, token: {token[:8]}...)"
                )

                return token

        except SpoolOccupiedError:
            # Re-raise occupation errors without retry
            raise
        except RedisError as e:
            logger.warning(f"Redis error acquiring lock for {tag_spool}: {e}")
            raise

    async def release_lock(self, tag_spool: str, worker_id: int, lock_token: str) -> bool:
        """
        Release lock safely using Lua script with ownership verification.

        Only deletes lock if the stored value matches our token.
        Prevents accidental release of locks acquired by other workers.

        Args:
            tag_spool: Spool identifier
            worker_id: Worker ID who owns the lock (for reconstructing lock_value)
            lock_token: Token returned from acquire_lock

        Returns:
            True if lock was released, False if lock not owned by us

        Raises:
            RedisError: If Redis operation fails
        """
        lock_key = self._lock_key(tag_spool)

        # Reconstruct full lock_value: "worker_id:token"
        # This matches the format stored by acquire_lock()
        lock_value = f"{worker_id}:{lock_token}"

        try:
            # Execute Lua script atomically
            # KEYS[1] = lock_key, ARGV[1] = expected lock value (worker_id:token)
            result = await self.redis.eval(
                RELEASE_SCRIPT,
                1,  # Number of keys
                lock_key,
                lock_value
            )

            released = result == 1

            if released:
                logger.info(
                    f"✅ Lock released: {tag_spool} by worker {worker_id} "
                    f"(token: {lock_token[:8]}...)"
                )
            else:
                logger.warning(
                    f"⚠️ Lock not released: {tag_spool} - not owned by worker {worker_id} "
                    f"(token: {lock_token[:8]}...)"
                )

            return released

        except RedisError as e:
            logger.error(f"Redis error releasing lock for {tag_spool}: {e}")
            raise

    async def extend_lock(
        self,
        tag_spool: str,
        lock_token: str,
        additional_seconds: int
    ) -> bool:
        """
        Extend lock TTL for long operations.

        Checks ownership before extending to prevent extending others' locks.

        Args:
            tag_spool: Spool identifier
            lock_token: Token from acquire_lock
            additional_seconds: Additional TTL seconds to add

        Returns:
            True if lock extended, False if lock not owned

        Raises:
            LockExpiredError: If lock no longer exists
            RedisError: If Redis operation fails
        """
        lock_key = self._lock_key(tag_spool)

        try:
            # Get current lock value
            current_value = await self.redis.get(lock_key)

            if current_value is None:
                raise LockExpiredError(tag_spool)

            # Verify ownership by checking if token matches
            if lock_token not in current_value:
                logger.warning(
                    f"Cannot extend lock for {tag_spool}: "
                    f"not owned by token {lock_token[:8]}..."
                )
                return False

            # Get current TTL and add additional seconds
            current_ttl = await self.redis.ttl(lock_key)
            if current_ttl < 0:
                # Key has no expiration or doesn't exist
                raise LockExpiredError(tag_spool)

            new_ttl = current_ttl + additional_seconds
            await self.redis.expire(lock_key, new_ttl)

            logger.info(
                f"✅ Lock extended: {tag_spool} - "
                f"TTL: {current_ttl}s → {new_ttl}s"
            )

            return True

        except LockExpiredError:
            raise
        except RedisError as e:
            logger.error(f"Redis error extending lock for {tag_spool}: {e}")
            raise

    async def get_lock_owner(self, tag_spool: str) -> Optional[tuple[int, str]]:
        """
        Query current lock owner.

        Args:
            tag_spool: Spool identifier

        Returns:
            Tuple of (worker_id, token) if locked, None if not locked

        Raises:
            RedisError: If Redis operation fails
        """
        lock_key = self._lock_key(tag_spool)

        try:
            lock_value = await self.redis.get(lock_key)

            if lock_value is None:
                return None

            # Parse lock value
            worker_id, token = self._parse_lock_value(lock_value)
            return (worker_id, token)

        except ValueError as e:
            logger.error(f"Failed to parse lock value for {tag_spool}: {e}")
            return None
        except RedisError as e:
            logger.error(f"Redis error getting lock owner for {tag_spool}: {e}")
            raise
