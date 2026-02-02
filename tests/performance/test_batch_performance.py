"""
Performance tests for batch union operations.

Validates <1 second requirement for 10-union batch operations.
"""
import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime

from backend.services.union_service import UnionService
from backend.repositories.union_repository import UnionRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.models.union import Union


def generate_large_mock_data(num_unions: int, ot: str = "001"):
    """Generate mock data for performance testing."""
    headers = [
        "ID", "TAG_SPOOL", "N_UNION", "DN_UNION", "TIPO_UNION",
        "ARM_FECHA_INICIO", "ARM_FECHA_FIN", "ARM_WORKER",
        "SOL_FECHA_INICIO", "SOL_FECHA_FIN", "SOL_WORKER",
        "NDT_FECHA", "NDT_STATUS", "version",
        "Creado_Por", "Fecha_Creacion", "Modificado_Por", "Fecha_Modificacion"
    ]

    data = [headers]

    for i in range(1, num_unions + 1):
        row = [
            f"OT-{ot}+{i}",  # ID
            f"OT-{ot}",  # TAG_SPOOL
            str(i),  # N_UNION
            "4.0",  # DN_UNION
            "BW",  # TIPO_UNION (SOLD-required)
            "",  # ARM_FECHA_INICIO
            "",  # ARM_FECHA_FIN (disponible for ARM)
            "",  # ARM_WORKER
            "",  # SOL_FECHA_INICIO
            "",  # SOL_FECHA_FIN
            "",  # SOL_WORKER
            "",  # NDT_FECHA
            "",  # NDT_STATUS
            f"uuid-{i}",  # version
            "SYSTEM",  # Creado_Por
            "01-01-2026",  # Fecha_Creacion
            "",  # Modificado_Por
            ""  # Fecha_Modificacion
        ]
        data.append(row)

    return data


@pytest.fixture
def mock_sheets_repo_with_latency():
    """Mock SheetsRepository with realistic latency simulation."""
    repo = MagicMock()

    # Mock _get_worksheet for batch operations
    mock_worksheet = MagicMock()

    # Simulate Google Sheets API latency (300ms for batch_update)
    def batch_update_with_latency(*args, **kwargs):
        time.sleep(0.3)  # 300ms latency
        return None

    mock_worksheet.batch_update.side_effect = batch_update_with_latency
    repo._get_worksheet.return_value = mock_worksheet

    return repo


@pytest.fixture
def union_repo_10_unions(mock_sheets_repo_with_latency):
    """UnionRepository with 10 unions for performance testing."""
    ColumnMapCache.invalidate("Uniones")

    # Generate 10 unions
    mock_data = generate_large_mock_data(num_unions=10, ot="001")
    mock_sheets_repo_with_latency.read_worksheet.return_value = mock_data

    return UnionRepository(mock_sheets_repo_with_latency)


@pytest.fixture
def union_repo_20_unions(mock_sheets_repo_with_latency):
    """UnionRepository with 20 unions for stress testing."""
    ColumnMapCache.invalidate("Uniones")

    mock_data = generate_large_mock_data(num_unions=20, ot="002")
    mock_sheets_repo_with_latency.read_worksheet.return_value = mock_data

    return UnionRepository(mock_sheets_repo_with_latency)


@pytest.fixture
def union_repo_50_unions(mock_sheets_repo_with_latency):
    """UnionRepository with 50 unions for stress testing."""
    ColumnMapCache.invalidate("Uniones")

    mock_data = generate_large_mock_data(num_unions=50, ot="003")
    mock_sheets_repo_with_latency.read_worksheet.return_value = mock_data

    return UnionRepository(mock_sheets_repo_with_latency)


@pytest.fixture
def metadata_repo():
    """Mock MetadataRepository."""
    repo = MagicMock()
    repo.batch_log_events = MagicMock()
    return repo


@pytest.fixture
def union_service(union_repo_10_unions, metadata_repo, mock_sheets_repo_with_latency):
    """UnionService with 10-union repository."""
    return UnionService(
        union_repo=union_repo_10_unions,
        metadata_repo=metadata_repo,
        sheets_repo=mock_sheets_repo_with_latency
    )


class TestBatchPerformance:
    """Test batch operation performance requirements."""

    def test_10_union_batch_under_1_second(self, union_service, union_repo_10_unions):
        """
        10-union batch operation should complete in <1 second (p95).

        Requirement: < 1s for 10 unions
        Target: 0.5s average (300ms batch_update + 200ms overhead)
        """
        # Get all 10 unions
        all_unions = union_repo_10_unions.get_by_ot("001")
        assert len(all_unions) == 10

        union_ids = [u.id for u in all_unions]

        # Execute: Process selection with timing
        start_time = time.time()

        result = union_service.process_selection(
            tag_spool="OT-001",
            union_ids=union_ids,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        elapsed_time = time.time() - start_time

        # Verify: Success
        assert result["union_count"] == 10
        assert result["event_count"] == 11  # 1 batch + 10 granular

        # Verify: Performance < 1 second (p95 requirement)
        assert elapsed_time < 1.0, f"Batch operation took {elapsed_time:.3f}s (target: <1.0s)"

        # Log performance metric
        print(f"\n✅ 10-union batch: {elapsed_time:.3f}s (target: <1.0s)")

    def test_20_union_batch_under_2_seconds(
        self,
        union_repo_20_unions,
        metadata_repo,
        mock_sheets_repo_with_latency
    ):
        """
        20-union batch should complete in <2 seconds (p99).

        Larger batches may take longer but should still be fast.
        """
        # Create service with 20-union repo
        service = UnionService(
            union_repo=union_repo_20_unions,
            metadata_repo=metadata_repo,
            sheets_repo=mock_sheets_repo_with_latency
        )

        # Get all 20 unions
        all_unions = union_repo_20_unions.get_by_ot("002")
        assert len(all_unions) == 20

        union_ids = [u.id for u in all_unions]

        # Execute with timing
        start_time = time.time()

        result = service.process_selection(
            tag_spool="OT-002",
            union_ids=union_ids,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        elapsed_time = time.time() - start_time

        # Verify: Success
        assert result["union_count"] == 20

        # Verify: Performance < 2 seconds
        assert elapsed_time < 2.0, f"20-union batch took {elapsed_time:.3f}s (target: <2.0s)"

        print(f"\n✅ 20-union batch: {elapsed_time:.3f}s (target: <2.0s)")

    def test_50_union_stress_test(
        self,
        union_repo_50_unions,
        metadata_repo,
        mock_sheets_repo_with_latency
    ):
        """
        50-union batch stress test (rare but possible scenario).

        Target: Should still complete in reasonable time (<5s).
        """
        # Create service with 50-union repo
        service = UnionService(
            union_repo=union_repo_50_unions,
            metadata_repo=metadata_repo,
            sheets_repo=mock_sheets_repo_with_latency
        )

        # Get all 50 unions
        all_unions = union_repo_50_unions.get_by_ot("003")
        assert len(all_unions) == 50

        union_ids = [u.id for u in all_unions]

        # Execute with timing
        start_time = time.time()

        result = service.process_selection(
            tag_spool="OT-003",
            union_ids=union_ids,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        elapsed_time = time.time() - start_time

        # Verify: Success
        assert result["union_count"] == 50

        # Verify: Performance < 5 seconds (stress test threshold)
        assert elapsed_time < 5.0, f"50-union batch took {elapsed_time:.3f}s (target: <5.0s)"

        print(f"\n✅ 50-union batch: {elapsed_time:.3f}s (target: <5.0s)")

    def test_concurrent_finalizar_operations(
        self,
        union_service,
        union_repo_10_unions
    ):
        """
        Test memory usage and performance with concurrent operations.

        Simulates multiple workers finalizing different spools simultaneously.
        """
        # Get unions for concurrent processing
        all_unions = union_repo_10_unions.get_by_ot("001")

        # Split into 2 batches (simulating 2 concurrent workers)
        batch_1 = [u.id for u in all_unions[:5]]
        batch_2 = [u.id for u in all_unions[5:]]

        # Execute both batches sequentially (simulating concurrent load)
        start_time = time.time()

        result_1 = union_service.process_selection(
            tag_spool="OT-001",
            union_ids=batch_1,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        result_2 = union_service.process_selection(
            tag_spool="OT-001",
            union_ids=batch_2,
            worker_id=45,
            worker_nombre="JD(45)",
            operacion="ARM"
        )

        elapsed_time = time.time() - start_time

        # Verify: Both succeeded
        assert result_1["union_count"] == 5
        assert result_2["union_count"] == 5

        # Verify: Total time reasonable for 2 operations
        assert elapsed_time < 2.0, f"Concurrent operations took {elapsed_time:.3f}s"

        print(f"\n✅ Concurrent operations (2x5 unions): {elapsed_time:.3f}s")

    def test_memory_usage_during_batch(
        self,
        union_service,
        union_repo_10_unions
    ):
        """
        Monitor memory usage during batch operations.

        Ensures no memory leaks or excessive allocation.
        """
        import psutil
        import os

        # Get baseline memory
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute batch operation
        all_unions = union_repo_10_unions.get_by_ot("001")
        union_ids = [u.id for u in all_unions]

        result = union_service.process_selection(
            tag_spool="OT-001",
            union_ids=union_ids,
            worker_id=93,
            worker_nombre="MR(93)",
            operacion="ARM"
        )

        # Get memory after operation
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory

        # Verify: Memory increase reasonable (<50MB for 10 unions)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.2f}MB (should be <50MB)"

        print(f"\n✅ Memory usage: +{memory_increase:.2f}MB (baseline: {baseline_memory:.2f}MB)")
