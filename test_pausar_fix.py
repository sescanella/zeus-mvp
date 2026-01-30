"""
Test script to verify PAUSAR fix for cache invalidation issue.

Reproduces the bug:
1. TOMAR ARM on a spool
2. Immediately PAUSAR ARM on same spool
3. Should succeed (before fix: fails with "state 'pendiente'" error)
"""
import asyncio
import sys
from backend.models.occupation import TomarRequest, PausarRequest
from backend.models.enums import ActionType
from backend.core.dependency import get_state_service

async def test_tomar_pausar_flow():
    """Test TOMAR → PAUSAR flow to verify cache invalidation."""
    
    tag_spool = "TEST-CACHE-01"
    worker_id = 93
    worker_nombre = "MR(93)"
    
    # Get StateService instance
    service = get_state_service()
    
    try:
        print(f"\n=== Testing TOMAR → PAUSAR flow for {tag_spool} ===\n")
        
        # Step 1: TOMAR
        print(f"Step 1: TOMAR ARM...")
        tomar_request = TomarRequest(
            tag_spool=tag_spool,
            worker_id=worker_id,
            worker_nombre=worker_nombre,
            operacion=ActionType.ARM
        )
        
        tomar_response = await service.tomar(tomar_request)
        print(f"✅ TOMAR succeeded: {tomar_response.message}")
        
        # Step 2: PAUSAR (immediately after TOMAR)
        print(f"\nStep 2: PAUSAR ARM (immediately after TOMAR)...")
        pausar_request = PausarRequest(
            tag_spool=tag_spool,
            worker_id=worker_id,
            worker_nombre=worker_nombre,
            operacion=ActionType.ARM
        )
        
        pausar_response = await service.pausar(pausar_request)
        print(f"✅ PAUSAR succeeded: {pausar_response.message}")
        
        print(f"\n🎉 SUCCESS: TOMAR → PAUSAR flow works correctly!")
        print(f"Fix verified: Cache is properly invalidated after Armador update.")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        print(f"\nThis indicates the cache invalidation fix did NOT work.")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_tomar_pausar_flow())
    sys.exit(0 if result else 1)
