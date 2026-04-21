#!/usr/bin/env python3
"""
T-021 — Remediate the two spools corrupted by the partial-COMPLETAR bug.

Target spools (verified against production Sheets 2026-04-13):
    MK-1923-TW-17422-004   — 7 uniones, only 2 SOLD, Fecha_Soldadura=10/4/2026
    MK-1923-TK-34058-001   — 7 uniones, only 3 SOLD, Fecha_Soldadura=9/4/2026

What this script does (per spool):
    1. Reads current row from Operaciones.
    2. Verifies preconditions:
         - Total_Uniones >= 1
         - Uniones_SOLD_Completadas < Total_Uniones
         - Fecha_Soldadura is NOT empty (the corruption marker)
       If not satisfied, SKIPS the spool with a warning (no action).
    3. Computes new Estado_Detalle = "SOLD parcial {done}/{total} (pausado)".
    4. Dry-run (default): prints the diff. No writes.
    5. With --apply: writes to Operaciones:
         Fecha_Soldadura  → ""
         Soldador         → ""
         Estado_Detalle   → "SOLD parcial {done}/{total} (pausado)"
       And logs a T021_REMEDIATION event to Metadata.

Usage:
    # Dry-run (default — review planned changes)
    python backend/scripts/remediate_T021_corrupt_spools.py

    # Apply changes
    python backend/scripts/remediate_T021_corrupt_spools.py --apply

IMPORTANT: Run only AFTER backend + frontend deploy of the T-021 fix is live.
Otherwise the frontend may still render stale "SOLD completado" green text
based on cached data.
"""
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.config import config
from backend.utils.date_formatter import now_chile, format_datetime_for_sheets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# Hardcoded list — script does NOT search for other corrupt spools.
TARGET_SPOOLS = [
    "MK-1923-TW-17422-004",
    "MK-1923-TK-34058-001",
]


def _get_cell_value(row: list, headers, col_name: str):
    try:
        idx = headers.index(col_name)
    except ValueError:
        return None
    return row[idx] if idx < len(row) else None


def inspect_spool(sheets_repo: SheetsRepository, tag_spool: str) -> Optional[dict]:
    """Read the Operaciones row for the given spool and extract relevant fields."""
    worksheet_data = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
    if not worksheet_data:
        logger.error(f"Operaciones sheet empty/unreadable for {tag_spool}")
        return None
    headers = worksheet_data[0]

    try:
        tag_idx = headers.index("TAG_SPOOL")
    except ValueError:
        logger.error("TAG_SPOOL column not found in Operaciones headers")
        return None

    for row_num, row in enumerate(worksheet_data[1:], start=2):
        if row_num <= 1 or tag_idx >= len(row):
            continue
        if row[tag_idx] == tag_spool:
            return {
                "row_num": row_num,
                "tag_spool": tag_spool,
                "total_uniones": _get_cell_value(row, headers, "Total_Uniones"),
                "uniones_sold": _get_cell_value(row, headers, "Uniones_SOLD_Completadas"),
                "fecha_soldadura": _get_cell_value(row, headers, "Fecha_Soldadura"),
                "soldador": _get_cell_value(row, headers, "Soldador"),
                "estado_detalle": _get_cell_value(row, headers, "Estado_Detalle"),
            }
    logger.warning(f"Spool {tag_spool} not found in Operaciones")
    return None


def _to_int(val) -> int:
    if val is None or val == "":
        return 0
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def build_remediation(snapshot: dict) -> Optional[dict]:
    """Check preconditions and return remediation dict, or None to skip."""
    total = _to_int(snapshot["total_uniones"])
    done = _to_int(snapshot["uniones_sold"])
    fecha = snapshot["fecha_soldadura"]

    if total < 1:
        logger.warning(f"SKIP {snapshot['tag_spool']}: Total_Uniones={total} (<1)")
        return None
    if done >= total:
        logger.warning(
            f"SKIP {snapshot['tag_spool']}: counters consistent ({done}/{total}) — "
            "not corrupt"
        )
        return None
    if not fecha:
        logger.warning(
            f"SKIP {snapshot['tag_spool']}: Fecha_Soldadura empty — "
            "not the T-021 corruption pattern"
        )
        return None

    new_estado = f"SOLD parcial {done}/{total} (pausado)"

    return {
        "tag_spool": snapshot["tag_spool"],
        "row_num": snapshot["row_num"],
        "previous": {
            "Fecha_Soldadura": fecha,
            "Soldador": snapshot["soldador"],
            "Estado_Detalle": snapshot["estado_detalle"],
        },
        "new": {
            "Fecha_Soldadura": "",
            "Soldador": "",
            "Estado_Detalle": new_estado,
        },
        "counters": {"sold_completadas": done, "total_uniones": total},
    }


def print_diff(remediation: dict) -> None:
    logger.info("─" * 72)
    logger.info(f"Spool: {remediation['tag_spool']} (row {remediation['row_num']})")
    logger.info(
        f"Counters: Uniones_SOLD_Completadas={remediation['counters']['sold_completadas']} / "
        f"Total_Uniones={remediation['counters']['total_uniones']}"
    )
    for col in ("Fecha_Soldadura", "Soldador", "Estado_Detalle"):
        prev = remediation["previous"][col] or "(empty)"
        new = remediation["new"][col] or "(empty)"
        logger.info(f"  {col:20s}: {prev!s:30s} →  {new!s}")


def apply_remediation(
    sheets_repo: SheetsRepository,
    metadata_repo: MetadataRepository,
    remediation: dict,
) -> None:
    tag = remediation["tag_spool"]
    row_num = remediation["row_num"]

    batch = [
        {"row": row_num, "column_name": col, "value": val}
        for col, val in remediation["new"].items()
    ]
    sheets_repo.batch_update_by_column_name(
        sheet_name=config.HOJA_OPERACIONES_NOMBRE,
        updates=batch,
    )
    logger.info(f"✅ Sheet updated for {tag}")

    log_remediation_event(metadata_repo, remediation)


def log_remediation_event(metadata_repo: MetadataRepository, remediation: dict) -> None:
    """Append a SYSTEM_REMEDIATION audit event for a remediated spool.
    Extracted so it can be called both during --apply and separately for
    retroactively logging past remediations (see --log-missing-events)."""
    tag = remediation["tag_spool"]
    try:
        import json
        metadata_repo.log_event(
            evento_tipo="SYSTEM_REMEDIATION",
            tag_spool=tag,
            worker_id=0,
            worker_nombre="SYSTEM_T021",
            operacion="SOLD",
            accion="REMEDIAR",
            metadata_json=json.dumps({
                "previous": remediation["previous"],
                "new": remediation["new"],
                "counters": remediation["counters"],
                "ticket": "T-021",
                "reason": "partial_sold_corruption",
                "remediated_at": format_datetime_for_sheets(now_chile()),
            }),
        )
        logger.info(f"✅ Metadata event logged for {tag}")
    except Exception as e:
        logger.error(f"Metadata logging failed for {tag}: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="T-021 remediation script")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes. Default is dry-run (preview only).",
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    logger.info(f"━━━ T-021 Remediation — mode: {mode} ━━━")
    logger.info(f"Target spools ({len(TARGET_SPOOLS)}):")
    for t in TARGET_SPOOLS:
        logger.info(f"  • {t}")

    sheets_repo = SheetsRepository()
    metadata_repo = MetadataRepository(sheets_repo=sheets_repo) if args.apply else None

    # Prime column map cache
    ColumnMapCache.get_or_build(config.HOJA_OPERACIONES_NOMBRE, sheets_repo)

    remediations = []
    for tag in TARGET_SPOOLS:
        snapshot = inspect_spool(sheets_repo, tag)
        if snapshot is None:
            continue
        rem = build_remediation(snapshot)
        if rem is None:
            continue
        remediations.append(rem)
        print_diff(rem)

    if not remediations:
        logger.info("Nothing to remediate (all targets skipped or not found).")
        return 0

    if not args.apply:
        logger.info("─" * 72)
        logger.info(f"DRY-RUN complete. {len(remediations)} spool(s) would be updated.")
        logger.info("Re-run with --apply to execute.")
        return 0

    logger.info("─" * 72)
    logger.info(f"APPLYING changes to {len(remediations)} spool(s)...")
    for rem in remediations:
        try:
            apply_remediation(sheets_repo, metadata_repo, rem)
        except Exception as e:
            logger.error(f"❌ Remediation failed for {rem['tag_spool']}: {e}", exc_info=True)
            return 1

    logger.info("─" * 72)
    logger.info("✅ T-021 remediation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
