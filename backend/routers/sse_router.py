"""
SSE Router for real-time spool updates.

Provides Server-Sent Events (SSE) endpoint that streams Redis pub/sub
events to connected clients for real-time UI updates.

Success Criteria:
- Sub-10-second refresh latency (typically 150ms-1s)
- Redis pub/sub: ~100ms latency
- SSE delivery: ~50-500ms (network dependent)
- Keep-alive every 15 seconds
- Dead connection detection after 30 seconds

Endpoints:
    GET /api/sse/stream - SSE stream for spool updates
"""
from fastapi import APIRouter, Request, Depends
from sse_starlette import EventSourceResponse
from redis import asyncio as aioredis

from backend.services.sse_service import event_generator
from backend.repositories.redis_repository import RedisRepository

router = APIRouter(prefix="/api/sse", tags=["sse"])


def get_redis() -> aioredis.Redis:
    """
    Dependency: Get Redis client for SSE streaming.

    Returns:
        Redis: Async Redis client instance

    Raises:
        HTTPException: If Redis not connected
    """
    redis_repo = RedisRepository()
    client = redis_repo.get_client()

    if client is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Redis service unavailable"
        )

    return client


@router.get("/stream")
async def sse_stream(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    SSE endpoint for real-time spool updates.

    Streams state change events from Redis pub/sub channel to connected
    clients. Events include TOMAR, PAUSAR, COMPLETAR, and STATE_CHANGE.

    Args:
        request: FastAPI Request for disconnect detection
        redis: Async Redis client (injected)

    Returns:
        EventSourceResponse: SSE stream with headers:
            - Cache-Control: no-cache, no-transform
            - Connection: keep-alive
            - X-Accel-Buffering: no (disable nginx buffering)

    Response format:
        event: spool_update
        data: {"event_type": "TOMAR", "tag_spool": "SPOOL-001", ...}
        id: 2026-01-27T15:30:45Z

    Configuration:
        - ping=15: Keep-alive every 15 seconds
        - send_timeout=30: Detect dead connections after 30s

    Example:
        ```javascript
        const eventSource = new EventSource('/api/sse/stream');
        eventSource.addEventListener('spool_update', (event) => {
            const data = JSON.parse(event.data);
            console.log('Spool update:', data);
        });
        ```
    """
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }

    return EventSourceResponse(
        event_generator(request, redis),
        headers=headers,
        ping=15,  # Keep-alive every 15 seconds
        send_timeout=30  # Detect dead connections after 30s
    )
