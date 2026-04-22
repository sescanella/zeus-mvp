"""
NotasService — F-1 Spool notes (v5.1).

Append-only free-text notes per spool. Notes are stored as a single cell
in the Operaciones sheet's `Notas` column. Each saved entry is appended
with a date prefix in YYYYMMDD format, matching the convention already
used by planning (e.g. "20260415: lanzada a producción").

History is never overwritten — previous lines are always preserved.
Every append is also logged as NOTAS_ACTUALIZADA in the Metadata sheet
for ISO 9001 audit trail.
"""

import logging
from typing import Optional

from backend.config import config
from backend.exceptions import SpoolNoEncontradoError, WorkerNoEncontradoError
from backend.repositories.metadata_repository import MetadataRepository
from backend.repositories.sheets_repository import SheetsRepository
from backend.services.worker_service import WorkerService
from backend.utils.date_formatter import format_date_yyyymmdd, today_chile

logger = logging.getLogger(__name__)


class NotasService:
    """Servicio para leer y agregar notas a un spool."""

    NOTAS_COLUMN = "Notas"

    def __init__(
        self,
        sheets_repository: SheetsRepository,
        metadata_repository: MetadataRepository,
        worker_service: WorkerService,
    ):
        self.sheets_repository = sheets_repository
        self.metadata_repository = metadata_repository
        self.worker_service = worker_service

    def get_nota(self, tag_spool: str) -> str:
        """
        Lee el contenido actual de la columna Notas para un spool.

        Args:
            tag_spool: TAG del spool

        Returns:
            str: Contenido actual de la celda Notas (string vacío si nunca se escribió)

        Raises:
            SpoolNoEncontradoError: si el spool no existe
        """
        spool = self.sheets_repository.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        row_num = self._find_spool_row(tag_spool)
        current = self.sheets_repository.get_cell_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name=self.NOTAS_COLUMN,
        )
        return current or ""

    def append_nota(
        self,
        tag_spool: str,
        worker_id: int,
        texto: str,
    ) -> str:
        """
        Agrega una nueva entrada al final de la columna Notas del spool.

        La entrada se formatea como "YYYYMMDD: {texto}" y se concatena con
        un salto de línea al contenido previo. Se registra un evento
        NOTAS_ACTUALIZADA en la hoja Metadata.

        Args:
            tag_spool: TAG del spool
            worker_id: ID del trabajador autor de la nota
            texto: Texto de la nota (sin prefijo de fecha, se agrega aquí)

        Returns:
            str: Contenido completo de la celda Notas después del append

        Raises:
            SpoolNoEncontradoError: si el spool no existe
            WorkerNoEncontradoError: si el trabajador no existe en Trabajadores
            ValueError: si texto es vacío después de trim
        """
        clean_text = (texto or "").strip()
        if not clean_text:
            raise ValueError("El texto de la nota no puede estar vacío")

        worker = self.worker_service.find_worker_by_id(worker_id)
        if not worker:
            raise WorkerNoEncontradoError(str(worker_id))

        spool = self.sheets_repository.get_spool_by_tag(tag_spool)
        if not spool:
            raise SpoolNoEncontradoError(tag_spool)

        row_num = self._find_spool_row(tag_spool)

        # Read current content and append new entry
        current = self.sheets_repository.get_cell_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name=self.NOTAS_COLUMN,
        ) or ""

        prefix = format_date_yyyymmdd(today_chile())
        new_entry = f"{prefix}: {clean_text}"
        new_content = f"{current}\n{new_entry}" if current else new_entry

        # Write back to Sheet
        self.sheets_repository.update_cell_by_column_name(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            row=row_num,
            column_name=self.NOTAS_COLUMN,
            value=new_content,
        )

        # Audit trail — ISO 9001 append-only event
        try:
            import json

            self.metadata_repository.log_event(
                evento_tipo="NOTAS_ACTUALIZADA",
                tag_spool=tag_spool,
                worker_id=worker_id,
                worker_nombre=worker.nombre_completo,
                operacion="NOTAS",
                accion="COMPLETAR",
                metadata_json=json.dumps({"nota": new_entry}, ensure_ascii=False),
            )
        except Exception as exc:
            # Don't fail the user-facing write if audit logging has a transient error;
            # the note is already in the sheet. Log loudly so it can be reconciled.
            logger.error(
                f"NOTAS_ACTUALIZADA audit event failed for {tag_spool} "
                f"(worker {worker_id}): {exc}",
                exc_info=True,
            )

        logger.info(
            f"✅ Nota agregada a {tag_spool} por {worker.nombre_completo}: "
            f"{len(clean_text)} caracteres"
        )
        return new_content

    def _find_spool_row(self, tag_spool: str) -> int:
        """Resuelve el número de fila (1-indexed) del spool en Operaciones."""
        from backend.core.column_map_cache import ColumnMapCache

        column_map = ColumnMapCache.get_or_build(
            config.HOJA_OPERACIONES_NOMBRE, self.sheets_repository
        )
        from backend.utils.normalize import normalize_column_name

        tag_key = normalize_column_name("TAG_SPOOL")
        if tag_key not in column_map:
            raise RuntimeError("TAG_SPOOL column not found in column map")

        column_letter = self.sheets_repository._index_to_column_letter(
            column_map[tag_key]
        )
        row_num: Optional[int] = self.sheets_repository.find_row_by_column_value(
            sheet_name=config.HOJA_OPERACIONES_NOMBRE,
            column_letter=column_letter,
            value=tag_spool,
        )
        if row_num is None:
            raise SpoolNoEncontradoError(tag_spool)
        return row_num
