#!/usr/bin/env python3
"""
One-shot backfill for the two T-021 remediation events that could not be
logged on 2026-04-21 because EventoTipo.SYSTEM_REMEDIATION and Accion.REMEDIAR
did not yet exist in the enum. The data writes to Operaciones succeeded; only
the audit trail entry in Metadata was missing.

Run ONCE after merging the enum additions. Safe to skip entirely if Metadata
already contains the SYSTEM_REMEDIATION events for these spools.

Values below were captured from the live script output on 2026-04-21 at
15:51:55 -04:00 just before the Metadata call failed.

Usage:
    source venv/bin/activate
    PYTHONPATH="$(pwd)" python backend/scripts/backfill_T021_remediation_events.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.metadata_repository import MetadataRepository
from backend.utils.date_formatter import format_datetime_for_sheets, now_chile


REMEDIATIONS = [
    {
        "tag_spool": "MK-1923-TW-17422-004",
        "previous": {
            "Fecha_Soldadura": "21/4/2026",
            "Soldador": "DE(1001)",
            "Estado_Detalle": "ARM completado - Disponible",
        },
        "new": {
            "Fecha_Soldadura": "",
            "Soldador": "",
            "Estado_Detalle": "SOLD parcial 2/7 (pausado)",
        },
        "counters": {"sold_completadas": 2, "total_uniones": 7},
    },
    {
        "tag_spool": "MK-1923-TK-34058-001",
        "previous": {
            "Fecha_Soldadura": "9/4/2026",
            "Soldador": "FF(129)",
            "Estado_Detalle": "ARM completado - Disponible",
        },
        "new": {
            "Fecha_Soldadura": "",
            "Soldador": "",
            "Estado_Detalle": "SOLD parcial 3/7 (pausado)",
        },
        "counters": {"sold_completadas": 3, "total_uniones": 7},
    },
]


def main() -> int:
    print("━━━ Backfill of T-021 remediation events ━━━")
    sheets_repo = SheetsRepository()
    metadata_repo = MetadataRepository(sheets_repo=sheets_repo)

    for rem in REMEDIATIONS:
        tag = rem["tag_spool"]
        try:
            metadata_repo.log_event(
                evento_tipo="SYSTEM_REMEDIATION",
                tag_spool=tag,
                worker_id=0,
                worker_nombre="SYSTEM_T021",
                operacion="SOLD",
                accion="REMEDIAR",
                metadata_json=json.dumps({
                    "previous": rem["previous"],
                    "new": rem["new"],
                    "counters": rem["counters"],
                    "ticket": "T-021",
                    "reason": "partial_sold_corruption",
                    "remediated_at": "21-04-2026 15:51:55",
                    "backfilled_at": format_datetime_for_sheets(now_chile()),
                    "backfill_reason": (
                        "Original log_event call failed because "
                        "EventoTipo.SYSTEM_REMEDIATION / Accion.REMEDIAR "
                        "did not exist at the time of remediation."
                    ),
                }),
            )
            print(f"  ✅ Event logged for {tag}")
        except Exception as e:
            print(f"  ❌ Failed for {tag}: {e}")
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
