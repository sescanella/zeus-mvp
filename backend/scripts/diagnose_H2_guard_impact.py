#!/usr/bin/env python3
"""
H2 guard impact analysis (READ-ONLY).

Question we answer: if the H2 guard from PR #4 were active today,
how many spools that are currently operationally valid would be blocked
from entering metrología?

The PR #4 guard refuses metrología entry when any union bound to the
TAG_SPOOL has `arm_fecha_fin is None`, or when any SOLD-required union
has `sol_fecha_fin is None`. It intends to catch spools whose per-spool
dates (Fecha_Armado, Fecha_Soldadura) were written but whose per-union
state is incomplete.

But legacy v2.1/v3.0 spools were armed/soldered at the SPOOL level and
never touched per-union. Their union rows (if any exist) carry empty
date fields legitimately. If this guard blocks them, it is a regression.

For every spool in Operaciones this script prints:
  - is_legacy_v2_candidate  (Total_Uniones empty/0)
  - already_in_metrologia   (Fecha_QC_Metrologia set → already approved)
  - pending_metrologia      (ARM+SOLD dates set, QC_Met empty)
  - guard_would_trigger     (any union has arm_fecha_fin/sol_fecha_fin None
                              for SOLD-required types)
  - classification          (SAFE / REGRESSION_RISK / TARGETED_BY_FIX)

Classifications:
  - SAFE                — guard would NOT trigger. No change in behaviour.
  - TARGETED_BY_FIX     — guard WOULD trigger AND the spool looks
                           partially-processed (corrupt). The fix is
                           catching what it should catch.
  - REGRESSION_RISK     — guard WOULD trigger BUT the spool looks like
                           a legitimate legacy spool (Total_Uniones=0
                           or unions never tracked at all).

The counts at the end inform the redesign in Phase 2:
  - If REGRESSION_RISK == 0: guard is safe to keep as-is.
  - If REGRESSION_RISK is small: add legacy escape hatch.
  - If REGRESSION_RISK is large: restrict guard to v4.0 spools only.

This script ONLY READS. It writes nothing.

Usage:
    source venv/bin/activate
    PYTHONPATH="$(pwd)" python backend/scripts/diagnose_H2_guard_impact.py
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.core.column_map_cache import ColumnMapCache
from backend.utils.normalize import normalize_column_name
from backend.config import config
from backend.services.occupation_service import SOLD_REQUIRED_TYPES


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
    all_rows = sheets_repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)
    if not all_rows or len(all_rows) < 2:
        print("Operaciones sheet empty or header-only.")
        return 1

    op_col_map = ColumnMapCache.get_or_build(
        config.HOJA_OPERACIONES_NOMBRE, sheets_repo
    )

    def op_idx(col):
        return op_col_map.get(normalize_column_name(col))

    tag_idx = op_idx("TAG_SPOOL")
    ot_idx = op_idx("OT")
    fa_idx = op_idx("Fecha_Armado")
    fs_idx = op_idx("Fecha_Soldadura")
    fqc_idx = op_idx("Fecha_QC_Metrologia")
    tu_idx = op_idx("Total_Uniones")

    if None in (tag_idx, fa_idx, fs_idx, fqc_idx, tu_idx):
        print("Missing one of required columns in Operaciones.")
        return 1

    # Preload Uniones and bucket per TAG_SPOOL.
    uni_rows = sheets_repo.read_worksheet("Uniones")
    uni_col_map = ColumnMapCache.get_or_build("Uniones", sheets_repo)

    def uni_idx(col):
        return uni_col_map.get(normalize_column_name(col))

    u_tag = uni_idx("TAG_SPOOL")
    u_tipo = uni_idx("TIPO_UNION")
    u_arm_fin = uni_idx("ARM_FECHA_FIN")
    u_sol_fin = uni_idx("SOL_FECHA_FIN")

    if None in (u_tag, u_tipo, u_arm_fin, u_sol_fin):
        print("Missing one of required columns in Uniones.")
        return 1

    per_spool: dict[str, dict] = {}
    for row in uni_rows[1:]:
        if not row or len(row) <= u_tag:
            continue
        tag = row[u_tag]
        if not tag:
            continue
        tipo = (row[u_tipo] if u_tipo < len(row) else "").strip()
        arm_fin = row[u_arm_fin] if u_arm_fin < len(row) else ""
        sol_fin = row[u_sol_fin] if u_sol_fin < len(row) else ""
        bucket = per_spool.setdefault(
            tag,
            {
                "n_rows": 0,
                "arm_pending": 0,
                "sold_required_total": 0,
                "sold_required_pending": 0,
                "all_dates_empty": 0,
            },
        )
        bucket["n_rows"] += 1
        if _is_empty(arm_fin):
            bucket["arm_pending"] += 1
        if tipo in SOLD_REQUIRED_TYPES:
            bucket["sold_required_total"] += 1
            if _is_empty(sol_fin):
                bucket["sold_required_pending"] += 1
        if _is_empty(arm_fin) and _is_empty(sol_fin):
            bucket["all_dates_empty"] += 1

    # Classify every spool in Operaciones.
    counts = {
        "SAFE": 0,
        "TARGETED_BY_FIX": 0,
        "REGRESSION_RISK": 0,
    }
    regression_risk_samples: list[dict] = []
    targeted_samples: list[dict] = []
    per_bucket_examples: dict[str, list[str]] = {
        "legacy_already_approved": [],
        "legacy_pending_met": [],
        "v40_partial": [],
    }

    for row in all_rows[1:]:
        if not row or len(row) <= tag_idx:
            continue
        tag = row[tag_idx]
        if not tag:
            continue
        fa = row[fa_idx] if fa_idx < len(row) else ""
        fs = row[fs_idx] if fs_idx < len(row) else ""
        fqc = row[fqc_idx] if fqc_idx < len(row) else ""
        tu = _as_int(row[tu_idx] if tu_idx < len(row) else "")

        # Only care about spools that have passed or are at metrología.
        already_in_metrologia = not _is_empty(fqc)
        pending_metrologia = (
            not already_in_metrologia
            and not _is_empty(fa)
            and not _is_empty(fs)
        )
        if not (already_in_metrologia or pending_metrologia):
            continue

        unions = per_spool.get(tag, {
            "n_rows": 0,
            "arm_pending": 0,
            "sold_required_total": 0,
            "sold_required_pending": 0,
            "all_dates_empty": 0,
        })

        # Reproduce the PR #4 guard decision exactly.
        # As of round 2: SOLD-pending always triggers; ARM-pending triggers
        # only if at least one union has arm_fecha_fin set (per-unit tracked).
        # Legacy spools whose arm_fecha_fin is uniformly empty are exempt
        # from the ARM check.
        guard_triggers = False
        if unions["n_rows"] > 0:
            if unions["sold_required_pending"] > 0:
                guard_triggers = True
            any_arm_tracked = (
                unions["arm_pending"] < unions["n_rows"]
            )  # at least one union has arm_fecha_fin set
            if any_arm_tracked and unions["arm_pending"] > 0:
                guard_triggers = True

        if not guard_triggers:
            counts["SAFE"] += 1
            continue

        # Guard would block. Is it catching corruption or a legacy spool?
        is_legacy_candidate = (tu is None or tu == 0)

        # Spool is partial-processing (fix TARGET) if Total_Uniones is set AND
        # the unions tracked match (non-zero n_rows, non-zero sold_required_total)
        # but pending > 0. That's the T-096 corruption shape.
        looks_like_corrupt_v40 = (
            (tu is not None and tu > 0)
            and unions["sold_required_total"] > 0
            and unions["sold_required_pending"] > 0
        )

        # Legacy spools look different: Total_Uniones=0, or unions whose
        # dates are systematically empty (never tracked at unit level).
        looks_like_legacy = (
            is_legacy_candidate
            or (
                unions["n_rows"] > 0
                and unions["all_dates_empty"] == unions["n_rows"]
            )
        )

        record = {
            "TAG_SPOOL": tag,
            "OT": row[ot_idx] if ot_idx is not None and ot_idx < len(row) else "",
            "Total_Uniones": tu,
            "Fecha_Armado": fa,
            "Fecha_Soldadura": fs,
            "Fecha_QC_Metrologia": fqc,
            "uniones_rows": unions["n_rows"],
            "arm_pending": unions["arm_pending"],
            "sold_required_total": unions["sold_required_total"],
            "sold_required_pending": unions["sold_required_pending"],
            "all_dates_empty": unions["all_dates_empty"],
            "state": "already_in_met" if already_in_metrologia else "pending_met",
        }

        if looks_like_corrupt_v40:
            counts["TARGETED_BY_FIX"] += 1
            if len(targeted_samples) < 10:
                targeted_samples.append(record)
        elif looks_like_legacy:
            counts["REGRESSION_RISK"] += 1
            if len(regression_risk_samples) < 15:
                regression_risk_samples.append(record)
            # Break down by bucket for better understanding.
            if already_in_metrologia:
                if len(per_bucket_examples["legacy_already_approved"]) < 5:
                    per_bucket_examples["legacy_already_approved"].append(tag)
            else:
                if len(per_bucket_examples["legacy_pending_met"]) < 5:
                    per_bucket_examples["legacy_pending_met"].append(tag)
        else:
            # Ambiguous — mark as regression risk to be safe.
            counts["REGRESSION_RISK"] += 1
            if len(regression_risk_samples) < 15:
                record["notes"] = "AMBIGUOUS"
                regression_risk_samples.append(record)
            if len(per_bucket_examples["v40_partial"]) < 5:
                per_bucket_examples["v40_partial"].append(tag)

    print("=" * 70)
    print("H2 GUARD IMPACT SUMMARY")
    print("=" * 70)
    print(f"  SAFE                (guard would NOT trigger):       {counts['SAFE']}")
    print(f"  TARGETED_BY_FIX     (guard catches real corruption): {counts['TARGETED_BY_FIX']}")
    print(f"  REGRESSION_RISK     (guard blocks legitimate spool): {counts['REGRESSION_RISK']}")
    print()

    total_affected = counts["TARGETED_BY_FIX"] + counts["REGRESSION_RISK"]
    if total_affected == 0:
        print("✅ Guard would not affect any spool currently in metrología flow.")
    else:
        ratio = counts["REGRESSION_RISK"] / total_affected * 100
        print(f"Regression ratio: {counts['REGRESSION_RISK']}/{total_affected} "
              f"= {ratio:.1f}% of affected spools are false positives.")
    print()

    def _dump_samples(label, items):
        if not items:
            return
        print(f"\n=== {label} ({len(items)} shown) ===")
        for i, r in enumerate(items, 1):
            print(f"\n[{i}] TAG_SPOOL={r['TAG_SPOOL']}  OT={r['OT']}  state={r['state']}")
            print(f"    Operaciones: Total_Uniones={r['Total_Uniones']!r}  "
                  f"Fecha_Armado={r['Fecha_Armado']!r}  "
                  f"Fecha_Soldadura={r['Fecha_Soldadura']!r}  "
                  f"Fecha_QC_Metrologia={r['Fecha_QC_Metrologia']!r}")
            print(f"    Uniones: rows={r['uniones_rows']}  arm_pending={r['arm_pending']}  "
                  f"sold_req_total={r['sold_required_total']}  "
                  f"sold_req_pending={r['sold_required_pending']}  "
                  f"all_dates_empty={r['all_dates_empty']}")
            if "notes" in r:
                print(f"    NOTES: {r['notes']}")

    _dump_samples("TARGETED_BY_FIX samples", targeted_samples)
    _dump_samples("REGRESSION_RISK samples", regression_risk_samples)

    print("\n=== Buckets of REGRESSION_RISK (tag examples) ===")
    for bucket, tags in per_bucket_examples.items():
        if tags:
            print(f"  {bucket}: {tags}")

    print("\nDone. This script only reads; nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
