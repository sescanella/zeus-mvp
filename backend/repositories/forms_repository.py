"""
Repository for Forms data access (NoConformidad sheet).

Modular monolith pattern: isolated forms module reusing SheetsRepository singleton.
"""
import gspread
import logging
from typing import Optional

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import retry_on_sheets_error
from backend.exceptions import SheetsConnectionError, SheetsUpdateError

NOCONFORMIDAD_SHEET_NAME = "NoConformidad"
NOCONFORMIDAD_HEADERS = [
    "ID", "Fecha", "TAG_SPOOL", "Worker_ID", "Worker_Nombre",
    "Origen", "Tipo_NC", "Descripcion"
]


class FormsRepository:
    """Repository for forms data access (append-only)."""

    def __init__(self, sheets_repo: SheetsRepository):
        self.logger = logging.getLogger(__name__)
        self.sheets_repo = sheets_repo
        self._worksheet: Optional[gspread.Worksheet] = None

    def _get_worksheet(self) -> gspread.Worksheet:
        """Get NoConformidad worksheet (lazy loading with auto-header setup)."""
        if not self._worksheet:
            spreadsheet = self.sheets_repo._get_spreadsheet()
            try:
                self._worksheet = spreadsheet.worksheet(NOCONFORMIDAD_SHEET_NAME)
            except gspread.exceptions.WorksheetNotFound:
                raise SheetsConnectionError(
                    f"Sheet '{NOCONFORMIDAD_SHEET_NAME}' not found in spreadsheet. "
                    "Please create it manually."
                )

            # Auto-setup headers if sheet is empty
            try:
                first_row = self._worksheet.row_values(1)
                if not first_row:
                    self._worksheet.append_row(
                        NOCONFORMIDAD_HEADERS,
                        value_input_option='USER_ENTERED'
                    )
                    self.logger.info(
                        f"Headers written to '{NOCONFORMIDAD_SHEET_NAME}': "
                        f"{NOCONFORMIDAD_HEADERS}"
                    )
            except Exception as e:
                self.logger.warning(f"Could not check/write headers: {e}")

            self.logger.info(f"Sheet '{NOCONFORMIDAD_SHEET_NAME}' loaded")

        return self._worksheet

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def append_no_conformidad(self, row_data: list) -> None:
        """
        Append a No Conformidad row to the sheet.

        Args:
            row_data: List matching NOCONFORMIDAD_HEADERS order.

        Raises:
            SheetsUpdateError: If write fails.
        """
        try:
            worksheet = self._get_worksheet()
            worksheet.append_row(row_data, value_input_option='USER_ENTERED')
            self.logger.info(f"No Conformidad row appended: ID={row_data[0]}")
        except gspread.exceptions.APIError as e:
            raise SheetsUpdateError(
                f"Error writing No Conformidad row",
                updates={"error": str(e)}
            )
        except Exception as e:
            raise SheetsUpdateError(
                f"Unexpected error writing No Conformidad",
                updates={"error": str(e)}
            )
