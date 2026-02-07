"""
Health Check Router - Monitoreo del estado del sistema.

Endpoint para verificar que la API está funcionando y que la conexión
con Google Sheets está operativa. Usado por Railway y monitoreo externo.

Endpoints:
- GET /api/health - Health check con test de conexión Sheets

Note: Single-user mode - No Redis health check needed.
"""

from fastapi import APIRouter, Depends, status
from datetime import datetime

from backend.core.dependency import get_sheets_repository
from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Health check endpoint para monitoreo del sistema.

    Simplified for single-user mode: Only checks Google Sheets.

    Verifica:
    - Estado general de la API (si responde, está "alive")
    - Conexión con Google Sheets (intenta leer hoja Trabajadores)

    Status logic:
    - "healthy": Sheets OK
    - "unhealthy": Sheets FAIL (core features unavailable)

    Args:
        sheets_repo: Repositorio de Google Sheets (inyectado automáticamente).

    Returns:
        Dict con:
        - status: "healthy" or "unhealthy"
        - operational: Boolean indicating if core features work
        - timestamp: Timestamp UTC actual (ISO 8601 format)
        - environment: Ambiente de ejecución (development/production)
        - sheets_connection: "ok" si Sheets responde, "error" si falla
        - version: Versión de la API

    Raises:
        No lanza excepciones. Siempre retorna 200 OK con status apropiado.

    Example response (healthy):
        ```json
        {
            "status": "healthy",
            "operational": true,
            "timestamp": "2026-02-04T14:30:00Z",
            "environment": "production",
            "sheets_connection": "ok",
            "version": "4.0.0-single-user"
        }
        ```

    Usage:
        ```bash
        curl http://localhost:8000/api/health
        ```
    """
    logger.info("Health check requested (single-user mode)")

    # Test conexión Google Sheets (intentar leer 1 fila de Trabajadores)
    sheets_status = "ok"
    sheets_error = None
    try:
        sheets_repo.read_worksheet(config.HOJA_TRABAJADORES_NOMBRE)
        logger.debug("Sheets connection test successful")
    except Exception as e:
        logger.error(f"Health check failed: Sheets connection error - {str(e)}")
        sheets_status = "error"
        sheets_error = str(e)

    # Determine overall status (simplified: only Sheets matters)
    if sheets_status == "ok":
        status_value = "healthy"
        operational = True
    else:
        status_value = "unhealthy"
        operational = False

    # Construir response
    response = {
        "status": status_value,
        "operational": operational,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": config.ENVIRONMENT,
        "sheets_connection": sheets_status,
        "version": "4.0.0-single-user"
    }

    # Add error details if present
    if sheets_error:
        response["details"] = {"sheets_error": sheets_error}

    return response


@router.get("/health/diagnostic", status_code=status.HTTP_200_OK)
async def diagnostic_check(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    Diagnostic endpoint para troubleshooting de problemas de despliegue.

    Expone información útil sobre la configuración sin revelar credenciales:
    - GOOGLE_SHEET_ID parcialmente enmascarado
    - Lista de hojas disponibles en el spreadsheet
    - Si la hoja "Roles" existe
    - Cuántos roles hay en la hoja "Roles"

    Este endpoint es temporal y solo debe usarse para debugging.
    """
    logger.info("Diagnostic check requested")

    diagnostic_info = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": config.ENVIRONMENT,
        "google_sheet_id_masked": f"{config.GOOGLE_SHEET_ID[:8]}...{config.GOOGLE_SHEET_ID[-8:]}",
        "config_sheet_names": {
            "operaciones": config.HOJA_OPERACIONES_NOMBRE,
            "trabajadores": config.HOJA_TRABAJADORES_NOMBRE,
            "metadata": config.HOJA_METADATA_NOMBRE,
        }
    }

    # Intentar listar hojas disponibles
    try:
        spreadsheet = sheets_repo._get_spreadsheet()
        all_worksheets = spreadsheet.worksheets()

        diagnostic_info["spreadsheet_title"] = spreadsheet.title
        diagnostic_info["available_sheets"] = [ws.title for ws in all_worksheets]
        diagnostic_info["total_sheets"] = len(all_worksheets)

        # Verificar si hoja "Roles" existe
        roles_sheet_exists = "Roles" in diagnostic_info["available_sheets"]
        diagnostic_info["roles_sheet_exists"] = roles_sheet_exists

        if roles_sheet_exists:
            try:
                roles_sheet = spreadsheet.worksheet("Roles")
                all_records = roles_sheet.get_all_records()
                diagnostic_info["roles_count"] = len(all_records)

                # Contar roles activos
                active_roles = [r for r in all_records if str(r.get('Activo', '')).upper() == 'TRUE']
                diagnostic_info["active_roles_count"] = len(active_roles)
            except Exception as e:
                diagnostic_info["roles_error"] = str(e)
        else:
            diagnostic_info["roles_count"] = 0
            diagnostic_info["active_roles_count"] = 0

    except Exception as e:
        diagnostic_info["error"] = str(e)
        diagnostic_info["error_type"] = type(e).__name__

    return diagnostic_info


@router.get("/health/column-map", status_code=status.HTTP_200_OK)
async def column_map_debug(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    TEMPORARY DEBUG ENDPOINT - Shows column mapping for Operaciones sheet.

    This helps diagnose column index issues in production.
    """
    logger.info("Column map debug requested")

    try:
        from backend.core.column_map_cache import ColumnMapCache
        from backend.config import config

        # Get column map
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, sheets_repo)

        # Find TAG_SPOOL column specifically
        tag_spool_index = column_map.get("tagspool") or column_map.get("split")

        # Get first few rows for context
        all_rows = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        header = all_rows[0] if all_rows else []

        # Search for TEST-02 specifically
        test_spool_search = None
        if len(all_rows) > 1:
            for row_idx, row_data in enumerate(all_rows[1:], start=2):
                if tag_spool_index is not None and tag_spool_index < len(row_data):
                    if row_data[tag_spool_index] == "TEST-02":
                        test_spool_search = {
                            "found": True,
                            "row_number": row_idx,
                            "tag_column_index": tag_spool_index,
                            "tag_value": row_data[tag_spool_index]
                        }
                        break

        if test_spool_search is None:
            test_spool_search = {"found": False, "tag_column_index": tag_spool_index}

        # Now test get_spool_by_tag directly with detailed logging
        try:
            # Manual simulation of get_spool_by_tag logic
            def normalize(name: str) -> str:
                return name.lower().replace(" ", "").replace("_", "").replace("/", "")

            tag_column_names_to_try = ["TAG_SPOOL", "SPLIT", "tag_spool"]
            tag_column_index = None
            tag_column_used = None

            for col_name in tag_column_names_to_try:
                normalized = normalize(col_name)
                if normalized in column_map:
                    tag_column_index = column_map[normalized]
                    tag_column_used = col_name
                    break

            if tag_column_index is None:
                tag_column_index = 6  # Fallback
                tag_column_used = "FALLBACK_G"

            # Convert index to column letter
            column_letter = sheets_repo._index_to_column_letter(tag_column_index)

            # Try find_row_by_column_value
            row_num = sheets_repo.find_row_by_column_value(
                sheet_name=config.HOJA_OPERACIONES_NOMBRE,
                column_letter=column_letter,
                value="TEST-02"
            )

            # Now actually call get_spool_by_tag
            spool_result = sheets_repo.get_spool_by_tag("TEST-02")

            get_spool_status = {
                "success": spool_result is not None,
                "tag_column_used": tag_column_used,
                "tag_column_index": tag_column_index,
                "column_letter": column_letter,
                "find_row_result": row_num,
                "spool_data": {
                    "tag_spool": spool_result.tag_spool if spool_result else None,
                    "armador": spool_result.armador if spool_result else None,
                    "soldador": spool_result.soldador if spool_result else None
                } if spool_result else None
            }
        except Exception as e:
            logger.error(f"get_spool_by_tag test failed: {e}", exc_info=True)
            get_spool_status = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_columns": len(column_map),
            "tag_spool_column_index": tag_spool_index,
            "tag_spool_normalized_keys": [k for k in column_map.keys() if "tag" in k or "split" in k],
            "header_sample": header[:15],  # First 15 column headers
            "test_02_search": test_spool_search,
            "get_spool_by_tag_test": get_spool_status,
            "column_map_sample": {k: v for k, v in list(column_map.items())[:20]}
        }

    except Exception as e:
        logger.error(f"Column map debug failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.get("/health/test-get-spool-flow", status_code=status.HTTP_200_OK)
async def test_get_spool_flow(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    TEMPORARY DEBUG ENDPOINT - Simulates complete get_spool_by_tag flow.

    This reproduces the EXACT flow to diagnose why get_spool_by_tag returns None.
    """
    logger.info("get_spool_by_tag flow test requested")

    try:
        from backend.core.column_map_cache import ColumnMapCache
        from backend.config import config

        # STEP 1: Get column map
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, sheets_repo)

        # STEP 2: Find TAG column
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        tag_column_names_to_try = ["TAG_SPOOL", "SPLIT", "tag_spool"]
        tag_column_index = None
        tag_column_used = None

        for col_name in tag_column_names_to_try:
            normalized = normalize(col_name)
            if normalized in column_map:
                tag_column_index = column_map[normalized]
                tag_column_used = col_name
                break

        if tag_column_index is None:
            tag_column_index = 6
            tag_column_used = "FALLBACK"

        # STEP 3: Convert index to letter
        column_letter = sheets_repo._index_to_column_letter(tag_column_index)

        # STEP 4: Find row (FIRST read_worksheet call)
        row_num = sheets_repo.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=column_letter,
            value="TEST-02"
        )

        if row_num is None:
            return {
                "status": "error",
                "message": "find_row_by_column_value returned None",
                "tag_column_index": tag_column_index,
                "column_letter": column_letter
            }

        # STEP 5: Read worksheet AGAIN (SECOND read_worksheet call - THIS IS THE BUG AREA)
        all_rows_second = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

        # STEP 6: Check the condition
        condition_check = {
            "all_rows_is_none": all_rows_second is None,
            "all_rows_length": len(all_rows_second) if all_rows_second else 0,
            "row_num": row_num,
            "row_num_greater_than_length": row_num > len(all_rows_second) if all_rows_second else True,
            "will_return_none": (not all_rows_second) or (row_num > len(all_rows_second))
        }

        if not all_rows_second or row_num > len(all_rows_second):
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "bug_found",
                "message": "FOUND THE BUG: row_num > len(all_rows) condition triggered",
                **condition_check
            }

        # STEP 7: Call actual get_spool_by_tag and capture result
        try:
            actual_spool = sheets_repo.get_spool_by_tag("TEST-02")
            spool_result = {
                "get_spool_returned": actual_spool is not None,
                "spool_data": {
                    "tag": actual_spool.tag_spool if actual_spool else None,
                    "nv": actual_spool.nv if actual_spool else None
                } if actual_spool else None
            }
        except Exception as e:
            import traceback
            spool_result = {
                "get_spool_error": str(e),
                "error_type": type(e).__name__,
                "traceback_short": traceback.format_exc().split("\n")[-5:]
            }

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "no_bug_in_condition",
            "message": "Condition check passed, testing actual get_spool_by_tag call",
            **condition_check,
            **spool_result
        }

    except Exception as e:
        import traceback
        logger.error(f"get_spool flow test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


@router.get("/health/test-spool-constructor", status_code=status.HTTP_200_OK)
async def test_spool_constructor(
    sheets_repo: SheetsRepository = Depends(get_sheets_repository)
):
    """
    TEMPORARY DEBUG ENDPOINT - Tests Spool constructor with TEST-02 data.

    This helps diagnose why Spool construction is failing.
    """
    logger.info("Spool constructor test requested")

    try:
        from backend.models.spool import Spool
        from backend.core.column_map_cache import ColumnMapCache
        from backend.config import config
        from datetime import datetime

        # Get row data for TEST-02
        all_rows = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
        column_map = ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, sheets_repo)

        # Find TEST-02
        tag_index = column_map.get("tagspool", 6)
        row_data = None
        row_num = None
        for idx, row in enumerate(all_rows[1:], start=2):
            if tag_index < len(row) and row[tag_index] == "TEST-02":
                row_data = row
                row_num = idx
                break

        if not row_data:
            return {"error": "TEST-02 not found in sheet"}

        # Helper functions
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "").replace("_", "").replace("/", "")

        def get_col_value(col_name: str):
            normalized = normalize(col_name)
            if normalized not in column_map:
                return None
            col_index = column_map[normalized]
            if col_index < len(row_data):
                value = row_data[col_index]
                return value if value and str(value).strip() else None
            return None

        # Extract values
        values = {
            "tag_spool": "TEST-02",
            "nv": get_col_value("NV"),
            "armador": get_col_value("Armador"),
            "soldador": get_col_value("Soldador"),
            "fecha_materiales_raw": get_col_value("Fecha_Materiales"),
            "fecha_armado_raw": get_col_value("Fecha_Armado"),
            "fecha_soldadura_raw": get_col_value("Fecha_Soldadura"),
        }

        # Parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                from datetime import datetime as dt
                # Try YYYY-MM-DD
                return dt.strptime(str(date_str), "%Y-%m-%d").date()
            except ValueError:
                try:
                    # Try DD/MM/YYYY
                    return dt.strptime(str(date_str), "%d/%m/%Y").date()
                except ValueError:
                    try:
                        # Try DD-MM-YYYY
                        return dt.strptime(str(date_str), "%d-%m-%Y").date()
                    except ValueError:
                        return None

        # Get ALL fields that get_spool_by_tag uses
        all_values = {
            **values,
            "fecha_qc_metrologia_raw": get_col_value("Fecha_QC_Metrología"),
            "ocupado_por": get_col_value("Ocupado_Por"),
            "fecha_ocupacion": get_col_value("Fecha_Ocupacion"),
            "version": get_col_value("version"),
            "estado_detalle": get_col_value("Estado_Detalle"),
        }

        # Try to construct Spool EXACTLY like get_spool_by_tag (v2.1 mode)
        try:
            spool = Spool(
                tag_spool="TEST-02",
                nv=all_values["nv"],
                fecha_materiales=parse_date(all_values["fecha_materiales_raw"]),
                fecha_armado=parse_date(all_values["fecha_armado_raw"]),
                fecha_soldadura=parse_date(all_values["fecha_soldadura_raw"]),
                fecha_qc_metrologia=parse_date(all_values["fecha_qc_metrologia_raw"]),
                armador=all_values["armador"],
                soldador=all_values["soldador"],
                ocupado_por=None,  # v2.1 mode
                fecha_ocupacion=None,  # v2.1 mode
                version=0,  # v2.1 mode
                estado_detalle=None,  # v2.1 mode
            )
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "success",
                "row_number": row_num,
                "extracted_values": all_values,
                "parsed_dates": {
                    "fecha_materiales": str(parse_date(all_values["fecha_materiales_raw"])),
                    "fecha_armado": str(parse_date(all_values["fecha_armado_raw"])),
                    "fecha_soldadura": str(parse_date(all_values["fecha_soldadura_raw"])),
                    "fecha_qc_metrologia": str(parse_date(all_values["fecha_qc_metrologia_raw"])),
                },
                "spool_created": True,
                "spool_data": {
                    "tag_spool": spool.tag_spool,
                    "nv": spool.nv,
                    "armador": spool.armador,
                    "soldador": spool.soldador,
                    "fecha_materiales": str(spool.fecha_materiales) if spool.fecha_materiales else None,
                    "ocupado_por": spool.ocupado_por,
                    "version": spool.version
                }
            }
        except Exception as e:
            import traceback
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "error",
                "row_number": row_num,
                "extracted_values": all_values,
                "spool_created": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

    except Exception as e:
        import traceback
        logger.error(f"Spool constructor test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


@router.get("/health/clear-cache", status_code=status.HTTP_200_OK)
async def clear_cache():
    """
    TEMPORARY DEBUG ENDPOINT - Clears the column map cache.

    Forces a rebuild of column mapping on next request.
    """
    logger.info("Cache clear requested")

    try:
        from backend.core.column_map_cache import ColumnMapCache

        # Get cached sheets before clearing
        cached_before = ColumnMapCache.get_cached_sheets()

        # Clear all caches
        ColumnMapCache.clear_all()

        # Get cached sheets after clearing (should be empty)
        cached_after = ColumnMapCache.get_cached_sheets()

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "success",
            "cached_sheets_before": cached_before,
            "cached_sheets_after": cached_after,
            "message": "Column map cache cleared. Next API call will rebuild cache."
        }

    except Exception as e:
        logger.error(f"Cache clear failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }


