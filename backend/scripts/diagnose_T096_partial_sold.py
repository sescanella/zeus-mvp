#!/usr/bin/env python3
"""
T-096 — Diagnostic (READ-ONLY) for the B6 partial-SOLD metrología auto-trigger bug.

Scans the production Google Sheet and prints spools whose Operaciones row looks
corrupt in the same shape as the T-021 incident:

    Fecha_Soldadura is set, BUT the SOLD-required unions in the Uniones sheet
    are not all soldered (sol_fecha_fin missing on at least one).

For each suspect spool it prints the fields needed to distinguish the three
hypotheses from the 21-abr audit:

    - Total_Uniones                         (empty/0 => H1 candidate)
    - Uniones_SOLD_Completadas              (raw value from Operaciones)
    - Fecha_Soldadura, Fecha_QC_Metrologia  (downstream corruption markers)
    - Estado_Detalle                        (what Matias sees on the UI)
    - real SOLD-required count from Uniones (ground truth)
    - real sol_fecha_fin count              (ground truth)
    - per-OT Uniones count                  (decides v3.0 vs v4.0 FINALIZAR branch)

This script ONLY READS. It writes nothing to Sheets or Metadata. Safe to run
against production.

Usage:
    source venv/bin/activate
    PYTHONPATH="$(pwd)" python backend/scripts/diagnose_T096_partial_sold.py
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.union_repository import UnionRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.utils.normalize import normalize_column_name
from backend.config import config
from backend.services.occupation_service import SOLD_REQUIRED_TYPES


OP_COLS = [
    "TAG_SPOOL",
    "OT",
    "Total_Uniones",
    "Uniones_ARM_Completadas",
    "Uniones_SOLD_Completadas",
    "Pulgadas_ARM",
    "Pulgadas_SOLD",
    "Fecha_Armado",
    "Fecha_Soldadura",
    "Fecha_QC_Metrologia",
    "Estado_Detalle",
    "Ocupado_Por",
]


def _col_value(row: list, col_map: dict, col_name: str) -> str:
    idx = col_map.get(normalize_column_name(col_name))
    if idx is None:
        return "<COL_NOT_FOUND>"
    if idx >= len(row):
        return ""
    return row[idx]


def _is_empty(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _as_int(v) -> Optional[int]:
    if _is_empty(v):
        return None
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            return None


def main() -> int:
    config.validate()
    print(f"Sheet ID: {config.GOOGLE_SHEET_ID}")
    print(f"Operaciones: {config.HOJA_OPERACIONES_NOMBRE}\n")

    sheets_repo = SheetsRepository()
    union_repo = UnionRepository(sheets_repo=sheets_repo)

    all_rows = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
    if not all_rows or len(all_rows) < 2:
        print("Operaciones sheet empty or header-only.")
        return 1

    op_col_map = ColumnMapCache.get_or_build(
        config.HOJA_OPERACIONES_NOMBRE, sheets_repo
    )

    tag_idx = op_col_map.get(normalize_column_name("TAG_SPOOL"))
    fs_idx = op_col_map.get(normalize_column_name("Fecha_Soldadura"))
    ot_idx_op = op_col_map.get(normalize_column_name("OT"))
    if tag_idx is None or fs_idx is None or ot_idx_op is None:
        print("Missing TAG_SPOOL, OT, or Fecha_Soldadura column in Operaciones.")
        return 1

    # Preload the entire Uniones sheet once to count SOLD per spool + per OT.
    uni_rows = sheets_repo.read_worksheet("Uniones")
    uni_col_map = ColumnMapCache.get_or_build("Uniones", sheets_repo)
    uni_tag_idx = uni_col_map.get(normalize_column_name("TAG_SPOOL"))
    uni_ot_idx = uni_col_map.get(normalize_column_name("OT"))
    uni_tipo_idx = uni_col_map.get(normalize_column_name("TIPO_UNION"))
    uni_sol_fin_idx = uni_col_map.get(normalize_column_name("SOL_FECHA_FIN"))

    if None in (uni_tag_idx, uni_ot_idx, uni_tipo_idx, uni_sol_fin_idx):
        print("Missing key column(s) in Uniones sheet.")
        return 1

    # Build: tag_spool -> {total, sold_required, sold_done}
    # Build: ot -> count (raw, matches UnionRepository.get_total_uniones behaviour)
    per_spool: dict[str, dict] = {}
    per_ot_rowcount: dict[str, int] = {}
    for u_row in uni_rows[1:]:
        if not u_row or len(u_row) <= max(uni_tag_idx, uni_ot_idx):
            continue
        tag = u_row[uni_tag_idx] if uni_tag_idx < len(u_row) else ""
        ot = u_row[uni_ot_idx] if uni_ot_idx < len(u_row) else ""
        ot_key = str(ot).strip()
        if ot_key:
            per_ot_rowcount[ot_key] = per_ot_rowcount.get(ot_key, 0) + 1
        if not tag:
            continue
        tipo = (u_row[uni_tipo_idx] if uni_tipo_idx < len(u_row) else "").strip()
        sol_fin = u_row[uni_sol_fin_idx] if uni_sol_fin_idx < len(u_row) else ""
        bucket = per_spool.setdefault(
            tag, {"total": 0, "sold_required": 0, "sold_done": 0}
        )
        bucket["total"] += 1
        if tipo in SOLD_REQUIRED_TYPES:
            bucket["sold_required"] += 1
            if not _is_empty(sol_fin):
                bucket["sold_done"] += 1

    # Scan Operaciones and flag suspects.
    suspects: list[dict] = []
    total_with_fecha_sold = 0
    for row in all_rows[1:]:
        if not row or len(row) <= tag_idx:
            continue
        tag = row[tag_idx]
        if not tag:
            continue
        fecha_sold = row[fs_idx] if fs_idx < len(row) else ""
        if _is_empty(fecha_sold):
            continue
        total_with_fecha_sold += 1

        real = per_spool.get(tag, {"total": 0, "sold_required": 0, "sold_done": 0})
        ot_val = str(row[ot_idx_op]).strip() if ot_idx_op < len(row) else ""
        ot_rowcount = per_ot_rowcount.get(ot_val, 0)
        # Corruption pattern: Fecha_Soldadura written but SOLD-required not fully done.
        if real["sold_required"] > 0 and real["sold_done"] < real["sold_required"]:
            record = {c: _col_value(row, op_col_map, c) for c in OP_COLS}
            record["_real_total_uniones"] = real["total"]
            record["_real_sold_required"] = real["sold_required"]
            record["_real_sold_done"] = real["sold_done"]
            record["_ot_rowcount_uniones"] = ot_rowcount
            record["_branch_would_take"] = (
                "v3.0 (_finalizar_v30_spool, no guard)"
                if ot_rowcount == 0
                else "v4.0 (with T-021 guard)"
            )
            suspects.append(record)

    print(f"Rows in Operaciones with Fecha_Soldadura set: {total_with_fecha_sold}")
    print(f"Suspects (Fecha_Soldadura set but SOLD-required incomplete): {len(suspects)}\n")

    def _dump(label: str, items: list[dict], cap: int = 15) -> None:
        print(f"=== {label} (showing up to {cap}) ===")
        for i, r in enumerate(items[:cap], 1):
            print(f"\n[{i}] TAG_SPOOL={r['TAG_SPOOL']}  OT={r['OT']}")
            print(f"    Operaciones: Total_Uniones={r['Total_Uniones']!r}  "
                  f"ARM_done={r['Uniones_ARM_Completadas']!r}  "
                  f"SOLD_done={r['Uniones_SOLD_Completadas']!r}")
            print(f"    Fechas: Armado={r['Fecha_Armado']!r}  "
                  f"Soldadura={r['Fecha_Soldadura']!r}  "
                  f"QC_Met={r['Fecha_QC_Metrologia']!r}")
            print(f"    Estado_Detalle={r['Estado_Detalle']!r}  Ocupado_Por={r['Ocupado_Por']!r}")
            print(f"    Uniones (per-spool): total={r['_real_total_uniones']}  "
                  f"SOLD_required={r['_real_sold_required']}  "
                  f"SOLD_done={r['_real_sold_done']}")
            print(f"    Uniones (per-OT rowcount): {r['_ot_rowcount_uniones']}  "
                  f"→ finalizar branch: {r['_branch_would_take']}")
        if len(items) > cap:
            print(f"\n... {len(items) - cap} more")

    if suspects:
        _dump("SUSPECTS — Fecha_Soldadura set but SOLD-required incomplete", suspects)

    print("\nDone. This script only reads; nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
