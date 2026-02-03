#!/usr/bin/env python3
"""
Verify TEST-02 v4.0 fix end-to-end.

Debug session: .planning/debug/v4-endpoint-rejects-test02-as-v3.md

Verification steps:
1. Get TEST-02 spool from repository
2. Verify total_uniones=8
3. Verify is_v4_spool() returns True
4. Verify get_spool_version() returns "v4.0"
5. Simulate INICIAR endpoint logic (should accept v4.0 spool)
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.repositories.sheets_repository import SheetsRepository
from backend.utils.version_detection import is_v4_spool, get_spool_version
from backend.utils.cache import get_cache
from backend.core.column_map_cache import ColumnMapCache


def main():
    """Run end-to-end verification."""

    print("=" * 60)
    print("TEST-02 v4.0 FIX VERIFICATION")
    print("=" * 60)

    # Clear all caches for fresh test
    print("\n[1] Clearing caches...")
    cache = get_cache()
    cache.clear()
    ColumnMapCache.clear_all()
    print("  ✓ Caches cleared")

    # Step 1: Get spool
    print("\n[2] Fetching TEST-02 from repository...")
    repo = SheetsRepository()
    spool = repo.get_spool_by_tag('TEST-02')

    if not spool:
        print("  ❌ FAIL: TEST-02 not found")
        return 1

    print(f"  ✓ Spool found")
    print(f"    TAG_SPOOL: {spool.tag_spool}")
    print(f"    Total_Uniones: {spool.total_uniones}")
    print(f"    OT: {spool.ot}")

    # Step 2: Verify total_uniones
    print("\n[3] Verifying total_uniones field...")
    if spool.total_uniones is None:
        print(f"  ❌ FAIL: total_uniones is None (expected: 8)")
        return 1
    elif spool.total_uniones != 8:
        print(f"  ❌ FAIL: total_uniones is {spool.total_uniones} (expected: 8)")
        return 1
    else:
        print(f"  ✓ total_uniones = 8")

    # Step 3: Verify is_v4_spool()
    print("\n[4] Testing is_v4_spool()...")
    spool_dict = spool.model_dump()
    is_v4 = is_v4_spool(spool_dict)

    if not is_v4:
        print(f"  ❌ FAIL: is_v4_spool() returned False (expected: True)")
        print(f"    spool_dict keys: {list(spool_dict.keys())}")
        print(f"    total_uniones in dict: {spool_dict.get('total_uniones')}")
        return 1
    else:
        print(f"  ✓ is_v4_spool() = True")

    # Step 4: Verify get_spool_version()
    print("\n[5] Testing get_spool_version()...")
    version = get_spool_version(spool_dict)

    if version != "v4.0":
        print(f"  ❌ FAIL: get_spool_version() returned '{version}' (expected: 'v4.0')")
        return 1
    else:
        print(f"  ✓ get_spool_version() = 'v4.0'")

    # Step 5: Simulate INICIAR endpoint logic
    print("\n[6] Simulating v4.0 INICIAR endpoint logic...")

    # This is the exact logic from occupation_v4.py line 107
    if not is_v4_spool(spool.model_dump()):
        print(f"  ❌ FAIL: INICIAR endpoint would reject TEST-02")
        print(f"    Error: Spool is v3.0, use /api/v3/occupation/tomar instead")
        return 1
    else:
        print(f"  ✓ INICIAR endpoint would accept TEST-02")

    # SUCCESS
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nTEST-02 is now properly configured as v4.0:")
    print(f"  - Total_Uniones: 8")
    print(f"  - Version: v4.0")
    print(f"  - Can use: POST /api/v4/occupation/iniciar")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
