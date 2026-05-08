"""
Regression tests for the parsed-Worker-list cache in WorkerService (T-136 D1).

Pin-tests that ensure:
  1. Repeated calls within the TTL window do NOT re-read Sheets nor re-parse.
  2. Returned values are correct after the cache hit (same content as fresh fetch).
  3. The cache key is consistent — calling find_worker_by_id and
     get_all_active_workers in sequence shares the cache.
  4. Manually invalidating the cache forces a re-fetch on the next call.

The cache is invalidated globally (singleton SimpleCache) — these tests
clear the cache before each run so they don't leak state into the rest
of the suite.

Reference: docs/audits/T-136-perf-baseline-2026-04-29.md §"Fase 2 — Diagnóstico"
"""
from unittest.mock import MagicMock

import pytest

from backend.services.worker_service import (
    WorkerService,
    _WORKERS_CACHE_KEY,
)
from backend.models.worker import Worker
from backend.utils.cache import get_cache


def make_worker_row(worker_id: int, nombre: str, apellido: str, activo: bool = True) -> list:
    """Shape of a row from the Trabajadores sheet (4 cols)."""
    return [str(worker_id), nombre, apellido, "TRUE" if activo else "FALSE"]


def make_role_row(worker_id: int, rol: str, activo: bool = True) -> MagicMock:
    """Shape of a Role record returned by RoleRepository.get_all_roles()."""
    role = MagicMock()
    role.id = worker_id
    role.activo = activo
    role.rol = MagicMock()
    role.rol.value = rol
    return role


@pytest.fixture(autouse=True)
def _clear_cache_around_each_test():
    """Wipe the singleton cache so tests are isolated."""
    cache = get_cache()
    cache.invalidate(_WORKERS_CACHE_KEY)
    yield
    cache.invalidate(_WORKERS_CACHE_KEY)


@pytest.fixture
def fake_sheets_repo():
    """SheetsRepository mock that returns one Trabajadores header row + 2 workers."""
    repo = MagicMock()
    repo.read_worksheet.return_value = [
        ["Id", "Nombre", "Apellido", "Activo"],
        make_worker_row(93, "Mauricio", "Rodriguez", activo=True),
        make_worker_row(11, "Manuel", "Marchetti", activo=True),
    ]
    return repo


@pytest.fixture
def fake_role_service():
    """RoleService mock with role_repository.get_all_roles() returning 1 role per worker."""
    service = MagicMock()
    service.role_repository.get_all_roles.return_value = [
        make_role_row(93, "Soldador"),
        make_role_row(11, "Armador"),
    ]
    return service


def test_cache_hit_skips_sheets_read_within_ttl(fake_sheets_repo, fake_role_service):
    svc = WorkerService(sheets_repository=fake_sheets_repo, role_service=fake_role_service)

    # First call populates cache
    first = svc.get_all_active_workers()
    assert len(first) == 2
    assert fake_sheets_repo.read_worksheet.call_count == 1
    assert fake_role_service.role_repository.get_all_roles.call_count == 1

    # Second call hits cache, no further Sheets/Role reads
    second = svc.get_all_active_workers()
    assert len(second) == 2
    assert fake_sheets_repo.read_worksheet.call_count == 1, (
        "Cache hit must NOT re-read the Trabajadores sheet"
    )
    assert fake_role_service.role_repository.get_all_roles.call_count == 1, (
        "Cache hit must NOT re-fetch Roles"
    )


def test_cache_returns_equivalent_workers(fake_sheets_repo, fake_role_service):
    svc = WorkerService(sheets_repository=fake_sheets_repo, role_service=fake_role_service)
    first = svc.get_all_active_workers()
    second = svc.get_all_active_workers()
    # Same set of (id, nombre) — content equivalence
    assert {(w.id, w.nombre) for w in first} == {(w.id, w.nombre) for w in second}


def test_cache_shared_across_methods(fake_sheets_repo, fake_role_service):
    """find_worker_by_id and find_worker_by_nombre share the same cache as get_all_active_workers."""
    svc = WorkerService(sheets_repository=fake_sheets_repo, role_service=fake_role_service)

    # First public call populates cache via _get_all_workers
    found = svc.find_worker_by_id(93)
    assert found is not None
    assert found.id == 93
    assert fake_sheets_repo.read_worksheet.call_count == 1

    # Subsequent public calls go through the same cache
    svc.get_all_active_workers()
    svc.find_worker_by_nombre("manuel")
    assert fake_sheets_repo.read_worksheet.call_count == 1, (
        "All WorkerService methods must share the parsed-list cache"
    )


def test_manual_invalidation_forces_refetch(fake_sheets_repo, fake_role_service):
    svc = WorkerService(sheets_repository=fake_sheets_repo, role_service=fake_role_service)
    svc.get_all_active_workers()
    assert fake_sheets_repo.read_worksheet.call_count == 1

    # Manually invalidate (simulates external write that changed Trabajadores)
    get_cache().invalidate(_WORKERS_CACHE_KEY)

    # Next call must re-fetch
    svc.get_all_active_workers()
    assert fake_sheets_repo.read_worksheet.call_count == 2, (
        "After cache invalidation, the next call must re-read the sheet"
    )


def test_cache_returns_only_workers_filtered_by_active(fake_sheets_repo, fake_role_service):
    """get_all_active_workers filters out inactive — cache must not break that filter."""
    fake_sheets_repo.read_worksheet.return_value = [
        ["Id", "Nombre", "Apellido", "Activo"],
        make_worker_row(93, "Mauricio", "Rodriguez", activo=True),
        make_worker_row(99, "Inactive", "Worker", activo=False),
    ]
    fake_role_service.role_repository.get_all_roles.return_value = []

    svc = WorkerService(sheets_repository=fake_sheets_repo, role_service=fake_role_service)
    active = svc.get_all_active_workers()
    assert all(w.activo for w in active)
    assert len(active) == 1
    assert active[0].id == 93
