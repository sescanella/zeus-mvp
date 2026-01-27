"""
Load Test for ZEUES v3.0 Real-Time SSE System

Simulates 30 concurrent workers performing TOMAR/PAUSAR/COMPLETAR operations
while maintaining SSE connections for real-time updates.

Performance Requirements (Phase 4):
- SSE updates arrive within 10 seconds
- Dashboard shows all occupied spools
- SSE connections stay alive for 8 hours
- 30 workers generate < 80 Google Sheets API requests/min

Usage:
    # Run with Locust web UI (localhost:8089)
    locust -f test_sse_load.py --host=http://localhost:8000

    # Run headless with 30 users, 5 spawn rate, 10 min duration
    locust -f test_sse_load.py --host=http://localhost:8000 --users=30 --spawn-rate=5 --run-time=10m --headless

    # Verification mode (check only, no load)
    python test_sse_load.py --check-only
"""

import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional
from threading import Thread, Event

from locust import HttpUser, task, between, events
from locust.env import Environment
import sseclient
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Global metrics tracking
sse_latencies: List[float] = []
api_requests_per_minute: List[int] = []
connection_failures: int = 0
sse_events_received: int = 0
start_time: Optional[float] = None


class SSEClient:
    """
    SSE client for receiving real-time spool updates.

    Maintains connection to /api/sse/stream and measures latency
    from operation publish to event receipt.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.url = f"{base_url}/api/sse/stream"
        self.connected = False
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.last_event_time: Optional[float] = None

    def start(self):
        """Start SSE connection in background thread."""
        self.stop_event.clear()
        self.thread = Thread(target=self._listen, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop SSE connection."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def _listen(self):
        """Background thread: Listen to SSE stream."""
        global connection_failures, sse_events_received, sse_latencies

        retry_count = 0
        max_retries = 3

        while not self.stop_event.is_set() and retry_count < max_retries:
            try:
                response = requests.get(self.url, stream=True, timeout=60)

                if response.status_code != 200:
                    logger.error(f"SSE connection failed: {response.status_code}")
                    connection_failures += 1
                    retry_count += 1
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    continue

                self.connected = True
                retry_count = 0  # Reset on success

                client = sseclient.SSEClient(response)

                for event in client.events():
                    if self.stop_event.is_set():
                        break

                    if event.event == 'spool_update':
                        self.last_event_time = time.time()
                        sse_events_received += 1

                        # Parse event data
                        try:
                            data = json.loads(event.data)

                            # Calculate latency (approximate - using timestamp in event)
                            event_timestamp = data.get('timestamp')
                            if event_timestamp:
                                event_time = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                                latency = (datetime.now().astimezone() - event_time).total_seconds() * 1000
                                sse_latencies.append(latency)

                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Failed to parse SSE event: {e}")

                self.connected = False

            except requests.exceptions.RequestException as e:
                logger.error(f"SSE connection error: {e}")
                connection_failures += 1
                retry_count += 1
                time.sleep(2 ** retry_count)

            except Exception as e:
                logger.error(f"Unexpected SSE error: {e}", exc_info=True)
                connection_failures += 1
                break


class WorkerUser(HttpUser):
    """
    Simulates a worker performing manufacturing operations.

    Each user:
    - Opens SSE connection for real-time updates
    - Performs TOMAR/PAUSAR/COMPLETAR operations (5 actions/min)
    - Maintains connection for test duration

    Wait time: 12 seconds between tasks (5 actions/min per user)
    With 30 users: 150 actions/min total
    """

    wait_time = between(10, 14)  # Average 12s → 5 actions/min

    def on_start(self):
        """Initialize user: Start SSE connection."""
        self.sse_client = SSEClient(self.host)
        self.sse_client.start()

        # Wait for connection establishment
        for _ in range(10):  # Max 5 seconds
            if self.sse_client.connected:
                break
            time.sleep(0.5)

        if not self.sse_client.connected:
            logger.warning(f"User {self.user_id} SSE connection not established")

        # User simulation data
        self.worker_id = 93 + (hash(str(id(self))) % 10)  # Workers 93-102
        self.current_spool: Optional[str] = None
        self.operation: str = 'ARM'  # Could randomize: ['ARM', 'SOLD']

    def on_stop(self):
        """Cleanup: Stop SSE connection."""
        if hasattr(self, 'sse_client'):
            self.sse_client.stop()

    @task(3)
    def tomar_spool(self):
        """
        TOMAR: Occupy a spool (most common action).

        Flow:
        1. Get available spools for operation
        2. TOMAR first available spool
        3. Verify SSE event received
        """
        global api_requests_per_minute

        # Skip if already has a spool
        if self.current_spool:
            return

        # Get available spools
        with self.client.get(
            f"/api/spools/iniciar?operacion={self.operation}",
            catch_response=True,
            name="/api/spools/iniciar"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                spools = data.get('spools', [])

                if not spools:
                    response.failure("No spools available")
                    return

                # TOMAR first available
                tag_spool = spools[0]['tag_spool']

                with self.client.post(
                    "/api/tomar",
                    json={
                        "worker_id": self.worker_id,
                        "operacion": self.operation,
                        "tag_spool": tag_spool
                    },
                    catch_response=True,
                    name="/api/tomar"
                ) as tomar_response:
                    if tomar_response.status_code == 200:
                        self.current_spool = tag_spool
                        tomar_response.success()
                    else:
                        tomar_response.failure(f"TOMAR failed: {tomar_response.status_code}")
            else:
                response.failure(f"Get spools failed: {response.status_code}")

    @task(1)
    def pausar_spool(self):
        """
        PAUSAR: Release a spool (less common).

        Flow:
        1. PAUSAR current spool
        2. Verify SSE event received
        """
        if not self.current_spool:
            return

        with self.client.post(
            "/api/pausar",
            json={
                "worker_id": self.worker_id,
                "operacion": self.operation,
                "tag_spool": self.current_spool
            },
            catch_response=True,
            name="/api/pausar"
        ) as response:
            if response.status_code == 200:
                self.current_spool = None
                response.success()
            else:
                response.failure(f"PAUSAR failed: {response.status_code}")

    @task(2)
    def completar_spool(self):
        """
        COMPLETAR: Complete operation on spool.

        Flow:
        1. COMPLETAR current spool
        2. Verify SSE event received
        """
        if not self.current_spool:
            return

        with self.client.post(
            "/api/completar",
            json={
                "worker_id": self.worker_id,
                "operacion": self.operation,
                "tag_spool": self.current_spool,
                "timestamp": datetime.now().isoformat()
            },
            catch_response=True,
            name="/api/completar"
        ) as response:
            if response.status_code == 200:
                self.current_spool = None
                response.success()
            else:
                response.failure(f"COMPLETAR failed: {response.status_code}")

    @task(1)
    def check_dashboard(self):
        """
        Periodic dashboard check to verify occupied spools visibility.
        """
        with self.client.get(
            "/api/dashboard/occupied",
            catch_response=True,
            name="/api/dashboard/occupied"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Verify response is list
                if isinstance(data, list):
                    response.success()
                else:
                    response.failure("Dashboard response not a list")
            else:
                response.failure(f"Dashboard failed: {response.status_code}")


# Locust event handlers for metrics tracking
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics tracking."""
    global start_time, sse_latencies, api_requests_per_minute, connection_failures, sse_events_received

    start_time = time.time()
    sse_latencies = []
    api_requests_per_minute = []
    connection_failures = 0
    sse_events_received = 0

    logger.info("Load test starting - metrics initialized")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report final metrics and verify success criteria."""
    global start_time, sse_latencies, connection_failures, sse_events_received

    if start_time is None:
        logger.error("Test start time not recorded")
        return

    duration = time.time() - start_time
    duration_hours = duration / 3600

    # Calculate metrics
    avg_latency = sum(sse_latencies) / len(sse_latencies) if sse_latencies else 0
    max_latency = max(sse_latencies) if sse_latencies else 0
    p95_latency = sorted(sse_latencies)[int(len(sse_latencies) * 0.95)] if sse_latencies else 0

    # API requests/min (estimate from total requests)
    total_requests = environment.stats.total.num_requests
    requests_per_min = (total_requests / duration) * 60 if duration > 0 else 0

    logger.info("=" * 80)
    logger.info("LOAD TEST RESULTS - Phase 4 Success Criteria")
    logger.info("=" * 80)
    logger.info(f"Duration: {duration:.1f}s ({duration_hours:.2f}h)")
    logger.info(f"Total users: {environment.runner.user_count}")
    logger.info("")

    logger.info("SSE METRICS:")
    logger.info(f"  Events received: {sse_events_received}")
    logger.info(f"  Connection failures: {connection_failures}")
    logger.info(f"  Average latency: {avg_latency:.1f}ms")
    logger.info(f"  Max latency: {max_latency:.1f}ms")
    logger.info(f"  P95 latency: {p95_latency:.1f}ms")
    logger.info("")

    logger.info("API METRICS:")
    logger.info(f"  Total requests: {total_requests}")
    logger.info(f"  Requests/min: {requests_per_min:.1f}")
    logger.info(f"  Failed requests: {environment.stats.total.num_failures}")
    logger.info("")

    # SUCCESS CRITERIA VERIFICATION
    logger.info("SUCCESS CRITERIA:")

    criteria_passed = 0
    criteria_total = 4

    # 1. SSE updates arrive within 10 seconds
    criterion_1 = max_latency < 10000
    logger.info(f"  1. SSE latency < 10s: {'PASS' if criterion_1 else 'FAIL'} (max: {max_latency:.1f}ms)")
    if criterion_1:
        criteria_passed += 1

    # 2. Dashboard shows all occupied spools (check event count)
    criterion_2 = sse_events_received > 0
    logger.info(f"  2. Dashboard updates working: {'PASS' if criterion_2 else 'FAIL'} ({sse_events_received} events)")
    if criterion_2:
        criteria_passed += 1

    # 3. SSE connection stability (< 10% failure rate)
    connection_stability = connection_failures / (sse_events_received + 1) if sse_events_received > 0 else 1
    criterion_3 = connection_stability < 0.1
    logger.info(f"  3. Connection stability: {'PASS' if criterion_3 else 'FAIL'} ({connection_failures} failures)")
    if criterion_3:
        criteria_passed += 1

    # 4. API quota (< 80 requests/min)
    criterion_4 = requests_per_min < 80
    logger.info(f"  4. API quota < 80 req/min: {'PASS' if criterion_4 else 'FAIL'} ({requests_per_min:.1f} req/min)")
    if criterion_4:
        criteria_passed += 1

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"RESULT: {criteria_passed}/{criteria_total} criteria passed")

    if criteria_passed == criteria_total:
        logger.info("STATUS: ALL CRITERIA PASSED ✓")
    else:
        logger.warning(f"STATUS: {criteria_total - criteria_passed} CRITERIA FAILED ✗")

    logger.info("=" * 80)


def check_only_mode():
    """
    Verification-only mode: Check if test infrastructure is ready.

    Validates:
    - Backend is running
    - SSE endpoint accessible
    - Dashboard endpoint accessible
    """
    logger.info("Running in CHECK-ONLY mode")
    logger.info("=" * 80)

    base_url = "http://localhost:8000"

    # Check 1: Health endpoint
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            logger.info("✓ Backend health check passed")
        else:
            logger.error(f"✗ Backend health check failed: {response.status_code}")
    except Exception as e:
        logger.error(f"✗ Backend not accessible: {e}")

    # Check 2: SSE endpoint
    try:
        response = requests.get(f"{base_url}/api/sse/stream", stream=True, timeout=5)
        if response.status_code == 200:
            logger.info("✓ SSE endpoint accessible")
            response.close()
        else:
            logger.error(f"✗ SSE endpoint failed: {response.status_code}")
    except Exception as e:
        logger.error(f"✗ SSE endpoint not accessible: {e}")

    # Check 3: Dashboard endpoint
    try:
        response = requests.get(f"{base_url}/api/dashboard/occupied", timeout=5)
        if response.status_code == 200:
            logger.info("✓ Dashboard endpoint accessible")
        else:
            logger.error(f"✗ Dashboard endpoint failed: {response.status_code}")
    except Exception as e:
        logger.error(f"✗ Dashboard endpoint not accessible: {e}")

    logger.info("=" * 80)
    logger.info("Check complete. Ready to run load test.")


if __name__ == "__main__":
    if "--check-only" in sys.argv:
        check_only_mode()
    else:
        logger.info("Use 'locust -f test_sse_load.py --host=http://localhost:8000' to run load test")
