"""
SSE Service for real-time spool updates streaming.

Provides event generator that subscribes to Redis pub/sub channel
and yields Server-Sent Events (SSE) for client consumption.

Handles:
- Client disconnect detection via request.is_disconnected()
- Proper subscription cleanup with context manager
- JSON parsing with error handling
- Graceful cancellation on client disconnect

Usage:
    from backend.services.sse_service import event_generator
    from sse_starlette import EventSourceResponse

    @router.get("/stream")
    async def sse_endpoint(request: Request, redis: Redis):
        return EventSourceResponse(
            event_generator(request, redis),
            headers={"X-Accel-Buffering": "no"},
            ping=15,
            send_timeout=30
        )
"""
import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any
from fastapi import Request
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


async def event_generator(
    request: Request,
    redis: aioredis.Redis
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Subscribe to Redis pub/sub channel and yield SSE events.

    Creates async generator that:
    1. Subscribes to "spools:updates" Redis channel
    2. Polls for messages with 1-second timeout (non-blocking)
    3. Checks for client disconnect every iteration
    4. Yields SSE events with "spool_update" event name
    5. Cleans up subscription on exit

    Args:
        request: FastAPI Request object for disconnect detection
        redis: Async Redis client for pub/sub subscription

    Yields:
        dict: SSE event with structure:
            {
                "event": "spool_update",
                "data": JSON string with event payload,
                "id": timestamp for Last-Event-ID support
            }

    Example event:
        {
            "event": "spool_update",
            "data": '{"event_type": "TOMAR", "tag_spool": "SPOOL-001", ...}',
            "id": "2026-01-27T15:30:45Z"
        }

    Raises:
        asyncio.CancelledError: When client disconnects (handled gracefully)
    """
    logger.info("SSE client connected - subscribing to spools:updates")

    async with redis.pubsub() as pubsub:
        try:
            # Subscribe to channel
            await pubsub.subscribe("spools:updates")

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info("SSE client disconnected - cleaning up")
                    break

                # Wait for message with timeout (non-blocking)
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                # Process message if received
                if message and message["type"] == "message":
                    try:
                        # Parse JSON data from Redis
                        data = json.loads(message["data"])

                        logger.debug(
                            f"SSE: Streaming {data.get('event_type')} event for {data.get('tag_spool')}"
                        )

                        # Yield SSE event
                        yield {
                            "event": "spool_update",
                            "data": json.dumps(data),
                            "id": data.get("timestamp")  # For Last-Event-ID support
                        }

                    except json.JSONDecodeError as e:
                        # Skip malformed messages
                        logger.warning(f"Malformed JSON in Redis message: {e}")
                        continue

                    except Exception as e:
                        # Log unexpected errors but continue streaming
                        logger.error(f"Error processing SSE message: {e}")
                        continue

        except asyncio.CancelledError:
            # Client disconnected - cleanup handled by context manager
            logger.info("SSE stream cancelled - client disconnected")
            raise

        except Exception as e:
            # Log unexpected errors during subscription
            logger.error(f"Unexpected error in SSE event generator: {e}")
            raise

        finally:
            # Context manager ensures unsubscribe and cleanup
            logger.info("SSE subscription cleanup complete")
