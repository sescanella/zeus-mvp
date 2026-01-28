"""
Redis Event Publisher Service for real-time spool updates.

Publishes state change events to Redis pub/sub channel for SSE streaming.
Events include TOMAR, PAUSAR, COMPLETAR, and STATE_CHANGE notifications.

Usage:
    event_service = RedisEventService(redis_client)
    await event_service.publish_spool_update(
        event_type="TOMAR",
        tag_spool="SPOOL-001",
        worker_nombre="MR(93)",
        estado_detalle="ARM: En Progreso",
        additional_data={"operacion": "ARM"}
    )
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from backend.utils.date_formatter import format_datetime_for_sheets, now_chile
from redis import asyncio as aioredis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisEventService:
    """
    Service for publishing spool state change events to Redis pub/sub.

    Publishes JSON messages to "spools:updates" channel for real-time
    streaming to connected SSE clients.

    Attributes:
        redis_client: Async Redis client for pub/sub operations
        channel: Redis channel name for spool updates
    """

    CHANNEL = "spools:updates"

    def __init__(self, redis_client: aioredis.Redis):
        """
        Initialize event service with Redis client.

        Args:
            redis_client: Async Redis client instance
        """
        self.redis_client = redis_client
        self.channel = self.CHANNEL

    async def publish_spool_update(
        self,
        event_type: str,
        tag_spool: str,
        worker_nombre: str,
        estado_detalle: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish spool state change event to Redis channel.

        Creates JSON message with event details and publishes to
        "spools:updates" channel for SSE streaming.

        Args:
            event_type: Event type (TOMAR, PAUSAR, COMPLETAR, STATE_CHANGE)
            tag_spool: Spool identifier (TAG_SPOOL)
            worker_nombre: Worker name in format "INICIALES(ID)"
            estado_detalle: Current state description
            additional_data: Optional dict with extra event data

        Returns:
            bool: True if published successfully, False otherwise

        Example:
            >>> await service.publish_spool_update(
            ...     event_type="TOMAR",
            ...     tag_spool="SPOOL-001",
            ...     worker_nombre="MR(93)",
            ...     estado_detalle="ARM: En Progreso",
            ...     additional_data={"operacion": "ARM"}
            ... )
            True
        """
        try:
            # Build event payload
            event_payload = {
                "event_type": event_type,
                "tag_spool": tag_spool,
                "worker_nombre": worker_nombre,
                "estado_detalle": estado_detalle,
                "timestamp": format_datetime_for_sheets(now_chile())
            }

            # Merge additional data if provided
            if additional_data:
                event_payload.update(additional_data)

            # Serialize to JSON
            message = json.dumps(event_payload)

            # Publish to channel
            subscribers = await self.redis_client.publish(self.channel, message)

            logger.info(
                f"Published {event_type} event for {tag_spool} to {subscribers} subscribers"
            )

            return True

        except RedisError as e:
            logger.error(
                f"Failed to publish {event_type} event for {tag_spool}: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error publishing event for {tag_spool}: {str(e)}"
            )
            return False
