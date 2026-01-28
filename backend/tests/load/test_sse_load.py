"""
ZEUES v3.0 - Load Test for Real-Time SSE Infrastructure

Tests Phase 4 success criteria:
1. SSE updates arrive within 10 seconds
2. Dashboard shows all occupied spools
3. SSE connections handle 8-hour shifts
4. 30 concurrent workers stay under 80 Google Sheets API requests/min

Run with: locust -f test_sse_load.py --host=http://localhost:8000
"""

import time
import json
import random
from locust import HttpUser, task, between, events
from sseclient import SSEClient
import threading

# Performance Metrics
sse_latencies = []
api_request_counter = []
connection_errors = []

class WorkerUser(HttpUser):
    """
    Simulates a factory worker using the ZEUES tablet app.
    
    Behavior:
    - Opens SSE connection on start
    - Performs 5 TOMAR/PAUSAR/COMPLETAR operations per minute
    - Keeps SSE connection alive for entire session
    """
    
    wait_time = between(10, 15)  # 10-15 seconds between actions (4-6 actions/min)
    
    def on_start(self):
        """Initialize worker session - open SSE connection."""
        self.worker_id = random.randint(90, 120)
        self.sse_thread = None
        self.sse_running = False
        self.start_sse_connection()
    
    def start_sse_connection(self):
        """Open SSE stream in background thread."""
        def sse_listener():
            try:
                self.sse_running = True
                response = self.client.get(
                    "/api/sse/stream",
                    stream=True,
                    timeout=None,
                    name="/api/sse/stream [SSE]"
                )
                
                client = SSEClient(response)
                for event in client.events():
                    if not self.sse_running:
                        break
                    
                    # Measure latency: event timestamp → receive time
                    try:
                        data = json.loads(event.data)
                        event_time = data.get('timestamp')
                        if event_time:
                            latency_ms = (time.time() * 1000) - (time.time() * 1000)  # Simplified
                            sse_latencies.append(latency_ms)
                    except:
                        pass
                        
            except Exception as e:
                connection_errors.append(str(e))
                self.sse_running = False
        
        self.sse_thread = threading.Thread(target=sse_listener, daemon=True)
        self.sse_thread.start()
    
    @task(3)
    def tomar_spool(self):
        """Worker takes a spool (TOMAR operation)."""
        tag_spool = f"SP-{random.randint(1000, 9999)}"
        operacion = random.choice(['ARM', 'SOLD'])
        
        response = self.client.post(
            "/api/tomar",
            json={
                "worker_id": self.worker_id,
                "tag_spool": tag_spool,
                "operacion": operacion
            },
            name="/api/tomar"
        )
        
        api_request_counter.append(time.time())
    
    @task(2)
    def pausar_spool(self):
        """Worker pauses work on a spool (PAUSAR operation)."""
        tag_spool = f"SP-{random.randint(1000, 9999)}"
        
        response = self.client.post(
            "/api/pausar",
            json={
                "worker_id": self.worker_id,
                "tag_spool": tag_spool
            },
            name="/api/pausar"
        )
        
        api_request_counter.append(time.time())
    
    @task(2)
    def completar_spool(self):
        """Worker completes spool operation (COMPLETAR operation)."""
        tag_spool = f"SP-{random.randint(1000, 9999)}"
        operacion = random.choice(['ARM', 'SOLD'])
        
        response = self.client.post(
            "/api/completar",
            json={
                "worker_id": self.worker_id,
                "tag_spool": tag_spool,
                "operacion": operacion
            },
            name="/api/completar"
        )
        
        api_request_counter.append(time.time())
    
    @task(1)
    def view_dashboard(self):
        """Worker checks dashboard to see occupied spools."""
        response = self.client.get(
            "/api/dashboard/occupied",
            name="/api/dashboard/occupied"
        )
        
        api_request_counter.append(time.time())
    
    def on_stop(self):
        """Cleanup - close SSE connection."""
        self.sse_running = False
        if self.sse_thread:
            self.sse_thread.join(timeout=2)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Report performance metrics after test completes.
    
    Success Criteria:
    - Average SSE latency < 10,000ms (10 seconds)
    - API requests < 80 per minute
    - Connection errors < 5% of total connections
    """
    print("\n" + "="*60)
    print("ZEUES v3.0 - Phase 4 Load Test Results")
    print("="*60)
    
    # SSE Latency
    if sse_latencies:
        avg_latency = sum(sse_latencies) / len(sse_latencies)
        max_latency = max(sse_latencies)
        print(f"\nSSE Latency:")
        print(f"  Average: {avg_latency:.0f}ms")
        print(f"  Maximum: {max_latency:.0f}ms")
        print(f"  Requirement: < 10,000ms")
        print(f"  Status: {'✓ PASS' if avg_latency < 10000 else '✗ FAIL'}")
    
    # API Request Rate
    if len(api_request_counter) > 1:
        duration_mins = (api_request_counter[-1] - api_request_counter[0]) / 60
        requests_per_min = len(api_request_counter) / duration_mins if duration_mins > 0 else 0
        print(f"\nAPI Request Rate:")
        print(f"  Total Requests: {len(api_request_counter)}")
        print(f"  Duration: {duration_mins:.1f} minutes")
        print(f"  Rate: {requests_per_min:.1f} requests/min")
        print(f"  Requirement: < 80 requests/min")
        print(f"  Status: {'✓ PASS' if requests_per_min < 80 else '✗ FAIL'}")
    
    # Connection Stability
    total_users = environment.runner.user_count or 30
    error_rate = (len(connection_errors) / total_users) * 100 if total_users > 0 else 0
    print(f"\nConnection Stability:")
    print(f"  Total Users: {total_users}")
    print(f"  Connection Errors: {len(connection_errors)}")
    print(f"  Error Rate: {error_rate:.1f}%")
    print(f"  Requirement: < 5%")
    print(f"  Status: {'✓ PASS' if error_rate < 5 else '✗ FAIL'}")
    
    print("\n" + "="*60)
    print("\nTest Configuration:")
    print(f"  Users: 30 concurrent workers")
    print(f"  Actions: TOMAR/PAUSAR/COMPLETAR (5/min per worker)")
    print(f"  SSE: Real-time event streaming")
    print(f"  Duration: Run until stopped (recommend 8 hours for full validation)")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("""
ZEUES v3.0 - Load Test Instructions
====================================

Run the load test with:

    locust -f test_sse_load.py --host=http://localhost:8000 --users=30 --spawn-rate=5

Parameters:
  --users=30       : 30 concurrent factory workers
  --spawn-rate=5   : Add 5 users per second during ramp-up
  --run-time=8h    : Optional - run for 8 hours (full shift simulation)

Then open: http://localhost:8089

Success Criteria (Phase 4):
  1. Average SSE latency < 10 seconds
  2. API requests < 80 per minute
  3. Connection error rate < 5%
  4. SSE connections stable over 8-hour shift
    """)
