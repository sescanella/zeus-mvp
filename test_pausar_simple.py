"""
Simple test to verify PAUSAR works after TOMAR.
Manually instantiates all dependencies to avoid FastAPI Depends() issues.
"""
import asyncio
from backend.models.occupation import TomarRequest, PausarRequest
from backend.models.enums import ActionType
from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.redis_repository import RedisRepository
from backend.services.redis_lock_service import RedisLockService
from backend.services.conflict_service import ConflictService
from backend.services.redis_event_service import RedisEventService
from backend.services.occupation_service import OccupationService
from backend.services.state_service import StateService


async def test_tomar_pausar():
    """Test TOMAR -> PAUSAR flow."""

    # Manual dependency construction
    sheets_repo = SheetsRepository(compatibility_mode="v3.0")
    metadata_repo = MetadataRepository(sheets_repo=sheets_repo)
    redis_repo = RedisRepository()
    await redis_repo.connect()

    try:
        redis_client = redis_repo.get_client()
        redis_lock_service = RedisLockService(redis_client=redis_client)
        conflict_service = ConflictService(sheets_repository=sheets_repo)
        redis_event_service = RedisEventService(redis_client=redis_client)

        occupation_service = OccupationService(
            redis_lock_service=redis_lock_service,
            sheets_repository=sheets_repo,
            metadata_repository=metadata_repo,
            conflict_service=conflict_service,
            redis_event_service=redis_event_service
        )

        state_service = StateService(
            occupation_service=occupation_service,
            sheets_repository=sheets_repo,
            metadata_repository=metadata_repo,
            redis_event_service=redis_event_service
        )

        tag_spool = "TEST-02"
        worker_id = 93
        worker_nombre = "MR(93)"

        print(f"\n=== Testing TOMAR → PAUSAR flow for {tag_spool} ===\n")

        # Step 1: TOMAR
        print("Step 1: TOMAR ARM...")
        tomar_request = TomarRequest(
            tag_spool=tag_spool,
            worker_id=worker_id,
            worker_nombre=worker_nombre,
            operacion=ActionType.ARM
        )

        tomar_response = await state_service.tomar(tomar_request)
        print(f"✅ TOMAR succeeded: {tomar_response.message}")

        # Step 2: PAUSAR (immediately after TOMAR)
        print(f"\nStep 2: PAUSAR ARM (immediately after TOMAR)...")
        pausar_request = PausarRequest(
            tag_spool=tag_spool,
            worker_id=worker_id,
            worker_nombre=worker_nombre,
            operacion=ActionType.ARM
        )

        pausar_response = await state_service.pausar(pausar_request)
        print(f"✅ PAUSAR succeeded: {pausar_response.message}")

        print(f"\n🎉 SUCCESS: TOMAR → PAUSAR flow works correctly!")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await redis_repo.disconnect()


if __name__ == "__main__":
    result = asyncio.run(test_tomar_pausar())
    exit(0 if result else 1)
