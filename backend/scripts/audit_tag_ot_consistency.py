#!/usr/bin/env python3
"""
READ-ONLY audit: consistencia TAG_SPOOL <-> OT en el sheet de PRODUCCIÓN.

Lee las hojas Operaciones y Uniones del libro de producción de Kronos
(_Kronos_Registro_Piping R04) y reporta discrepancias en la relación
TAG_SPOOL <-> OT. NO escribe nada en el sheet.

Chequeos:
  1) Uniones    : TAG_SPOOL asociado a >1 OT distinta.
  2) Operaciones: TAG_SPOOL asociado a >1 OT distinta + filas con TAG/OT vacíos.
  3) Cross-sheet: OT del tag en Uniones != OT en Operaciones (+ huérfanos).

Uso:
    source venv/bin/activate
    python backend/scripts/audit_tag_ot_consistency.py
"""
import sys
from collections import defaultdict
from pathlib import Path

# Permitir importar `backend.*`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import gspread  # noqa: E402
from google.oauth2.service_account import Credentials  # noqa: E402

from backend.config import config  # noqa: E402

# ID del libro de PRODUCCIÓN (datos reales Kronos). NO se usa config.GOOGLE_SHEET_ID
# porque .env.local apunta al sheet de testing.
PROD_SHEET_ID = "17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ"

# Nombre real de la columna del tag de spool en cada hoja de PRODUCCIÓN.
# OJO: en Operaciones la columna se llama 'TAG' (NO 'TAG_SPOOL' como en el schema).
OPER_TAG_COL = "TAG"
UNIONES_TAG_COL = "TAG_SPOOL"


def get_tag(record: dict, sheet: str) -> str:
    col = OPER_TAG_COL if sheet == "oper" else UNIONES_TAG_COL
    return norm(record.get(col, ""))


def norm(value) -> str:
    """Normaliza una celda a string sin espacios alrededor."""
    return str(value).strip()


def get_client() -> gspread.Client:
    creds_dict = config.get_credentials_dict()
    if not creds_dict:
        sys.exit(
            "ERROR: no se encontraron credenciales. Configura .env.local "
            "(GOOGLE_PRIVATE_KEY + GOOGLE_SERVICE_ACCOUNT_EMAIL) o el JSON local."
        )
    creds = Credentials.from_service_account_info(creds_dict, scopes=config.get_scopes())
    return gspread.authorize(creds)


def load_records(spreadsheet, tab: str) -> list[dict]:
    ws = spreadsheet.worksheet(tab)
    return ws.get_all_records()


def hr(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def check_single_ot_per_tag(records: list[dict], sheet_label: str, sheet: str) -> int:
    """Chequeo 1/2: un TAG_SPOOL debe pertenecer a una sola OT dentro de la hoja."""
    # tag_norm -> {ot_norm: {"display_tag": str, "ots": {ot_display: count}}}
    by_tag: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    display_tag: dict[str, str] = {}
    empty_tag = 0
    empty_ot = 0

    for r in records:
        tag = get_tag(r, sheet)
        ot = norm(r.get("OT", ""))
        if not tag:
            empty_tag += 1
            continue
        if not ot:
            empty_ot += 1
        key = tag.upper()
        display_tag.setdefault(key, tag)
        by_tag[key][ot] += 1

    conflicts = {t: ots for t, ots in by_tag.items() if len(ots) > 1}

    hr(f"CHEQUEO — {sheet_label}: TAG_SPOOL con más de una OT")
    print(f"Filas con TAG_SPOOL vacío : {empty_tag}")
    print(f"Filas con OT vacío        : {empty_ot}")
    print(f"TAGs únicos               : {len(by_tag)}")
    print(f"TAGs en conflicto (>1 OT) : {len(conflicts)}")

    if conflicts:
        print()
        for key in sorted(conflicts):
            ots = conflicts[key]
            detalle = ", ".join(f"{ot or '(vacío)'} ×{n}" for ot, n in sorted(ots.items()))
            print(f"  ⚠️  {display_tag[key]:<28} → {detalle}")
    else:
        print("  ✅ Sin conflictos.")

    return len(conflicts)


def check_cross_sheet(oper: list[dict], uniones: list[dict]) -> int:
    """Chequeo 3: OT por TAG_SPOOL debe coincidir entre Operaciones y Uniones."""
    # Mapa de Operaciones: tag.upper() -> set de OTs (normalmente 1)
    oper_ot: dict[str, set[str]] = defaultdict(set)
    oper_display: dict[str, str] = {}
    for r in oper:
        tag = get_tag(r, "oper")
        ot = norm(r.get("OT", ""))
        if not tag:
            continue
        key = tag.upper()
        oper_display.setdefault(key, tag)
        if ot:
            oper_ot[key].add(ot)

    # Tags presentes en Uniones (con su OT registrada)
    uniones_tags: dict[str, set[str]] = defaultdict(set)
    uniones_display: dict[str, str] = {}
    for r in uniones:
        tag = get_tag(r, "uniones")
        ot = norm(r.get("OT", ""))
        if not tag:
            continue
        key = tag.upper()
        uniones_display.setdefault(key, tag)
        uniones_tags[key].add(ot)

    mismatches = []      # (tag, ot_oper, ot_uniones)
    orphans = []         # tag en Uniones sin spool en Operaciones
    case_diffs = []      # mismo tag/ot pero difiere en mayúsc/espacios

    for key, ots_u in uniones_tags.items():
        if key not in oper_ot and key not in oper_display:
            orphans.append(uniones_display[key])
            continue
        ots_o = oper_ot.get(key, set())
        # Comparar conjunto de OTs en Uniones vs OT(s) en Operaciones
        for ot_u in ots_u:
            if ot_u == "":
                continue
            if ot_u not in ots_o:
                # ¿es solo diferencia de formato (case/espacios)?
                if any(ot_u.upper() == o.upper() for o in ots_o):
                    case_diffs.append((uniones_display[key], sorted(ots_o), ot_u))
                else:
                    mismatches.append(
                        (uniones_display[key], ", ".join(sorted(ots_o)) or "(sin OT)", ot_u)
                    )

    # Spools en Operaciones sin ninguna fila en Uniones (informativo)
    sin_uniones = [oper_display[k] for k in oper_display if k not in uniones_tags]

    hr("CHEQUEO — Cross-sheet: OT del TAG_SPOOL (Operaciones vs Uniones)")
    print(f"TAGs en Operaciones                : {len(oper_display)}")
    print(f"TAGs en Uniones                    : {len(uniones_tags)}")
    print(f"OT mismatch (discrepancia real)    : {len(mismatches)}")
    print(f"Diferencias de formato (case/space): {len(case_diffs)}")
    print(f"Huérfanos en Uniones (sin spool)   : {len(orphans)}")
    print(f"Spools sin uniones (informativo)   : {len(sin_uniones)}")

    if mismatches:
        print("\n  ── OT MISMATCH ───────────────────────────────────────────")
        print(f"  {'TAG_SPOOL':<28} {'OT (Operaciones)':<20} {'OT (Uniones)'}")
        for tag, ot_o, ot_u in sorted(mismatches):
            print(f"  ⚠️  {tag:<25} {ot_o:<20} {ot_u}")

    if case_diffs:
        print("\n  ── DIFERENCIAS DE FORMATO (mismo valor, distinta forma) ──")
        for tag, ots_o, ot_u in sorted(case_diffs):
            print(f"  ℹ️  {tag:<25} Oper={ots_o}  Uniones='{ot_u}'")

    if orphans:
        print("\n  ── HUÉRFANOS EN UNIONES (tag sin spool en Operaciones) ───")
        for tag in sorted(orphans):
            print(f"  ⚠️  {tag}")

    if sin_uniones:
        print(f"\n  ── SPOOLS SIN UNIONES ({len(sin_uniones)}) — informativo ──")
        for tag in sorted(sin_uniones):
            print(f"  ·  {tag}")

    if not (mismatches or orphans):
        print("\n  ✅ Sin discrepancias de OT entre hojas.")

    return len(mismatches) + len(orphans)


def main() -> None:
    print("Conectando al sheet de PRODUCCIÓN…")
    client = get_client()
    sh = client.open_by_key(PROD_SHEET_ID)
    print(f"Spreadsheet: {sh.title}")

    oper = load_records(sh, config.HOJA_OPERACIONES_NOMBRE)
    uniones = load_records(sh, "Uniones")
    print(f"Filas leídas — Operaciones: {len(oper)} | Uniones: {len(uniones)}")

    total = 0
    total += check_single_ot_per_tag(uniones, "Uniones", "uniones")
    total += check_single_ot_per_tag(oper, "Operaciones", "oper")
    total += check_cross_sheet(oper, uniones)

    hr("RESUMEN")
    if total == 0:
        print("✅ No se detectaron discrepancias TAG_SPOOL ↔ OT.")
    else:
        print(f"⚠️  Se detectaron {total} discrepancia(s) que requieren revisión manual.")


if __name__ == "__main__":
    main()
