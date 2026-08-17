"""
Single source of truth for the columns the backend depends on per Google
Sheets worksheet.

`critical_columns` MUST be present in the live sheet — if any is missing or
its name no longer matches the cached position, the system raises
CriticalColumnDriftError and surfaces HTTP 503 rather than silently reading
the wrong cell. `expected_columns` are nice-to-have (logged at warning
level if absent). Columns NOT listed here are tolerated freely (added or
removed by Engineering without backend coordination).

Consumers: backend/main.py (startup), backend/core/column_map_cache.py
(drift detection), backend/scripts/validate_schema_startup.py,
backend/routers/admin.py, backend/services/spool_service_v2.py.

Header names use the EXACT casing/punctuation as they appear in the live
sheet. ColumnMapCache normalizes via backend.utils.normalize.normalize_column_name
when looking up, so case/accents/underscores are tolerated at lookup time.
"""
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class SheetSchema:
    sheet_name: str
    critical_columns: frozenset[str]
    expected_columns: frozenset[str]
    # Accepted alternate header names for a canonical column. Maps a canonical
    # name (one that appears in `critical_columns`) to alternate header names
    # the live sheet may legitimately use instead. ColumnMapCache resolves any
    # alias to the canonical column so reads keep working and drift detection
    # does not 503. Example: Engineering renamed "TAG_SPOOL" → "TAG" in PROD;
    # listing "TAG" as an alias keeps the whole Operaciones read path alive
    # without a data fix. Lookup is normalization-insensitive.
    column_aliases: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )


OPERACIONES_SCHEMA = SheetSchema(
    sheet_name="Operaciones",
    critical_columns=frozenset({
        # Identifiers
        "SPLIT",
        "TAG_SPOOL",
        "OT",
        "NV",
        # ARM workflow
        "Fecha_Materiales",
        "Fecha_Armado",
        "Armador",
        # SOLD workflow
        "Fecha_Soldadura",
        "Soldador",
        # QC / metrología
        "Fecha_QC_Metrologia",
        # Occupation lock (v3.0)
        "Ocupado_Por",
        "Fecha_Ocupacion",
        "Estado_Detalle",
    }),
    expected_columns=frozenset({
        # v4.0 counters
        "Total_Uniones",
        "Uniones_ARM_Completadas",
        "Uniones_SOLD_Completadas",
        "Pulgadas_ARM",
        "Pulgadas_SOLD",
        # v5.1 free-text
        "Notas",
    }),
    column_aliases=MappingProxyType({
        # Engineering renamed the spool-tag header in PROD. Accept the
        # alternates so a header rename never tears down the Operaciones
        # read path. Canonical lookups for "TAG_SPOOL" resolve to whichever
        # of these the live header actually uses.
        "TAG_SPOOL": ("TAG", "SPLIT", "tag_spool"),
        # "SPLIT" is not a distinct field: it is the legacy header name for
        # the very same spool-tag column, and code still asks for it by that
        # name (e.g. sheets_service.parse_spool_row). PROD dropped the
        # "SPLIT" header in favour of "TAG", which left this critical column
        # unresolvable and 503'd every Operaciones read. Same alias list as
        # TAG_SPOOL so both canonical names resolve to the live header.
        "SPLIT": ("TAG", "TAG_SPOOL", "tag_spool"),
    }),
)


UNIONES_SCHEMA = SheetSchema(
    sheet_name="Uniones",
    critical_columns=frozenset({
        "ID",
        "OT",
        "N_UNION",
        "TAG_SPOOL",
        "DN_UNION",
        "TIPO_UNION",
        "ARM_FECHA_INICIO",
        "ARM_FECHA_FIN",
        "ARM_WORKER",
        "SOL_FECHA_INICIO",
        "SOL_FECHA_FIN",
        "SOL_WORKER",
        "NDT_UNION",
        "R_NDT_UNION",
        "NDT_FECHA",
        "NDT_STATUS",
        "version",
    }),
    expected_columns=frozenset(),
)


TRABAJADORES_SCHEMA = SheetSchema(
    sheet_name="Trabajadores",
    # Note: per-worker role lives in the separate "Roles" sheet (multi-role
    # support, v2.0). Trabajadores itself only carries identity + active flag.
    critical_columns=frozenset({
        "Id",
        "Nombre",
        "Apellido",
        "Activo",
    }),
    expected_columns=frozenset(),
)


METADATA_SCHEMA = SheetSchema(
    sheet_name="Metadata",
    critical_columns=frozenset({
        "ID",
        "Timestamp",
        "Evento_Tipo",
        "TAG_SPOOL",
        "Worker_ID",
        "Worker_Nombre",
        "Operacion",
        "Accion",
        "Fecha_Operacion",
        "Metadata_JSON",
    }),
    expected_columns=frozenset({
        "N_UNION",
    }),
)


ALL_SCHEMAS: dict[str, SheetSchema] = {
    s.sheet_name: s for s in (
        OPERACIONES_SCHEMA,
        UNIONES_SCHEMA,
        TRABAJADORES_SCHEMA,
        METADATA_SCHEMA,
    )
}
