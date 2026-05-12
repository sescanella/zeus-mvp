"""
Repositorio para el spreadsheet de auditoría del supervisor (ZEUES_App_Audit).

Tres tabs:
- Lista: mutable, una fila por TAG_SPOOL que Matías está siguiendo.
- Audit: append-only, eventos de UI deduplicados por ID.
- Snapshots_Legacy: append-only, dumps verbatim de localStorage para Capa 0.

Acceso vía sheets_repo.open_spreadsheet(config.GOOGLE_AUDIT_SHEET_ID) — NO usar
SheetsRepository.read_worksheet(), que está hardcoded al sheet de operaciones
y comparte un cache global keyed solo por nombre de tab (sería ambiguo si
ambos libros tuvieran tabs con el mismo nombre).
"""
import logging
from datetime import datetime
from typing import Optional

import gspread

from backend.config import config
from backend.exceptions import SheetsConnectionError, SheetsUpdateError
from backend.models.supervisor import (
    AuditEvent,
    LegacySnapshot,
    TrackedSpool,
)
from backend.repositories.metadata_repository import retry_on_sheets_error
from backend.repositories.sheets_repository import SheetsRepository
from backend.utils.sanitize import sanitize_row_for_sheets


def _col_letter(idx0: int) -> str:
    """1-indexed column → A, B, ..., Z, AA, AB, ... (idx0 es 0-indexed)."""
    n = idx0 + 1
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class SupervisorRepository:
    """
    Repositorio para el spreadsheet ZEUES_App_Audit.

    Pasa por sheets_repo.open_spreadsheet(config.GOOGLE_AUDIT_SHEET_ID), que
    reusa el mismo gspread.Client autenticado. NO usa los wrappers de
    SheetsRepository.read_worksheet/find_row_by_column_value porque están
    hardcoded al sheet de operaciones.
    """

    CHUNK_SIZE = 900  # gspread safe append_rows chunk size

    EXPECTED_HEADERS: dict[str, list[str]] = {
        config.HOJA_AUDIT_LISTA_NOMBRE: [
            "TAG_SPOOL", "Added_At", "Updated_At", "Notes",
        ],
        config.HOJA_AUDIT_EVENTS_NOMBRE: [
            "ID", "Timestamp", "Session_ID", "Event_Type",
            "TAG_SPOOL", "Modal", "Route", "Payload_JSON",
        ],
        config.HOJA_AUDIT_SNAPSHOTS_NOMBRE: [
            "Snapshot_ID", "Captured_At", "Raw_JSON", "User_Agent",
        ],
    }

    def __init__(self, sheets_repo: SheetsRepository):
        self.logger = logging.getLogger(__name__)
        self.sheets_repo = sheets_repo
        self._worksheets: dict[str, gspread.Worksheet] = {}

    # ─── Worksheet access ────────────────────────────────────────────────

    def _get_ws(self, name: str) -> gspread.Worksheet:
        """Lazy-load y cachea la worksheet del audit spreadsheet."""
        if name not in self._worksheets:
            try:
                sh = self.sheets_repo.open_spreadsheet(config.GOOGLE_AUDIT_SHEET_ID)
                self._worksheets[name] = sh.worksheet(name)
                self.logger.info(f"Audit worksheet '{name}' cargada")
            except gspread.exceptions.WorksheetNotFound:
                raise SheetsConnectionError(
                    f"Tab '{name}' no encontrada en spreadsheet de auditoría",
                    details=f"audit_sheet_id={config.GOOGLE_AUDIT_SHEET_ID}",
                )
        return self._worksheets[name]

    # ─── Lista (mutable: upsert + delete) ────────────────────────────────

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def list_tracked_spools(self) -> list[TrackedSpool]:
        """
        Lee toda la tab Lista. Tolera errores de parseo por fila.
        """
        ws = self._get_ws(config.HOJA_AUDIT_LISTA_NOMBRE)
        try:
            all_values = ws.get_all_values()
        except gspread.exceptions.APIError as e:
            raise SheetsConnectionError(
                "Error leyendo tab Lista",
                details=str(e),
            )

        if len(all_values) <= 1:
            return []

        out: list[TrackedSpool] = []
        for row_idx, row in enumerate(all_values[1:], start=2):
            if not row or not row[0].strip():
                continue  # fila vacía → ignorar
            try:
                out.append(TrackedSpool.from_sheets_row(row))
            except Exception as e:
                self.logger.warning(
                    f"Lista row {row_idx} no parsea: {e}; row={row}"
                )
                continue

        return out

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def find_tracked_row(self, tag_spool: str) -> Optional[int]:
        """
        Devuelve el número de fila 1-indexed del TAG_SPOOL en Lista, o None.

        Usa col_values(1) — una sola columna, evita leer todo el libro.
        """
        ws = self._get_ws(config.HOJA_AUDIT_LISTA_NOMBRE)
        try:
            col = ws.col_values(1)  # column A = TAG_SPOOL
        except gspread.exceptions.APIError as e:
            raise SheetsConnectionError(
                "Error leyendo columna TAG_SPOOL en Lista",
                details=str(e),
            )

        # col[0] es el header; buscar a partir de fila 2.
        target = tag_spool.strip()
        for idx, value in enumerate(col[1:], start=2):
            if value.strip() == target:
                return idx
        return None

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def upsert_tracked_spool(self, spool: TrackedSpool) -> TrackedSpool:
        """
        Inserta o actualiza la fila de un spool. Garantiza una sola fila por TAG_SPOOL.

        Comportamiento:
        - Si la tag ya existe → actualiza A:D de esa fila (single API call).
        - Si no existe → append_row al final.

        Returns el TrackedSpool tal como quedó persistido.
        """
        row_data = sanitize_row_for_sheets(spool.to_sheets_row())
        ws = self._get_ws(config.HOJA_AUDIT_LISTA_NOMBRE)

        existing_row = self.find_tracked_row(spool.tag_spool)

        try:
            if existing_row is not None:
                # Update A{row}:D{row} — 4 columnas en un solo call.
                end_col = _col_letter(len(row_data) - 1)  # "D" para 4 cols
                cell_range = f"A{existing_row}:{end_col}{existing_row}"
                ws.update(
                    range_name=cell_range,
                    values=[row_data],
                    value_input_option="USER_ENTERED",
                )
                self.logger.info(
                    f"Lista: actualizada fila {existing_row} para {spool.tag_spool}"
                )
            else:
                ws.append_row(row_data, value_input_option="USER_ENTERED")
                self.logger.info(f"Lista: append nuevo TAG {spool.tag_spool}")
        except gspread.exceptions.APIError as e:
            raise SheetsUpdateError(
                f"Error escribiendo Lista para {spool.tag_spool}",
                details=str(e),
            )

        return spool

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def remove_tracked_spool(self, tag_spool: str) -> bool:
        """
        Borra la fila de un TAG_SPOOL en Lista. Idempotente.

        Returns:
            True si se borró una fila, False si la tag no existía.
        """
        row_num = self.find_tracked_row(tag_spool)
        if row_num is None:
            self.logger.info(
                f"Lista: remove no-op, TAG {tag_spool} no encontrado"
            )
            return False

        ws = self._get_ws(config.HOJA_AUDIT_LISTA_NOMBRE)
        try:
            ws.delete_rows(row_num)
        except gspread.exceptions.APIError as e:
            raise SheetsUpdateError(
                f"Error borrando fila Lista para {tag_spool}",
                details=str(e),
            )

        self.logger.info(f"Lista: borrada fila {row_num} para {tag_spool}")
        return True

    # ─── Audit (append-only con dedup por ID) ────────────────────────────

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def append_audit_events(self, events: list[AuditEvent]) -> int:
        """
        Append eventos a la tab Audit, deduplicando por `id` contra lo que ya existe.

        Lee solo la columna A (IDs) para dedup — barato.
        Auto-chunkea en CHUNK_SIZE filas para evitar pegarle a límites de gspread.

        Returns:
            int: cantidad de eventos efectivamente escritos (post-dedup).
        """
        if not events:
            return 0

        ws = self._get_ws(config.HOJA_AUDIT_EVENTS_NOMBRE)

        # Lectura barata de IDs ya presentes.
        try:
            existing_ids = set(ws.col_values(1)[1:])  # skip header
        except gspread.exceptions.APIError as e:
            raise SheetsConnectionError(
                "Error leyendo IDs existentes en Audit",
                details=str(e),
            )

        new_events = [e for e in events if e.id not in existing_ids]
        skipped = len(events) - len(new_events)

        if not new_events:
            self.logger.info(
                f"Audit: todos los {len(events)} eventos ya existían (dedup), "
                f"nada que escribir."
            )
            return 0

        rows = [sanitize_row_for_sheets(e.to_sheets_row()) for e in new_events]
        chunks = [
            rows[i : i + self.CHUNK_SIZE]
            for i in range(0, len(rows), self.CHUNK_SIZE)
        ]

        try:
            for chunk_idx, chunk in enumerate(chunks, start=1):
                ws.append_rows(chunk, value_input_option="USER_ENTERED")
                self.logger.info(
                    f"Audit: chunk {chunk_idx}/{len(chunks)} appended "
                    f"({len(chunk)} eventos)"
                )
        except gspread.exceptions.APIError as e:
            raise SheetsUpdateError(
                f"Error appendeando eventos a Audit",
                details=str(e),
            )

        self.logger.info(
            f"Audit: {len(new_events)} eventos escritos "
            f"({skipped} skipped por dedup)"
        )
        return len(new_events)

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def get_audit_events_since(self, since: datetime) -> list[AuditEvent]:
        """
        Lee tab Audit y filtra eventos con timestamp >= since.
        Tolera errores de parseo por fila.
        """
        ws = self._get_ws(config.HOJA_AUDIT_EVENTS_NOMBRE)
        try:
            all_values = ws.get_all_values()
        except gspread.exceptions.APIError as e:
            raise SheetsConnectionError(
                "Error leyendo tab Audit",
                details=str(e),
            )

        if len(all_values) <= 1:
            return []

        events: list[AuditEvent] = []
        for row_idx, row in enumerate(all_values[1:], start=2):
            if not row or not row[0].strip():
                continue
            try:
                evt = AuditEvent.from_sheets_row(row)
            except Exception as e:
                self.logger.warning(
                    f"Audit row {row_idx} no parsea: {e}"
                )
                continue
            if evt.timestamp >= since:
                events.append(evt)

        events.sort(key=lambda e: e.timestamp)
        return events

    # ─── Snapshots_Legacy (append-only, dedup por snapshot_id) ───────────

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def append_legacy_snapshot(self, snapshot: LegacySnapshot) -> bool:
        """
        Append un snapshot. Idempotente por snapshot_id.

        Returns:
            True si se escribió la fila, False si snapshot_id ya existía.
        """
        ws = self._get_ws(config.HOJA_AUDIT_SNAPSHOTS_NOMBRE)

        try:
            existing_ids = set(ws.col_values(1)[1:])  # skip header
        except gspread.exceptions.APIError as e:
            raise SheetsConnectionError(
                "Error leyendo Snapshot_IDs existentes",
                details=str(e),
            )

        if snapshot.snapshot_id in existing_ids:
            self.logger.info(
                f"Snapshots_Legacy: {snapshot.snapshot_id} ya existe (no-op)"
            )
            return False

        row = sanitize_row_for_sheets(snapshot.to_sheets_row())
        try:
            ws.append_row(row, value_input_option="USER_ENTERED")
        except gspread.exceptions.APIError as e:
            raise SheetsUpdateError(
                f"Error appendeando snapshot {snapshot.snapshot_id}",
                details=str(e),
            )

        self.logger.info(
            f"Snapshots_Legacy: snapshot {snapshot.snapshot_id} escrito "
            f"({len(snapshot.raw)} bytes)"
        )
        return True

    # ─── Schema validation (called from startup) ─────────────────────────

    @retry_on_sheets_error(max_retries=3, backoff_seconds=1.0)
    def validate_schema(self) -> None:
        """
        Verifica que las 3 tabs existen y tienen los headers esperados.

        Llamada desde backend/scripts/validate_schema_startup.py para que el
        backend se niegue a arrancar si el spreadsheet de auditoría está
        mal configurado (e.g. PROD apuntando a sheet de DEV).

        Raises:
            SheetsConnectionError: Si alguna tab falta o el header es incorrecto.
        """
        for tab_name, expected in self.EXPECTED_HEADERS.items():
            ws = self._get_ws(tab_name)  # ya lanza SheetsConnectionError si falta
            try:
                actual = ws.row_values(1)
            except gspread.exceptions.APIError as e:
                raise SheetsConnectionError(
                    f"Error leyendo headers de '{tab_name}'",
                    details=str(e),
                )

            if actual != expected:
                raise SheetsConnectionError(
                    f"Headers incorrectos en tab '{tab_name}'",
                    details=(
                        f"esperado={expected} actual={actual} "
                        f"audit_sheet_id={config.GOOGLE_AUDIT_SHEET_ID}"
                    ),
                )

        self.logger.info(
            f"✅ validate_schema OK para spreadsheet auditoría "
            f"({config.GOOGLE_AUDIT_SHEET_ID})"
        )
