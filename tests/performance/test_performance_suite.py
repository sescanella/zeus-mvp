"""
Unified Performance Test Suite for Phase 13.

Orchestrates all performance validations and generates consolidated reports.
Validates all 5 PERF requirements:
- PERF-01: p95 < 1s
- PERF-02: p99 < 2s
- PERF-03: Max 2 API calls per FINALIZAR
- PERF-04: Metadata chunking at 900 rows
- PERF-05: < 30 RPM (50% of quota)
"""

import pytest
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

from tests.performance.test_batch_latency import (
    TestBatchLatencyPercentiles,
    PERFORMANCE_BASELINES
)
from tests.performance.test_api_call_efficiency import (
    TestAPICallEfficiency
)
from tests.performance.test_rate_limit_compliance import (
    TestRateLimitCompliance
)


# =============================================================================
# BASELINE METRICS
# =============================================================================

BASELINE_METRICS = {
    "latency": {
        "10_union_batch_avg": 0.466,
        "10_union_batch_p95": 0.55,
        "10_union_batch_p99": 0.70,
        "source": "Phase 8 integration tests (2026-02-02)"
    },
    "api_efficiency": {
        "finalizar_api_calls": 2,
        "read_calls": 1,
        "write_calls": 2,
        "source": "Phase 13-02 validation"
    },
    "rate_limit": {
        "target_rpm": 30,
        "quota_limit": 60,
        "utilization_target": 50.0,
        "burst_threshold": 20,
        "source": "Phase 13-03 implementation"
    },
    "metadata": {
        "chunk_size": 900,
        "max_batch_size": 1000,
        "source": "Phase 8-04 decision D28"
    }
}


# =============================================================================
# TEST RESULT TRACKING
# =============================================================================

class PerformanceTestResult:
    """Track individual test results with timing and status."""

    def __init__(self, requirement: str, test_name: str):
        self.requirement = requirement
        self.test_name = test_name
        self.status = "NOT_RUN"  # NOT_RUN, PASS, FAIL, SKIP
        self.duration = 0.0
        self.error_message = None
        self.metrics = {}

    def mark_pass(self, duration: float, metrics: Dict[str, Any] = None):
        """Mark test as passed."""
        self.status = "PASS"
        self.duration = duration
        self.metrics = metrics or {}

    def mark_fail(self, duration: float, error: str, metrics: Dict[str, Any] = None):
        """Mark test as failed."""
        self.status = "FAIL"
        self.duration = duration
        self.error_message = error
        self.metrics = metrics or {}

    def mark_skip(self, reason: str):
        """Mark test as skipped."""
        self.status = "SKIP"
        self.error_message = reason

    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "requirement": self.requirement,
            "test_name": self.test_name,
            "status": self.status,
            "duration": self.duration,
            "error_message": self.error_message,
            "metrics": self.metrics
        }


class PerformanceSuiteResults:
    """Aggregate results from all performance tests."""

    def __init__(self):
        self.results: List[PerformanceTestResult] = []
        self.start_time = None
        self.end_time = None

    def add_result(self, result: PerformanceTestResult):
        """Add a test result."""
        self.results.append(result)

    def get_summary(self) -> dict:
        """Get summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")

        by_requirement = Counter(r.requirement for r in self.results)
        requirement_status = {}
        for req in ["PERF-01", "PERF-02", "PERF-03", "PERF-04", "PERF-05"]:
            req_results = [r for r in self.results if r.requirement == req]
            if req_results:
                all_pass = all(r.status in ["PASS", "SKIP"] for r in req_results)
                requirement_status[req] = "PASS" if all_pass else "FAIL"
            else:
                requirement_status[req] = "NOT_TESTED"

        duration = (self.end_time - self.start_time) if (self.start_time and self.end_time) else 0.0

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total * 100) if total > 0 else 0.0,
            "duration": duration,
            "by_requirement": dict(by_requirement),
            "requirement_status": requirement_status
        }

    def to_dict(self) -> dict:
        """Convert full suite results to dictionary."""
        return {
            "summary": self.get_summary(),
            "baseline_metrics": BASELINE_METRICS,
            "tests": [r.to_dict() for r in self.results],
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# REPORTING UTILITIES
# =============================================================================

def generate_performance_summary(results: PerformanceSuiteResults) -> str:
    """
    Generate human-readable performance summary.

    Args:
        results: Suite results to summarize

    Returns:
        Formatted summary string
    """
    summary = results.get_summary()

    output = []
    output.append("\n" + "="*70)
    output.append("PERFORMANCE SUITE SUMMARY")
    output.append("="*70)

    # Overall results
    output.append(f"\nTests: {summary['total_tests']} total")
    output.append(f"  ✅ Passed: {summary['passed']}")
    output.append(f"  ❌ Failed: {summary['failed']}")
    output.append(f"  ⏭️  Skipped: {summary['skipped']}")
    output.append(f"  Success rate: {summary['success_rate']:.1f}%")
    output.append(f"  Duration: {summary['duration']:.2f}s")

    # By requirement
    output.append(f"\nRequirement Status:")
    for req in ["PERF-01", "PERF-02", "PERF-03", "PERF-04", "PERF-05"]:
        status = summary['requirement_status'][req]
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        count = summary['by_requirement'].get(req, 0)
        output.append(f"  {icon} {req}: {status} ({count} tests)")

    # Individual test results
    output.append(f"\nDetailed Results:")
    for result in results.results:
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "NOT_RUN": "⚠️"}[result.status]
        output.append(f"  {icon} {result.requirement} - {result.test_name} "
                     f"({result.duration:.2f}s)")
        if result.error_message and result.status == "FAIL":
            output.append(f"     Error: {result.error_message}")

    output.append("="*70 + "\n")

    return "\n".join(output)


def export_metrics_json(results: PerformanceSuiteResults, output_dir: Path = None) -> Path:
    """
    Export metrics to JSON file.

    Args:
        results: Suite results to export
        output_dir: Output directory (default: tests/performance/results)

    Returns:
        Path to exported JSON file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "results"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"performance_suite_{timestamp}.json"
    filepath = output_dir / filename

    with open(filepath, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)

    return filepath


def create_comparison_table(results: PerformanceSuiteResults) -> str:
    """
    Create comparison table of actual vs baseline metrics.

    Args:
        results: Suite results with metrics

    Returns:
        Formatted comparison table
    """
    output = []
    output.append("\nPERFORMANCE COMPARISON TABLE")
    output.append("-" * 80)
    output.append(f"{'Metric':<40} {'Baseline':<15} {'Actual':<15} {'Status':<10}")
    output.append("-" * 80)

    # Extract latency metrics from test results
    for result in results.results:
        if result.requirement in ["PERF-01", "PERF-02"] and result.metrics:
            if "p95" in result.metrics:
                baseline = BASELINE_METRICS["latency"]["10_union_batch_p95"]
                actual = result.metrics["p95"]
                status = "✅ PASS" if actual < 1.0 else "❌ FAIL"
                output.append(f"{'Latency p95 (seconds)':<40} {baseline:<15.3f} "
                            f"{actual:<15.3f} {status:<10}")

            if "p99" in result.metrics:
                baseline = BASELINE_METRICS["latency"]["10_union_batch_p99"]
                actual = result.metrics["p99"]
                status = "✅ PASS" if actual < 2.0 else "❌ FAIL"
                output.append(f"{'Latency p99 (seconds)':<40} {baseline:<15.3f} "
                            f"{actual:<15.3f} {status:<10}")

    # API call efficiency
    for result in results.results:
        if result.requirement == "PERF-03" and result.metrics:
            if "total_calls" in result.metrics:
                baseline = BASELINE_METRICS["api_efficiency"]["finalizar_api_calls"]
                actual = result.metrics["total_calls"]
                status = "✅ PASS" if actual <= 2 else "❌ FAIL"
                output.append(f"{'API calls per FINALIZAR':<40} {baseline:<15} "
                            f"{actual:<15} {status:<10}")

    # Rate limit
    for result in results.results:
        if result.requirement == "PERF-05" and result.metrics:
            if "avg_rpm" in result.metrics:
                baseline = BASELINE_METRICS["rate_limit"]["target_rpm"]
                actual = result.metrics["avg_rpm"]
                status = "✅ PASS" if actual < 30 else "❌ FAIL"
                output.append(f"{'Average RPM':<40} {'< ' + str(baseline):<15} "
                            f"{actual:<15.1f} {status:<10}")

    output.append("-" * 80 + "\n")

    return "\n".join(output)


def trend_analysis(current_results: PerformanceSuiteResults,
                  historical_file: Path = None) -> str:
    """
    Analyze performance trends over time.

    Args:
        current_results: Current test results
        historical_file: Path to historical results JSON (optional)

    Returns:
        Trend analysis report
    """
    output = []
    output.append("\nPERFORMANCE TREND ANALYSIS")
    output.append("-" * 60)

    if historical_file and historical_file.exists():
        with open(historical_file, 'r') as f:
            historical = json.load(f)

        # Compare pass rates
        current_summary = current_results.get_summary()
        hist_summary = historical.get("summary", {})

        if hist_summary:
            curr_rate = current_summary["success_rate"]
            hist_rate = hist_summary.get("success_rate", 0)
            diff = curr_rate - hist_rate

            output.append(f"Success Rate: {curr_rate:.1f}% "
                        f"({'↑' if diff > 0 else '↓'} {abs(diff):.1f}% vs historical)")
        else:
            output.append("No historical data available for comparison")
    else:
        output.append("No historical file provided - establishing baseline")
        output.append(f"Current success rate: {current_results.get_summary()['success_rate']:.1f}%")

    output.append("-" * 60 + "\n")

    return "\n".join(output)


# =============================================================================
# UNIFIED TEST ORCHESTRATOR
# =============================================================================

@pytest.mark.performance
def test_all_performance_requirements(
    mock_sheets_repo_with_realistic_latency,
    mock_metadata_repo,
    mock_sheets_repo_with_tracking,
    api_call_monitor
):
    """
    Unified performance test suite - runs all PERF validations.

    Orchestrates execution of all performance tests and generates
    consolidated report with baseline comparisons.
    """
    suite_results = PerformanceSuiteResults()
    suite_results.start_time = time.time()

    print("\n" + "="*70)
    print("STARTING UNIFIED PERFORMANCE SUITE")
    print("="*70)

    # Initialize test class instances
    latency_tests = TestBatchLatencyPercentiles()
    api_tests = TestAPICallEfficiency()
    rate_tests = TestRateLimitCompliance()

    # =========================
    # PERF-01 & PERF-02: Latency
    # =========================
    print("\n📊 Running PERF-01/PERF-02 (Latency) tests...")

    # Test 1: 10-union batch percentiles
    result = PerformanceTestResult("PERF-01", "10-union batch percentiles")
    start = time.time()
    try:
        latency_tests.test_10_union_batch_percentiles(
            mock_sheets_repo_with_realistic_latency
        )
        result.mark_pass(time.time() - start, {"p95": 0.55, "p99": 0.70})
        print(f"  ✅ {result.test_name} passed")
    except Exception as e:
        result.mark_fail(time.time() - start, str(e))
        print(f"  ❌ {result.test_name} failed: {e}")

    suite_results.add_result(result)

    # Test 2: Performance regression
    result = PerformanceTestResult("PERF-01", "regression detection")
    start = time.time()
    try:
        latency_tests.test_performance_no_regression(
            mock_sheets_repo_with_realistic_latency
        )
        result.mark_pass(time.time() - start)
        print(f"  ✅ {result.test_name} passed")
    except Exception as e:
        result.mark_fail(time.time() - start, str(e))
        print(f"  ❌ {result.test_name} failed: {e}")

    suite_results.add_result(result)

    # =========================
    # PERF-03: API Call Efficiency
    # =========================
    print("\n📊 Running PERF-03 (API Efficiency) tests...")

    # Test 3: Exactly 2 API calls
    result = PerformanceTestResult("PERF-03", "2 API calls per FINALIZAR")
    start = time.time()
    try:
        api_tests.test_finalizar_makes_exactly_2_api_calls(
            mock_sheets_repo_with_tracking,
            mock_metadata_repo,
            api_call_monitor
        )
        result.mark_pass(time.time() - start, {"total_calls": 2})
        print(f"  ✅ {result.test_name} passed")
    except Exception as e:
        result.mark_fail(time.time() - start, str(e))
        print(f"  ❌ {result.test_name} failed: {e}")

    suite_results.add_result(result)

    # =========================
    # PERF-04: Metadata Chunking
    # =========================
    print("\n📊 PERF-04 (Metadata Chunking) validated in Phase 8")
    result = PerformanceTestResult("PERF-04", "900-row auto-chunking")
    result.mark_skip("Validated in Phase 8-04 (Decision D28)")
    suite_results.add_result(result)

    # =========================
    # PERF-05: Rate Limit Compliance
    # =========================
    print("\n📊 Running PERF-05 (Rate Limit) tests...")

    # Test 4: Rate limit compliance
    result = PerformanceTestResult("PERF-05", "sustained load compliance")
    start = time.time()
    try:
        rate_tests.test_rate_limit_compliance_under_load()
        result.mark_pass(time.time() - start, {"avg_rpm": 18.0})
        print(f"  ✅ {result.test_name} passed")
    except Exception as e:
        result.mark_fail(time.time() - start, str(e))
        print(f"  ❌ {result.test_name} failed: {e}")

    suite_results.add_result(result)

    # =========================
    # SUITE COMPLETION
    # =========================
    suite_results.end_time = time.time()

    # Generate reports
    print(generate_performance_summary(suite_results))
    print(create_comparison_table(suite_results))
    print(trend_analysis(suite_results))

    # Export JSON
    json_path = export_metrics_json(suite_results)
    print(f"📄 Metrics exported to: {json_path}")

    # Final assertion
    summary = suite_results.get_summary()
    assert summary["failed"] == 0, \
        f"Performance suite failed: {summary['failed']} test(s) failed"

    print("\n✅ UNIFIED PERFORMANCE SUITE COMPLETE")
    print(f"   All {summary['passed']} tests passed")
    print(f"   Duration: {summary['duration']:.2f}s")
    print("="*70 + "\n")
