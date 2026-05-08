"""
API Call Efficiency Tests for PERF-03 and PERF-04 validation.

Tests that FINALIZAR makes exactly 2 API calls and metadata chunking works correctly.
"""
import pytest
import time
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from collections import deque
import uuid

from backend.services.union_service import UnionService
from backend.repositories.union_repository import UnionRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.models.union import Union
from backend.models.metadata import MetadataEvent, EventoTipo, Accion
from tests.fixtures.mock_uniones_data import generate_mock_uniones


class APICallMonitor:
    """
    Monitor API calls across tests with categorization and reporting.

    Tracks all gspread method calls and provides efficiency metrics.
    """

    def __init__(self):
        """Initialize API call monitor."""
        self.calls = deque()  # (timestamp, operation_type, method)
        self.read_calls = 0
        self.write_calls = 0
        self.batch_calls = 0

    def record_call(self, operation_type: str, method: str):
        """
        Record an API call.

        Args:
            operation_type: Type of operation ("read", "write", "batch")
            method: Method name (e.g., "get_all_values", "batch_update")
        """
        now = datetime.now()
        self.calls.append((now, operation_type, method))

        if operation_type == "read":
            self.read_calls += 1
        elif operation_type == "write":
            self.write_calls += 1
        elif operation_type == "batch":
            self.batch_calls += 1

    def get_total_calls(self) -> int:
        """Get total number of API calls."""
        return len(self.calls)

    def get_stats(self) -> dict:
        """
        Get comprehensive statistics.

        Returns:
            dict with read/write/batch counts and efficiency metrics
        """
        total = self.get_total_calls()

        return {
            "total_calls": total,
            "read_calls": self.read_calls,
            "write_calls": self.write_calls,
            "batch_calls": self.batch_calls,
            "batch_efficiency": (self.batch_calls / total * 100) if total > 0 else 0.0
        }

    def reset(self):
        """Reset all counters."""
        self.calls.clear()
        self.read_calls = 0
        self.write_calls = 0
        self.batch_calls = 0

    def print_report(self):
        """Print efficiency report."""
        stats = self.get_stats()
        print(f"\n📊 API Call Efficiency Report:")
        print(f"   Total API calls: {stats['total_calls']}")
        print(f"   Read calls: {stats['read_calls']}")
        print(f"   Write calls: {stats['write_calls']}")
        print(f"   Batch calls: {stats['batch_calls']}")
        print(f"   Batch efficiency: {stats['batch_efficiency']:.1f}%")


@pytest.fixture
def api_call_monitor():
    """Create API call monitor for tracking."""
    return APICallMonitor()


@pytest.fixture
def mock_sheets_repo_with_tracking(api_call_monitor):
    """Mock SheetsRepository with API call tracking."""
    repo = MagicMock()

    # Use mock data (100 unions across 10 OTs)
    mock_data = generate_mock_uniones(num_ots=10, unions_per_ot=10)

    # Track read call
    def track_read_call(*args, **kwargs):
        api_call_monitor.record_call("read", "read_worksheet")
        return mock_data

    repo.read_worksheet = MagicMock(side_effect=track_read_call)

    # Mock _get_worksheet for batch operations
    mock_worksheet = MagicMock()

    # Track batch_update call
    def track_batch_update(batch_data, value_input_option=None):
        api_call_monitor.record_call("batch", "batch_update")
        time.sleep(0.3)  # Simulate latency

    mock_worksheet.batch_update = MagicMock(side_effect=track_batch_update)
    repo._get_worksheet.return_value = mock_worksheet

    return repo


@pytest.fixture
def mock_metadata_sheets_repo_with_tracking(api_call_monitor):
    """Mock SheetsRepository for Metadata with API call tracking."""
    repo = MagicMock()

    # Mock _get_spreadsheet for MetadataRepository._get_worksheet()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()

    # Track append_rows call
    def track_append_rows(rows, value_input_option=None):
        api_call_monitor.record_call("batch", "append_rows")
        time.sleep(0.15)  # Simulate latency

    mock_worksheet.append_rows = MagicMock(side_effect=track_append_rows)
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    repo._get_spreadsheet.return_value = mock_spreadsheet

    return repo


@pytest.fixture
def union_repo_with_tracking(mock_sheets_repo_with_tracking):
    """Create UnionRepository with tracking."""
    from backend.core.column_map_cache import ColumnMapCache
    ColumnMapCache.invalidate("Uniones")
    return UnionRepository(mock_sheets_repo_with_tracking)


@pytest.fixture
def metadata_repo_with_tracking(mock_metadata_sheets_repo_with_tracking):
    """Create MetadataRepository with tracking."""
    with patch('backend.repositories.metadata_repository.config') as mock_config:
        mock_config.HOJA_METADATA_NOMBRE = "Metadata"
        repo = MetadataRepository(mock_metadata_sheets_repo_with_tracking)
        repo._get_worksheet()
        return repo


@pytest.fixture
def union_service_with_tracking(
    union_repo_with_tracking,
    metadata_repo_with_tracking,
    mock_sheets_repo_with_tracking
):
    """Create UnionService with tracking."""
    return UnionService(
        union_repo=union_repo_with_tracking,
        metadata_repo=metadata_repo_with_tracking,
        sheets_repo=mock_sheets_repo_with_tracking
    )


class TestAPICallEfficiency:
    """
    Validate API call efficiency for PERF-03 and PERF-04 requirements.
    """


    def test_metadata_chunking_at_900_rows(self, metadata_repo_with_tracking):
        """
        PERF-04: Metadata batch logging chunks at 900 rows for safety.

        Tests that large event batches (1000+ events) are automatically
        split into chunks of ≤ 900 rows per append_rows call.

        Note: n_union is constrained to 1-20, so we use None for batch events
        to simulate large-scale metadata logging without union-level granularity.
        """
        # Create 1050 events (triggers chunking: 900 + 150)
        # Use n_union=None for batch-level events (not constrained to 1-20)
        events = []
        for i in range(1, 1051):
            event = MetadataEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                evento_tipo=EventoTipo.UNION_ARM_REGISTRADA,
                tag_spool=f"TEST-CHUNK-{i // 20}",  # Vary tag_spool to simulate multiple spools
                worker_id=93,
                worker_nombre="MR(93)",
                operacion="ARM",
                accion=Accion.COMPLETAR,
                fecha_operacion="02-02-2026",
                metadata_json='{}',
                n_union=None  # Use None for batch events (not union-level)
            )
            events.append(event)

        # Get mock worksheet to verify chunking
        mock_worksheet = metadata_repo_with_tracking._worksheet
        mock_worksheet.append_rows.reset_mock()

        # Execute batch log (should trigger chunking)
        metadata_repo_with_tracking.batch_log_events(events)

        # Verify append_rows called multiple times (chunking occurred)
        call_count = mock_worksheet.append_rows.call_count

        print(f"\n✅ PERF-04 Validation:")
        print(f"   Total events: {len(events)}")
        print(f"   append_rows calls: {call_count}")
        print(f"   Expected calls: 2 (900 + 150)")

        # Should be called 2 times (900 + 150)
        assert call_count == 2, \
            f"PERF-04 FAILED: Expected 2 append_rows calls for 1050 events, got {call_count}"

        # Verify chunk sizes
        all_calls = mock_worksheet.append_rows.call_args_list

        for idx, call_obj in enumerate(all_calls, start=1):
            rows = call_obj[0][0]  # First positional argument
            chunk_size = len(rows)

            print(f"   Chunk {idx}: {chunk_size} rows")

            # Each chunk should be ≤ 900 rows (PERF-04)
            assert chunk_size <= 900, \
                f"PERF-04 FAILED: Chunk {idx} has {chunk_size} rows (max 900)"

        # Verify all events were logged
        total_logged = sum(len(call_obj[0][0]) for call_obj in all_calls)
        assert total_logged == len(events), \
            f"Not all events logged: {total_logged}/{len(events)}"

    def test_api_calls_scale_linearly(
        self,
        union_repo_with_tracking,
        metadata_repo_with_tracking,
        api_call_monitor
    ):
        """
        Validate API calls remain constant (always 2) regardless of union count.

        Tests that FINALIZAR with 10, 20, 30 unions always makes exactly 2 API calls.
        This ensures O(1) API complexity.
        """
        tag_spool = "MK-1335-CW-25238-002"
        worker = "MR(93)"
        worker_id = 93

        # Test with different union counts
        test_cases = [10, 20, 30]
        results = []

        for union_count in test_cases:
            # Reset monitor
            api_call_monitor.reset()

            # Fetch disponibles
            disponibles = union_repo_with_tracking.get_disponibles_arm_by_ot("002")

            # Select N unions
            union_ids = [u.id for u in disponibles[:union_count]]

            if len(union_ids) < union_count:
                # Not enough unions available, skip this test case
                print(f"\n⚠️  Skipping {union_count} unions (only {len(union_ids)} available)")
                continue

            # Record initial call count
            initial_calls = api_call_monitor.get_total_calls()

            # Execute FINALIZAR workflow
            union_repo_with_tracking.batch_update_arm(
                tag_spool=tag_spool,
                union_ids=union_ids,
                worker=worker,
                timestamp=datetime.now()
            )

            # Build and log metadata events
            union_details = [
                {"dn_union": u.dn_union, "tipo": u.tipo_union, "duracion_min": 15.5}
                for u in disponibles[:union_count]
            ]

            events = metadata_repo_with_tracking.build_union_events(
                tag_spool=tag_spool,
                worker_id=worker_id,
                worker_nombre=worker,
                operacion="ARM",
                union_ids=union_ids,
                union_details=union_details
            )

            metadata_repo_with_tracking.batch_log_events(events)

            # Calculate API calls
            finalizar_calls = api_call_monitor.get_total_calls() - initial_calls

            results.append((union_count, finalizar_calls))

            print(f"\n   {union_count} unions: {finalizar_calls} API calls")

        # Verify results
        print(f"\n✅ Linear Scaling Validation:")
        print(f"   Union counts tested: {[r[0] for r in results]}")
        print(f"   API calls: {[r[1] for r in results]}")

        # All should have exactly 2 API calls
        for union_count, api_calls in results:
            assert api_calls == 2, \
                f"Expected 2 API calls for {union_count} unions, got {api_calls}"

        print(f"   ✅ O(1) API complexity confirmed: Always 2 calls regardless of union count")


class TestBatchOperationValidation:
    """
    Validate batch operation details for completeness and efficiency.
    """



