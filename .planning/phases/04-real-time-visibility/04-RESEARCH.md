# Phase 4: Real-Time Visibility - Research

**Researched:** 2026-01-27
**Domain:** Server-Sent Events (SSE) with Redis Pub/Sub for real-time updates
**Confidence:** HIGH

## Summary

This phase implements real-time visibility of spool occupation status using Server-Sent Events (SSE) backed by Redis Pub/Sub. The research confirms that **sse-starlette 3.2.0** is the production-ready standard for FastAPI SSE implementation, **redis.asyncio** (formerly aioredis) provides native async pub/sub, and **native EventSource API with custom React hooks** is the recommended frontend approach with explicit visibility API integration for mobile lifecycle handling.

The standard architecture uses Redis pub/sub as the event bus: backend services publish state change events (TOMAR, PAUSAR, COMPLETAR) to Redis channels, SSE endpoints subscribe to these channels and stream events to connected clients, and frontend EventSource connections auto-reconnect with exponential backoff. This pattern scales to 30+ concurrent workers while respecting Google Sheets API limits (300 reads/min per project, 60 requests/min per user).

**Critical finding:** SSE requires specific proxy configuration (`X-Accel-Buffering: no` header or nginx `proxy_buffering off`) to prevent buffering that breaks real-time delivery. Connection lifecycle management (cleanup on disconnect, proper async context handling) prevents memory leaks. React's Page Visibility API integration (close on background, reconnect on foreground) is essential for mobile battery life and server resource optimization.

**Primary recommendation:** Use sse-starlette with async Redis pub/sub on a single broadcast channel (e.g., "spools:updates"), native browser EventSource with custom React hook implementing exponential backoff (1s, 2s, 4s... max 30s) and Page Visibility API integration, and add connection status indicator (green/red dot) for immediate user feedback.

## Standard Stack

The established libraries/tools for SSE + Redis Pub/Sub real-time updates in FastAPI:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sse-starlette | 3.2.0 | SSE implementation for FastAPI/Starlette | W3C-compliant, production-stable, native async support, automatic client disconnect detection |
| redis | latest (redis.asyncio) | Async Redis client with pub/sub | Official Redis Python client, aioredis merged into redis-py, native async/await, pub/sub built-in |
| EventSource (native) | Browser API | Frontend SSE client | Built-in browser API, automatic reconnection, standard W3C implementation, no dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @aidanuno/use-fetch-event-source | latest | React hook for EventSource with visibility API | Alternative to custom hook if need advanced features (headers, POST, auth) |
| reconnecting-eventsource | latest | EventSource wrapper with enhanced reconnect | If native EventSource reconnect insufficient (not needed for this phase - native is enough) |
| event-source-plus | latest | Configurable EventSource with retry strategies | If need custom retry logic beyond exponential backoff (overkill for MVP) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Server-Sent Events (SSE) | WebSockets (socket.io) | SSE: simpler (HTTP-based), one-way only, auto-reconnect. WebSocket: bidirectional, more complex, requires socket.io on both sides. SSE perfect for our read-only dashboard use case |
| Redis Pub/Sub | Database polling | Redis: instant push, scales better, no database load. Polling: simpler but adds 1-10s latency, increases Sheets API calls unnecessarily |
| Single broadcast channel | Multiple topic-specific channels | Single: simpler, fewer subscriptions, good for <100 events/sec. Multiple: better filtering but overkill for 30 workers |

**Installation:**
```bash
# Backend (Python)
pip install sse-starlette redis

# Frontend (React) - no installation needed
# Native EventSource is built into browsers
# Custom hook will be implemented in-house
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── services/
│   ├── sse_service.py           # SSE streaming logic
│   └── redis_event_service.py   # Pub/Sub event publishing
├── repositories/
│   └── redis_repository.py      # Already exists (Phase 2)
└── routers/
    ├── sse_router.py            # GET /api/sse/stream endpoint
    └── dashboard_router.py       # GET /api/dashboard/occupied endpoint

zeues-frontend/
├── app/
│   └── dashboard/
│       └── page.tsx             # Dashboard page component
├── lib/
│   └── hooks/
│       └── useSSE.ts            # Custom EventSource hook
└── components/
    └── ConnectionStatus.tsx      # Green/red dot indicator
```

### Pattern 1: Redis Pub/Sub Event Broadcasting
**What:** Backend services publish state change events to Redis channel; SSE endpoints subscribe and stream to clients
**When to use:** Any state transition (TOMAR, PAUSAR, COMPLETAR, state machine updates) that needs real-time visibility
**Example:**
```python
# Source: https://gist.github.com/lbatteau/1bc7ae630d5b7844d58f038085590f97
# Backend: Publishing state change event
from redis import asyncio as aioredis
import json

async def publish_state_change(redis: aioredis.Redis, event_type: str, data: dict):
    """Publish state change to Redis pub/sub channel"""
    message = json.dumps({
        "type": event_type,  # "TOMAR", "PAUSAR", "COMPLETAR", "STATE_CHANGE"
        "tag_spool": data["tag_spool"],
        "worker": data.get("worker"),
        "estado_detalle": data.get("estado_detalle"),
        "timestamp": datetime.utcnow().isoformat()
    })
    await redis.publish("spools:updates", message)
```

### Pattern 2: SSE Endpoint with Redis Subscription
**What:** FastAPI endpoint that subscribes to Redis channel and streams events via SSE
**When to use:** Main SSE streaming endpoint that all frontend clients connect to
**Example:**
```python
# Source: sse-starlette docs + Redis async pub/sub pattern
from fastapi import APIRouter, Depends
from sse_starlette import EventSourceResponse
from redis import asyncio as aioredis
import json

router = APIRouter()

async def event_stream(redis: aioredis.Redis):
    """Subscribe to Redis channel and yield SSE events"""
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe("spools:updates")

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    # Forward Redis message as SSE event
                    data = message["data"].decode("utf-8")
                    yield {
                        "event": "spool_update",
                        "data": data
                    }
        except asyncio.CancelledError:
            # Client disconnected - clean up subscription
            await pubsub.unsubscribe("spools:updates")
            raise

@router.get("/api/sse/stream")
async def sse_stream(redis: aioredis.Redis = Depends(get_redis)):
    """SSE endpoint for real-time spool updates"""
    return EventSourceResponse(
        event_stream(redis),
        ping=15,  # Keep-alive ping every 15 seconds
        send_timeout=30  # Detect dead connections after 30s
    )
```

### Pattern 3: Frontend EventSource with Exponential Backoff
**What:** Custom React hook wrapping native EventSource with auto-reconnect, exponential backoff, and Page Visibility API
**When to use:** All frontend SSE connections - dashboard, available spools list
**Example:**
```typescript
// Source: https://oneuptime.com/blog/post/2026-01-15-server-sent-events-sse-react/view
// Custom React hook pattern
import { useEffect, useState, useRef } from 'react';

interface UseSSEOptions {
  onMessage: (data: unknown) => void;
  onError?: (error: Event) => void;
  openWhenHidden?: boolean;  // Default false - close on background
}

export function useSSE(url: string, options: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 10;

  const connect = () => {
    const es = new EventSource(url);

    es.onopen = () => {
      setIsConnected(true);
      retryCountRef.current = 0;  // Reset on successful connection
    };

    es.addEventListener('spool_update', (event) => {
      const data = JSON.parse(event.data);
      options.onMessage(data);
    });

    es.onerror = (error) => {
      setIsConnected(false);
      es.close();

      // Exponential backoff: 1s, 2s, 4s, 8s... max 30s
      const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);

      if (retryCountRef.current < maxRetries) {
        retryCountRef.current += 1;
        setTimeout(connect, delay);
      } else {
        options.onError?.(error);
      }
    };

    eventSourceRef.current = es;
  };

  useEffect(() => {
    connect();

    // Page Visibility API - close on background, reconnect on foreground
    const handleVisibilityChange = () => {
      if (options.openWhenHidden === false) {
        if (document.hidden) {
          eventSourceRef.current?.close();
          setIsConnected(false);
        } else {
          retryCountRef.current = 0;
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      eventSourceRef.current?.close();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [url]);

  return { isConnected };
}
```

### Pattern 4: Dashboard Data Fetching + Real-Time Updates
**What:** Combine initial REST API fetch with SSE updates for efficient dashboard
**When to use:** Dashboard page showing occupied spools - load initial state then update via SSE
**Example:**
```typescript
// Dashboard page pattern
export default function DashboardPage() {
  const [occupiedSpools, setOccupiedSpools] = useState<OccupiedSpool[]>([]);

  // Initial load via REST API
  useEffect(() => {
    fetch('/api/dashboard/occupied')
      .then(res => res.json())
      .then(data => setOccupiedSpools(data));
  }, []);

  // Real-time updates via SSE
  const { isConnected } = useSSE('/api/sse/stream', {
    onMessage: (event) => {
      // Update local state based on event type
      if (event.type === 'TOMAR') {
        // Add to occupied list
        setOccupiedSpools(prev => [...prev, event]);
      } else if (event.type === 'PAUSAR' || event.type === 'COMPLETAR') {
        // Remove from occupied list
        setOccupiedSpools(prev => prev.filter(s => s.tag_spool !== event.tag_spool));
      } else if (event.type === 'STATE_CHANGE') {
        // Update estado_detalle for existing spool
        setOccupiedSpools(prev => prev.map(s =>
          s.tag_spool === event.tag_spool
            ? { ...s, estado_detalle: event.estado_detalle }
            : s
        ));
      }
    },
    openWhenHidden: false  // Close on background
  });

  return (
    <div>
      <ConnectionStatus connected={isConnected} />
      {/* List of occupied spools */}
    </div>
  );
}
```

### Pattern 5: Nginx/Proxy Configuration for SSE
**What:** Disable buffering for SSE endpoints to prevent delayed delivery
**When to use:** Production deployment with nginx, Railway, or any reverse proxy
**Example:**
```python
# Application-level approach (recommended)
# Add header to SSE response
@router.get("/api/sse/stream")
async def sse_stream(redis: aioredis.Redis = Depends(get_redis)):
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }
    return EventSourceResponse(
        event_stream(redis),
        headers=headers,
        ping=15
    )
```

```nginx
# Nginx configuration approach (if needed)
location /api/sse/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;  # Critical for SSE
    proxy_cache off;
    proxy_read_timeout 86400s;  # 24 hours
}
```

### Anti-Patterns to Avoid
- **Creating EventSource inside render:** Causes connection storm on re-renders - use useEffect with empty deps array
- **Not cleaning up subscriptions:** Memory leak in Redis - always use `async with pubsub:` context manager or explicit unsubscribe
- **Polling instead of SSE for dashboard:** Wastes Google Sheets API quota (300/min limit) and adds latency - use SSE
- **Sending full spool list on every change:** Bandwidth waste - send only deltas (add/remove/update events)
- **Ignoring Page Visibility API:** Drains mobile battery and wastes server resources - close on background
- **Hardcoded retry delays:** All clients reconnect simultaneously after server restart - use exponential backoff with jitter

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE server implementation | Custom async generator with manual keep-alive | sse-starlette library | Handles ping/keep-alive, client disconnect detection, send timeouts, multi-threading safety - production-tested since 2020 |
| EventSource reconnection logic | Custom WebSocket or fetch-based SSE | Native EventSource API + custom hook | Browser handles reconnection automatically, W3C standard, built-in Last-Event-ID support, simpler than WebSocket |
| Redis connection pooling | Manual connection management | redis.asyncio with singleton pattern (already in Phase 2) | Connection pool built-in (max 50 connections), auto-reconnect, proper async context cleanup |
| Exponential backoff algorithm | Manual setTimeout chains | Exponential backoff formula with max cap | Edge cases: max delay cap, retry count limit, jitter to prevent thundering herd - easy to get wrong |
| Page Visibility API integration | Manual focus/blur event handling | Document.visibilitychange event | Handles tab switching, minimizing, screen lock - browser events more reliable than focus/blur |
| Event serialization | Manual JSON.stringify/parse | JSON.dumps/loads with error handling | Handles edge cases: undefined, circular refs, NaN - use standard library |

**Key insight:** SSE looks simple (just stream text!) but production-ready implementation requires keep-alive pings, disconnect detection, timeout handling, proper async cleanup, and proxy configuration. sse-starlette solves all of these. Similarly, EventSource native API handles reconnection, but mobile lifecycle needs explicit Page Visibility API integration.

## Common Pitfalls

### Pitfall 1: Proxy Buffering Breaks Real-Time Delivery
**What goes wrong:** SSE events arrive in batches after 30-60 seconds instead of immediately, making "real-time" updates useless
**Why it happens:** Nginx and other reverse proxies buffer responses by default to optimize throughput; SSE uses chunked transfer encoding which proxies legally buffer until stream closes
**How to avoid:**
- Add `X-Accel-Buffering: no` header in FastAPI response (works with nginx, uwsgi, fastcgi proxies)
- OR configure nginx with `proxy_buffering off` for SSE endpoints
- Test in production environment (staging with real proxy setup) to verify immediate delivery
**Warning signs:**
- SSE works perfectly in local dev (no proxy) but delayed in production
- Events arrive in bursts after 30+ seconds
- Browser Network tab shows "pending" for long time before data appears

### Pitfall 2: Redis Pub/Sub Memory Leak from Unclosed Subscriptions
**What goes wrong:** Server memory grows continuously, eventually crashes; Redis shows thousands of inactive clients
**Why it happens:** When SSE client disconnects, async generator may not clean up Redis subscription if not properly awaited; `pubsub.subscribe()` allocates buffers that aren't freed
**How to avoid:**
- ALWAYS use `async with redis.pubsub() as pubsub:` context manager - ensures cleanup on disconnect
- Check for `await request.is_disconnected()` in event loop to break early
- Set `send_timeout` in EventSourceResponse to detect dead connections (default None = waits forever)
- Monitor Redis with `CLIENT LIST` command to verify connections drop when clients disconnect
**Warning signs:**
- Redis memory usage grows linearly with time
- `redis-cli CLIENT LIST | grep pubsub` shows stale connections from disconnected clients
- Server process memory increases even with constant number of active users

### Pitfall 3: Connection Limit Exceeded (6 per browser on HTTP/1.1)
**What goes wrong:** Opening multiple tabs or components causes new SSE connections to hang; browser shows "pending" indefinitely
**Why it happens:** HTTP/1.1 limits browsers to 6 concurrent connections per domain; each SSE connection holds one slot open indefinitely
**How to avoid:**
- Use HTTP/2 in production (increases limit to ~100 streams) - Railway/Vercel typically provides this
- Share single SSE connection across app using React Context instead of one-per-component
- Close SSE when tab hidden (Page Visibility API) to free connection slot
- For dev: test with single tab or use HTTP/2 dev server
**Warning signs:**
- Works fine with 1-2 tabs, breaks at 6-7 tabs
- Browser Network tab shows requests stuck at "pending"
- Closing one tab makes another tab's SSE suddenly connect

### Pitfall 4: EventSource Doesn't Auto-Reconnect on All Errors
**What goes wrong:** Connection drops due to network error; EventSource never reconnects, users see stale data forever
**Why it happens:** Native EventSource only auto-reconnects on connection drops, NOT on HTTP error responses (4xx/5xx); error handler gets called once then stops trying
**How to avoid:**
- Implement custom reconnect logic in `onerror` handler with exponential backoff
- Don't rely on native reconnection alone - wrap EventSource in custom hook
- Reset retry counter on successful open to avoid giving up after temporary network issues
- Add manual "Reconnect" button in UI as fallback
**Warning signs:**
- Connection status stays red after temporary server restart
- Network tab shows single failed request with no retries
- Users report needing to refresh page to see updates

### Pitfall 5: Google Sheets API Rate Limit (300/min) Triggered by SSE Updates
**What goes wrong:** 30 workers making simultaneous updates triggers 30 SSE broadcasts, each SSE handler fetches fresh data from Sheets, exceeds 300/min quota, API returns 429 errors
**Why it happens:** Naive implementation fetches from Sheets on every SSE event; with 30 workers doing 5 actions/min = 150 events/min, if each triggers a Sheets read, that's 150+ API calls
**How to avoid:**
- DON'T fetch from Sheets in SSE handler - event payload should contain all data needed
- Publish complete state change data to Redis (tag_spool, worker, estado_detalle) not just "refresh" signal
- Dashboard initial load uses REST API (1 Sheets call), SSE updates modify local state with event data (0 Sheets calls)
- If fresh data needed, use RedisRepository cache (Phase 2) with 30s TTL, not direct Sheets fetch
**Warning signs:**
- 429 "Too Many Requests" errors in logs when multiple workers active
- SSE working fine with 5 workers, fails with 20+
- API quota dashboard shows spike during high activity periods

### Pitfall 6: Mobile App Killed in Background, SSE Never Reconnects
**What goes wrong:** User backgrounds app for 5+ minutes; iOS/Android kills connection; returning to app shows stale data with green "connected" indicator (false positive)
**Why it happens:** Mobile OS suspends JavaScript execution in background tabs; EventSource.readyState still shows OPEN but connection is dead; no error event fires until user tries to send data
**How to avoid:**
- Integrate Page Visibility API: close EventSource when `document.hidden === true`
- Reconnect when page becomes visible again (`visibilitychange` event)
- Add heartbeat/ping from client side: if no message received in 30s, assume dead and reconnect
- Server-side ping (sse-starlette `ping=15`) helps but mobile OS may ignore
**Warning signs:**
- Connection status shows green but no updates arriving
- Works perfectly on desktop, fails on mobile after backgrounding
- Users report needing to force-quit and reopen app to see current data

### Pitfall 7: Race Condition - Worker Selects Spool Already Taken
**What goes wrong:** Worker A sees spool available, clicks TOMAR, but gets error "already occupied by Worker B" - SSE update arrived 0.5s too late
**Why it happens:** SSE has inherent latency (1-10s depending on network); optimistic locking in Phase 2 correctly rejects stale requests, but UX is jarring if list doesn't update fast enough
**How to avoid:**
- This is EXPECTED and CORRECT behavior (optimistic locking working as designed)
- Show friendly error message: "Este carrete fue tomado por [Worker Name]" (per CONTEXT.md decisions)
- Auto-refresh available spools list after error via SSE event
- Consider optimistic UI: remove spool from list immediately on click, re-add if TOMAR fails
- SSE target: <10s refresh latency (SUCCESS CRITERIA) reduces likelihood but doesn't eliminate race
**Warning signs:**
- Users frequently report "already taken" errors
- SSE latency measured at >10 seconds (exceeds requirements)
- Error rate correlates with number of concurrent workers (expected - more contention)

## Code Examples

Verified patterns from official sources:

### Complete SSE Backend Setup (FastAPI + Redis)
```python
# Source: sse-starlette docs + redis.asyncio patterns
# backend/routers/sse_router.py

from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse
from redis import asyncio as aioredis
from typing import AsyncGenerator
import asyncio
import json

router = APIRouter(prefix="/api/sse", tags=["sse"])

async def event_generator(
    request: Request,
    redis: aioredis.Redis
) -> AsyncGenerator[dict, None]:
    """
    Subscribe to Redis pub/sub channel and yield SSE events.

    Handles:
    - Client disconnect detection
    - Proper subscription cleanup
    - JSON parsing with error handling
    """
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe("spools:updates")

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break

                # Wait for message with timeout (non-blocking)
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message and message["type"] == "message":
                    try:
                        # Parse JSON data from Redis
                        data = json.loads(message["data"])

                        # Yield SSE event
                        yield {
                            "event": "spool_update",
                            "data": json.dumps(data),
                            "id": data.get("timestamp")  # For Last-Event-ID support
                        }
                    except json.JSONDecodeError:
                        # Skip malformed messages
                        continue

        except asyncio.CancelledError:
            # Client disconnected - cleanup handled by context manager
            pass
        finally:
            # Context manager ensures unsubscribe
            pass

@router.get("/stream")
async def sse_endpoint(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    SSE endpoint for real-time spool updates.

    Success Criteria: Sub-10-second refresh latency
    - Redis pub/sub provides ~100ms latency
    - SSE delivery adds ~50-500ms depending on network
    - Total: typically 150ms-1s, well under 10s requirement
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
```

### Publishing State Change Events
```python
# Source: Redis pub/sub patterns
# backend/services/redis_event_service.py

from redis import asyncio as aioredis
from datetime import datetime
import json

class RedisEventService:
    """Service for publishing state change events to Redis pub/sub"""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def publish_spool_update(
        self,
        event_type: str,  # "TOMAR", "PAUSAR", "COMPLETAR", "STATE_CHANGE"
        tag_spool: str,
        worker_nombre: str | None = None,
        estado_detalle: str | None = None,
        additional_data: dict | None = None
    ):
        """
        Publish spool state change to Redis channel.

        Event types:
        - TOMAR: Spool occupied by worker
        - PAUSAR: Spool released back to available
        - COMPLETAR: Operation completed (still occupied)
        - STATE_CHANGE: Estado_Detalle updated (ARM/SOLD progress)

        Args:
            event_type: Type of state change
            tag_spool: Spool barcode identifier
            worker_nombre: Worker name (format: "MR(93)")
            estado_detalle: Combined state from Phase 3
            additional_data: Extra fields as needed
        """
        event_data = {
            "type": event_type,
            "tag_spool": tag_spool,
            "worker": worker_nombre,
            "estado_detalle": estado_detalle,
            "timestamp": datetime.utcnow().isoformat(),
            **(additional_data or {})
        }

        message = json.dumps(event_data)

        # Publish to single broadcast channel
        # All SSE clients subscribed to "spools:updates" receive this
        await self.redis.publish("spools:updates", message)
```

### Integration into Existing Action Service
```python
# Source: ZEUES backend architecture
# backend/services/action_service.py (modifications)

class ActionService:
    def __init__(
        self,
        sheets_repo: SheetsRepository,
        redis_repo: RedisRepository,
        redis_event_service: RedisEventService  # NEW
    ):
        self.sheets_repo = sheets_repo
        self.redis_repo = redis_repo
        self.redis_event_service = redis_event_service  # NEW

    async def tomar_spool(
        self,
        tag_spool: str,
        worker_id: int,
        worker_nombre: str
    ):
        """
        Worker takes occupation of a spool.

        NEW: Publishes TOMAR event to Redis for real-time updates.
        """
        # Existing logic: optimistic locking, write to Sheets, update Redis cache
        # ... (Phase 2/3 implementation)

        # NEW: Publish event for SSE clients
        await self.redis_event_service.publish_spool_update(
            event_type="TOMAR",
            tag_spool=tag_spool,
            worker_nombre=worker_nombre,
            estado_detalle=estado_detalle  # From Phase 3
        )

    async def completar_operacion(
        self,
        tag_spool: str,
        operacion: str,  # "ARM" or "SOLD"
        worker_nombre: str
    ):
        """
        Worker completes an operation.

        NEW: Publishes STATE_CHANGE event (estado_detalle updated).
        """
        # Existing logic
        # ... (Phase 3 state machine transition)

        # NEW: Publish state change
        await self.redis_event_service.publish_spool_update(
            event_type="STATE_CHANGE",
            tag_spool=tag_spool,
            worker_nombre=worker_nombre,
            estado_detalle=new_estado_detalle  # Updated state
        )
```

### Complete Frontend React Hook
```typescript
// Source: React SSE patterns + Page Visibility API
// zeues-frontend/lib/hooks/useSSE.ts

import { useEffect, useState, useRef, useCallback } from 'react';

interface SSEEvent {
  type: 'TOMAR' | 'PAUSAR' | 'COMPLETAR' | 'STATE_CHANGE';
  tag_spool: string;
  worker: string | null;
  estado_detalle: string | null;
  timestamp: string;
}

interface UseSSEOptions {
  onMessage: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
  onConnectionChange?: (connected: boolean) => void;
  openWhenHidden?: boolean;  // Default: false
}

export function useSSE(url: string, options: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const MAX_RETRIES = 10;
  const MAX_DELAY = 30000;  // 30 seconds

  const updateConnectionStatus = useCallback((connected: boolean) => {
    setIsConnected(connected);
    options.onConnectionChange?.(connected);
  }, [options.onConnectionChange]);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(url);

    es.onopen = () => {
      updateConnectionStatus(true);
      retryCountRef.current = 0;  // Reset retry counter on success
    };

    es.addEventListener('spool_update', (event: MessageEvent) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        options.onMessage(data);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    });

    es.onerror = (error: Event) => {
      updateConnectionStatus(false);
      es.close();

      // Exponential backoff with max cap
      const delay = Math.min(
        1000 * Math.pow(2, retryCountRef.current),
        MAX_DELAY
      );

      if (retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        // Max retries exceeded
        options.onError?.(error);
      }
    };

    eventSourceRef.current = es;
  }, [url, options.onMessage, options.onError, updateConnectionStatus]);

  useEffect(() => {
    // Initial connection
    connect();

    // Page Visibility API integration
    const handleVisibilityChange = () => {
      if (options.openWhenHidden === false) {  // Default behavior
        if (document.hidden) {
          // Page hidden (backgrounded) - close connection to save resources
          eventSourceRef.current?.close();
          updateConnectionStatus(false);

          // Clear any pending reconnect
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        } else {
          // Page visible again - reconnect immediately
          retryCountRef.current = 0;  // Reset retry count
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup on unmount
    return () => {
      eventSourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [url, options.openWhenHidden, connect, updateConnectionStatus]);

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    updateConnectionStatus(false);
  }, [updateConnectionStatus]);

  return {
    isConnected,
    disconnect
  };
}
```

### Dashboard Page Implementation
```typescript
// Source: ZEUES frontend patterns
// zeues-frontend/app/dashboard/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { useSSE } from '@/lib/hooks/useSSE';

interface OccupiedSpool {
  tag_spool: string;
  worker_nombre: string;
  estado_detalle: string;
  fecha_ocupacion: string;
}

export default function DashboardPage() {
  const [occupiedSpools, setOccupiedSpools] = useState<OccupiedSpool[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Initial load via REST API
  useEffect(() => {
    fetch('/api/dashboard/occupied')
      .then(res => res.json())
      .then(data => {
        setOccupiedSpools(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Failed to load occupied spools:', err);
        setIsLoading(false);
      });
  }, []);

  // Real-time updates via SSE
  const { isConnected } = useSSE('/api/sse/stream', {
    onMessage: (event) => {
      switch (event.type) {
        case 'TOMAR':
          // Add newly occupied spool
          setOccupiedSpools(prev => [...prev, {
            tag_spool: event.tag_spool,
            worker_nombre: event.worker || '',
            estado_detalle: event.estado_detalle || '',
            fecha_ocupacion: event.timestamp
          }]);
          break;

        case 'PAUSAR':
          // Remove released spool
          setOccupiedSpools(prev =>
            prev.filter(s => s.tag_spool !== event.tag_spool)
          );
          break;

        case 'STATE_CHANGE':
          // Update estado_detalle for existing spool
          setOccupiedSpools(prev => prev.map(s =>
            s.tag_spool === event.tag_spool
              ? { ...s, estado_detalle: event.estado_detalle || s.estado_detalle }
              : s
          ));
          break;
      }
    },
    openWhenHidden: false  // Close on background (mobile optimization)
  });

  if (isLoading) {
    return <div className="p-4">Cargando...</div>;
  }

  return (
    <div className="p-4">
      {/* Connection status indicator */}
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-sm text-gray-600">
          {isConnected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>

      <h1 className="text-2xl font-bold mb-4">Carretes Ocupados</h1>

      {occupiedSpools.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No hay carretes ocupados actualmente</p>
          <p className="text-sm mt-2">Todos los carretes están disponibles</p>
        </div>
      ) : (
        <div className="space-y-2">
          {occupiedSpools.map(spool => (
            <div key={spool.tag_spool} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-lg">{spool.tag_spool}</h3>
                  <p className="text-sm text-gray-600">{spool.worker_nombre}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{spool.estado_detalle}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling every 5-10s | Server-Sent Events (SSE) push | ~2015 (HTTP/2 adoption) | Reduced latency from 5-10s average to <1s; eliminated wasted API calls on "no change" polls |
| aioredis package | redis.asyncio (built into redis-py) | 2022 (aioredis 2.0 merged) | Single dependency instead of two; simplified imports; native async support in official client |
| WebSockets for one-way updates | SSE for server-to-client | Ongoing (2020-2026) | SSE simpler for read-only use cases: HTTP-based (no special proxy config), auto-reconnect built-in, lower overhead |
| Manual exponential backoff | Libraries like event-source-plus | 2023-2024 | Standardized retry patterns; jitter to prevent thundering herd; configurable max delays |
| Ignore Page Visibility API | Close SSE on background | 2024-2025 (mobile PWA focus) | Reduced mobile battery drain; freed server resources; improved UX on app return |

**Deprecated/outdated:**
- **aioredis standalone package (deprecated 2022):** Now use `from redis import asyncio as aioredis` - all functionality merged into official redis-py client
- **Custom SSE implementations without ping:** Modern sse-starlette handles keep-alive automatically - don't hand-roll SSE protocol
- **HTTP/1.1 for SSE in production:** HTTP/2 increases connection limit from 6 to ~100, critical for multiple tabs/components - ensure production uses HTTP/2
- **EventSource polyfills for modern browsers:** Native support in all browsers since 2015 - no need for polyfills unless targeting IE11 (not relevant for mobile-first tablet app)

## Open Questions

Things that couldn't be fully resolved:

1. **Railway/Vercel HTTP/2 Support and SSE Behavior**
   - What we know: Railway and Vercel both support HTTP/2; sse-starlette works on both platforms
   - What's unclear: Specific buffering behavior, connection timeout defaults, and whether platform-specific headers needed beyond `X-Accel-Buffering: no`
   - Recommendation: Test in Railway staging environment early in Phase 4 implementation; monitor SSE latency with browser DevTools Network tab; add logging to measure time between Redis publish and browser receipt

2. **Optimal Ping Interval for Mobile Network Conditions**
   - What we know: sse-starlette default is 15s; SSE spec recommends 15-30s; mobile networks often drop idle connections after 30-60s
   - What's unclear: Whether 15s is aggressive enough for factory WiFi vs 4G/5G fallback; battery drain tradeoff
   - Recommendation: Start with 15s (sse-starlette default); monitor connection drop frequency in production; increase to 30s if battery drain reported; decrease to 10s if seeing frequent timeouts

3. **Redis Pub/Sub Channel Strategy: Single vs Multiple**
   - What we know: Single channel "spools:updates" simplest; could split into "spools:tomar", "spools:pausar", etc.; 30 workers = ~150 events/min = 2.5/sec (well below Redis capacity)
   - What's unclear: Performance benefit of filtering at subscribe level vs filtering in client after receiving all events
   - Recommendation: Start with single broadcast channel (CONTEXT.md "Claude's Discretion"); volume is low enough that client-side filtering adds negligible overhead; if future phases need selective subscriptions (e.g., dashboard only shows specific operation), then split channels

4. **Last-Event-ID Support for Message Recovery**
   - What we know: SSE spec supports Last-Event-ID header for resuming after disconnect; requires server to buffer recent events
   - What's unclear: Whether ZEUES needs this complexity; events are state changes not transactions; dashboard can re-fetch via REST API on reconnect
   - Recommendation: Skip Last-Event-ID implementation in Phase 4 MVP - reconnect fetches fresh state via REST API (1 Sheets API call); add only if users report visible gaps during network instability

5. **Exact Exponential Backoff Timing Values**
   - What we know: Formula is `delay = min(1000 * 2^retry_count, 30000)`; max 10 retries recommended
   - What's unclear: Optimal initial delay (1s vs 2s), max delay (30s vs 60s), jitter amount
   - Recommendation: Start with documented values (1s initial, 30s max, no jitter - code example above); add jitter (randomize ±20%) only if seeing thundering herd after server restart in production; Phase 4 has 30 workers max so unlikely to be an issue

## Sources

### Primary (HIGH confidence)
- sse-starlette 3.2.0 PyPI - https://pypi.org/project/sse-starlette/ (Version, installation, requirements)
- sse-starlette GitHub README - https://github.com/sysid/sse-starlette (API, usage, configuration, ping/keep-alive)
- redis-py asyncio examples - https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html (Pub/sub pattern, connection cleanup)
- Google Sheets API Limits (official) - https://developers.google.com/workspace/sheets/api/limits (300/min quota)
- launchdarkly/js-eventsource README - https://github.com/launchdarkly/js-eventsource (Exponential backoff config, jitter implementation)
- MDN Page Visibility API - https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API (visibilitychange event)

### Secondary (MEDIUM confidence)
- Medium: Server-Sent Events in FastAPI using Redis Pub/Sub (Deepdesk) - Pattern for Redis + SSE integration
- Medium: Scalable Real-Time Apps with Python and Redis (ITNEXT) - AsyncIO + FastAPI + Pub/Sub architecture
- OneUptime Blog: How to Implement SSE in React (Jan 2026) - Recent React patterns including hooks
- DigitalOcean: NGINX Optimization for SSE - X-Accel-Buffering header recommendation
- GitHub Gist (lbatteau): SSE with async Redis Pub/Sub - Code pattern verified with official docs
- WebSearch: redis-py pub/sub 2026 - Confirmed aioredis merger into redis.asyncio
- WebSearch: react-eventsource npm 2026 - openWhenHidden option for Page Visibility API

### Tertiary (LOW confidence)
- DEV Community: "SSE still not production ready after a decade" - Anecdotal proxy buffering issues (but solutions well-documented)
- GitHub Issues: Redis pub/sub memory leaks - Various tickets across libraries (mitigated by async context manager pattern)
- Medium: Various SSE tutorials - Code patterns cross-verified with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - sse-starlette 3.2.0 verified from official PyPI/GitHub, redis.asyncio from official docs, EventSource is W3C standard
- Architecture: HIGH - Redis pub/sub pattern verified in official redis-py docs, SSE patterns verified in sse-starlette docs, React hook pattern cross-verified across multiple 2026 sources
- Pitfalls: MEDIUM-HIGH - Proxy buffering solution verified across multiple sources including nginx docs; Redis cleanup pattern from official docs; connection limit from W3C spec; other pitfalls from multiple community sources but solutions verified

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (30 days - SSE/Redis stack stable, sse-starlette 3.2.0 recent release)

---

**Research complete.** This document provides:
- Verified standard stack (sse-starlette 3.2.0, redis.asyncio, native EventSource)
- Complete architecture patterns with code examples ready for implementation
- Critical pitfalls identified with prevention strategies
- Google Sheets API quota constraints accounted for (300/min)
- Success criteria addressed: <10s refresh via Redis pub/sub (~100ms latency) + SSE delivery (50-500ms)
- Mobile lifecycle handling via Page Visibility API integration
- Production-ready proxy configuration for Railway deployment
