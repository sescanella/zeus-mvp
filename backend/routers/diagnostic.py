"""
Diagnostic Router - Version detection and system diagnostics.

Provides endpoints for version detection diagnostics and troubleshooting.
"""
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from backend.services.version_detection_service import VersionDetectionService
from backend.models.version import VersionResponse, VersionInfo
from backend.core.dependency import get_sheets_repository
from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.exceptions import SpoolNoEncontradoError
from backend.config import config


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


def get_version_service(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
) -> VersionDetectionService:
    """
    Dependency injection for VersionDetectionService.

    Args:
        sheets_repo: SheetsRepository instance (injected by FastAPI)

    Returns:
        VersionDetectionService instance
    """
    return VersionDetectionService(sheets_repository=sheets_repo)


@router.get("/{tag}/version", response_model=VersionResponse, status_code=status.HTTP_200_OK)
async def get_spool_version(
    tag: str,
    version_service: VersionDetectionService = Depends(get_version_service)
):
    """
    Detect spool version (v3.0 vs v4.0) based on union count.

    Queries Total_Uniones column (68) from Operaciones sheet and determines
    version based on union count:
    - v4.0: union_count > 0 (Engineering populated unions)
    - v3.0: union_count = 0 or None (legacy workflow)

    Includes retry logic with exponential backoff (3 attempts, 2s/4s/10s).
    Defaults to v3.0 on detection failure (safer legacy workflow).

    Args:
        tag: TAG_SPOOL identifier (path parameter)
        version_service: VersionDetectionService (injected)

    Returns:
        VersionResponse with:
        - success: True
        - data: VersionInfo with version, union_count, detection_logic

    Raises:
        404 Not Found: If spool doesn't exist in Operaciones sheet
        503 Service Unavailable: If Sheets connection fails after retries
        200 OK with v3.0 default: If detection fails (included in detection_logic)

    Example response (v4.0 spool):
        ```json
        {
            "success": true,
            "data": {
                "version": "v4.0",
                "union_count": 8,
                "detection_logic": "Total_Uniones=8 -> v4.0",
                "tag_spool": "TEST-02"
            }
        }
        ```

    Example response (v3.0 spool):
        ```json
        {
            "success": true,
            "data": {
                "version": "v3.0",
                "union_count": 0,
                "detection_logic": "Total_Uniones=0 -> v3.0",
                "tag_spool": "OLD-SPOOL"
            }
        }
        ```

    Example response (detection failed):
        ```json
        {
            "success": true,
            "data": {
                "version": "v3.0",
                "union_count": 0,
                "detection_logic": "Detection failed, defaulting to v3.0: Sheets timeout",
                "tag_spool": "UNKNOWN"
            }
        }
        ```

    Usage:
        ```bash
        curl -X GET http://localhost:8000/api/diagnostic/TEST-02/version
        ```
    """
    logger.info(f"Version detection requested for spool: {tag}")

    try:
        # Detect version with retry logic
        version_info_dict = await version_service.detect_version(tag)

        # Convert dict to VersionInfo model
        version_info = VersionInfo(**version_info_dict)

        # Wrap in response
        response = VersionResponse(success=True, data=version_info)

        logger.info(
            f"Version detection complete for {tag}: {version_info.version} "
            f"(union_count={version_info.union_count})"
        )

        return response

    except SpoolNoEncontradoError as e:
        # Spool doesn't exist - 404
        logger.error(f"Spool not found: {tag}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": e.error_code,
                "message": e.message,
                "data": e.data
            }
        )

    except Exception as e:
        # Unexpected error - log and re-raise
        logger.error(f"Version detection failed unexpectedly for {tag}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "VERSION_DETECTION_ERROR",
                "message": f"Failed to detect version for spool {tag}: {str(e)}"
            }
        )


@router.get("/compatibility-mode", status_code=status.HTTP_200_OK)
async def get_compatibility_mode(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Returns the current compatibility mode of SheetsRepository singleton.

    Expected: "v3.0" for REPARACION features to work.
    """
    return {
        "compatibility_mode": sheets_repo._compatibility_mode,
        "expected": "v3.0",
        "status": "OK" if sheets_repo._compatibility_mode == "v3.0" else "MISMATCH"
    }


@router.get("/test-03-raw", status_code=status.HTTP_200_OK)
async def get_test_03_raw_data(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Reads TEST-03 spool directly from Google Sheets and shows raw parsing.

    This bypasses filters to show exactly what the repository is reading.
    """
    # Get column map
    column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, sheets_repo)

    # Read all rows
    all_rows = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

    # Find TEST-03
    tag_idx = column_map["tagspool"]
    estado_idx = column_map["estadodetalle"]
    ocupado_idx = column_map["ocupadopor"]

    for i, row in enumerate(all_rows[1:], start=2):  # Skip header
        if len(row) > tag_idx and row[tag_idx] == "TEST-03":
            tag_value = row[tag_idx] if len(row) > tag_idx else ""
            estado_value = row[estado_idx] if len(row) > estado_idx else ""
            ocupado_value = row[ocupado_idx] if len(row) > ocupado_idx else ""

            # Now parse using repository method
            spool = sheets_repo.get_spool_by_tag("TEST-03")

            return {
                "found": True,
                "row_number": i,
                "raw_data": {
                    "TAG_SPOOL": tag_value,
                    "Estado_Detalle_raw": estado_value,
                    "Ocupado_Por_raw": ocupado_value
                },
                "parsed_spool": {
                    "tag_spool": spool.tag_spool if spool else None,
                    "estado_detalle": spool.estado_detalle if spool else None,
                    "ocupado_por": spool.ocupado_por if spool else None
                },
                "compatibility_mode": sheets_repo._compatibility_mode,
                "diagnosis": {
                    "raw_has_rechazado": "RECHAZADO" in estado_value if estado_value else False,
                    "parsed_has_rechazado": "RECHAZADO" in spool.estado_detalle if spool and spool.estado_detalle else False,
                    "should_appear": "RECHAZADO" in estado_value and not ocupado_value
                }
            }

    return {
        "found": False,
        "message": "TEST-03 not found in Google Sheets",
        "compatibility_mode": sheets_repo._compatibility_mode
    }
