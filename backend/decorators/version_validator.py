"""
Version validation decorator for v4.0 endpoints.

Validates that spool is v4.0 (has unions) before allowing request to proceed.
Returns 422 Unprocessable Entity for v3.0 spools on v4.0-only endpoints.
"""
from functools import wraps
from typing import Callable, Any
import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.services.version_detection_service import VersionDetectionService
from backend.models.version import VersionMismatchError


logger = logging.getLogger(__name__)


def require_v4_spool(version_service: VersionDetectionService):
    """
    Decorator to validate spool version for v4.0 endpoints.

    Extracts tag_spool from request (path or body), detects version,
    and rejects v3.0 spools with 422 error.

    Args:
        version_service: VersionDetectionService instance for detection

    Returns:
        Decorator function

    Raises:
        HTTPException: 422 Unprocessable Entity if spool is not v4.0

    Example usage:
        ```python
        @router.post("/api/iniciar")
        @require_v4_spool(version_service)
        async def iniciar_union(request: IniciarRequest):
            # Only v4.0 spools reach here
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract tag_spool from kwargs (path parameter or body)
            tag_spool = kwargs.get('tag_spool') or kwargs.get('tag')

            # If not in path params, try to extract from request body
            if not tag_spool:
                # Look for Request object in args
                for arg in args:
                    if isinstance(arg, Request):
                        # Try to get from JSON body
                        try:
                            body = await arg.json()
                            tag_spool = body.get('tag_spool')
                        except Exception:
                            pass
                        break

            if not tag_spool:
                # Can't validate without tag_spool - let endpoint handle it
                logger.warning("require_v4_spool: tag_spool not found in request")
                return await func(*args, **kwargs)

            # Detect version
            logger.info(f"Validating version for spool: {tag_spool}")
            version_info = await version_service.detect_version(tag_spool)

            # Validate v4.0
            if version_info['version'] != 'v4.0':
                error_detail = VersionMismatchError(
                    message=f"This endpoint requires v4.0 spools with unions. Spool {tag_spool} is {version_info['version']}",
                    expected_version="v4.0",
                    actual_version=version_info['version'],
                    tag_spool=tag_spool
                )

                logger.warning(
                    f"Version mismatch: endpoint requires v4.0, spool {tag_spool} is {version_info['version']}"
                )

                raise HTTPException(
                    status_code=422,
                    detail=error_detail.model_dump()
                )

            # Inject version info into request for endpoint use
            # Check if there's a Request object in args to inject into
            for arg in args:
                if isinstance(arg, Request):
                    arg.state.version_info = version_info
                    break

            logger.info(f"Version validation passed: {tag_spool} is v4.0")
            return await func(*args, **kwargs)

        return wrapper
    return decorator
