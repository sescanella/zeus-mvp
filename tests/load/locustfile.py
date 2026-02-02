"""
Locust load test for ZEUES v4.0 union-level workflows.

Simulates 30-50 concurrent workers performing INICIAR/FINALIZAR operations
with realistic timing, union selection patterns, and error handling.

PERF-01: p95 < 1s for 10-union batches
PERF-02: p99 < 2s for all operations
PERF-03: Max 2 API calls per FINALIZAR
PERF-05: < 30 writes/min (50% of Google Sheets quota)

Usage:
    locust -f locustfile.py --headless -u 30 -r 5 -t 5m --host http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import time
from datetime import datetime


class WorkerUser(HttpUser):
    """
    Simulate worker performing v4.0 INICIAR/FINALIZAR workflows.

    Workflow pattern:
    1. INICIAR - Occupy spool without selecting unions
    2. Wait (simulate work time)
    3. FINALIZAR - Select unions and complete/pause

    Wait time: 5-15 seconds between operations (realistic work intervals)
    """

    wait_time = between(5, 15)  # Realistic intervals between operations

    def on_start(self):
        """Initialize worker-specific data when starting."""
        # Assign unique worker ID (simulate 30-50 workers)
        self.worker_id = random.randint(1, 100)
        self.worker_nombre = f"WORKER{self.worker_id}"

        # Track currently occupied spools
        self.occupied_spools = []

    @task(3)
    def finalizar_arm_10_unions(self):
        """
        Most common scenario: Complete 10 ARM unions.

        Weight: 3 (most frequent operation)
        Expected: p95 < 1s per PERF-01
        """
        # Generate realistic OT and union IDs
        ot_number = random.randint(1, 100)
        tag_spool = f"OT-{ot_number:03d}"

        # Select 10 unions (typical batch size)
        union_ids = [f"{tag_spool}+{i}" for i in range(1, 11)]

        with self.client.post(
            "/api/v4/occupation/finalizar",
            json={
                "tag_spool": tag_spool,
                "union_ids": union_ids,
                "worker_id": self.worker_id,
                "worker_nombre": self.worker_nombre,
                "operacion": "ARM",
                "fecha_operacion": datetime.now().strftime("%Y-%m-%d")
            },
            catch_response=True,
            name="FINALIZAR ARM (10 unions)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 403:
                # Ownership error (expected when simulating multiple workers)
                response.failure("Ownership validation failed (expected in load test)")
            elif response.status_code == 404:
                # Spool not found (test data limitation)
                response.failure("Spool not found (test data)")
            elif response.status_code == 409:
                # Conflict (race condition)
                response.failure("Conflict: selected unions unavailable")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(2)
    def finalizar_sold_5_unions(self):
        """
        Partial completion: Complete 5 SOLD unions.

        Weight: 2 (common partial work scenario)
        Triggers PAUSAR (not COMPLETAR)
        """
        ot_number = random.randint(1, 100)
        tag_spool = f"OT-{ot_number:03d}"

        # Select 5 unions (partial completion)
        union_ids = [f"{tag_spool}+{i}" for i in range(1, 6)]

        with self.client.post(
            "/api/v4/occupation/finalizar",
            json={
                "tag_spool": tag_spool,
                "union_ids": union_ids,
                "worker_id": self.worker_id,
                "worker_nombre": self.worker_nombre,
                "operacion": "SOLD",
                "fecha_operacion": datetime.now().strftime("%Y-%m-%d")
            },
            catch_response=True,
            name="FINALIZAR SOLD (5 unions - partial)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [403, 404, 409]:
                response.failure(f"Expected test error: {response.status_code}")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def finalizar_arm_50_unions(self):
        """
        Stress test: Complete 50 ARM unions in single batch.

        Weight: 1 (rare but important edge case)
        Tests performance under maximum load
        Expected: p99 < 2s per PERF-02
        """
        ot_number = random.randint(1, 100)
        tag_spool = f"OT-{ot_number:03d}"

        # Select 50 unions (stress test batch size)
        union_ids = [f"{tag_spool}+{i}" for i in range(1, 51)]

        with self.client.post(
            "/api/v4/occupation/finalizar",
            json={
                "tag_spool": tag_spool,
                "union_ids": union_ids,
                "worker_id": self.worker_id,
                "worker_nombre": self.worker_nombre,
                "operacion": "ARM",
                "fecha_operacion": datetime.now().strftime("%Y-%m-%d")
            },
            catch_response=True,
            name="FINALIZAR ARM (50 unions - stress)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [403, 404, 409]:
                response.failure(f"Expected test error: {response.status_code}")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def iniciar_new_spool(self):
        """
        Start work on new spool (INICIAR).

        Weight: 1 (less frequent than FINALIZAR)
        Occupies spool without union selection
        """
        ot_number = random.randint(1, 100)
        tag_spool = f"OT-{ot_number:03d}"
        operacion = random.choice(["ARM", "SOLD"])

        with self.client.post(
            "/api/v4/occupation/iniciar",
            json={
                "tag_spool": tag_spool,
                "worker_id": self.worker_id,
                "worker_nombre": self.worker_nombre,
                "operacion": operacion
            },
            catch_response=True,
            name="INICIAR (occupy spool)"
        ) as response:
            if response.status_code == 200:
                self.occupied_spools.append(tag_spool)
                response.success()
            elif response.status_code == 403:
                # ARM prerequisite or ownership error
                response.failure("ARM prerequisite or ownership error")
            elif response.status_code == 404:
                # Spool not found
                response.failure("Spool not found (test data)")
            elif response.status_code == 409:
                # Already occupied
                response.failure("Spool already occupied (expected in load test)")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def query_disponibles_arm(self):
        """
        Query available ARM unions for spool.

        Weight: 1 (read-only operation)
        Tests query performance
        """
        ot_number = random.randint(1, 100)
        tag_spool = f"OT-{ot_number:03d}"

        with self.client.get(
            f"/api/v4/uniones/{tag_spool}/disponibles?operacion=ARM",
            catch_response=True,
            name="GET disponibles ARM"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.failure("Spool not found (test data)")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def query_metricas(self):
        """
        Query pulgadas-diámetro metrics for spool.

        Weight: 1 (read-only operation)
        Tests metrics calculation performance
        """
        ot_number = random.randint(1, 100)
        tag_spool = f"OT-{ot_number:03d}"

        with self.client.get(
            f"/api/v4/uniones/{tag_spool}/metricas",
            catch_response=True,
            name="GET metricas"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.failure("Spool not found (test data)")
            else:
                response.failure(f"Unexpected status {response.status_code}")


# Event listeners for global metrics (imported by test_comprehensive_performance.py)
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize test environment."""
    print("\n" + "="*80)
    print("ZEUES v4.0 LOAD TEST - Phase 13 Performance Validation")
    print("="*80)
    print(f"Target host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if environment.runner else 'N/A'}")
    print("Validating: PERF-01 (p95<1s), PERF-02 (p99<2s), PERF-03 (2 API calls), PERF-05 (<30 RPM)")
    print("="*80 + "\n")
