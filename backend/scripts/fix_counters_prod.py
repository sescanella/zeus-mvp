#!/usr/bin/env python3
"""
Corrección puntual: recalcula los contadores de uniones en Operaciones (PROD)
desde la verdad autoritativa de la hoja Uniones.

Contexto (bug FINALIZAR 409 RACE_CONDITION):
    Algunos spools tienen `Uniones_ARM_Completadas` / `Uniones_SOLD_Completadas`
    desincronizados con la hoja Uniones (p.ej. contador=3 mientras ninguna unión
    tiene ARM_FECHA_FIN). Cuando el contador está POR ENCIMA de la realidad, el
    guard defensivo en `_determine_action` dispara un RaceConditionError falso y
    FINALIZAR devuelve HTTP 409.

    El fix de código (occupation_service.py rama ARM) ya neutraliza esto en el
    punto de decisión. Este script repara los datos YA corruptos para que los
    contadores en Operaciones reflejen la realidad de Uniones.

Qué hace:
    Para cada OT con uniones, recalcula desde Uniones:
        Uniones_ARM_Completadas  = #uniones con ARM_FECHA_FIN no vacío
        Uniones_SOLD_Completadas = #uniones con SOL_FECHA_FIN no vacío
        Pulgadas_ARM             = Σ DN_UNION de uniones ARM completas
        Pulgadas_SOLD            = Σ DN_UNION de uniones SOLD completas
    Compara con lo que dice Operaciones e imprime los mismatches. Solo escribe
    las filas que difieren, y SOLO tras confirmación explícita del operador.

    `Total_Uniones` NO se toca: está vacío para la mayoría de spools (cosmético)
    y no afecta la decisión PAUSAR/COMPLETAR. Limpiarlo es tarea aparte.

Uso:
    source venv/bin/activate
    python backend/scripts/fix_counters_prod.py            # dry-run (solo reporta)
    python backend/scripts/fix_counters_prod.py --apply    # escribe tras confirmar
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

OPER_TAB = "Operaciones"
UNIONES_TAB = "Uniones"

# Columnas de contadores a corregir en Operaciones.
COUNTER_COLS = [
    "Uniones_ARM_Completadas",
    "Uniones_SOLD_Completadas",
    "Pulgadas_ARM",
    "Pulgadas_SOLD",
]


def get_client() -> gspread.Client:
    creds_dict = config.get_credentials_dict()
    if not creds_dict:
        sys.exit(
            "ERROR: no se encontraron credenciales. Configura .env.local "
            "(GOOGLE_PRIVATE_KEY + GOOGLE_SERVICE_ACCOUNT_EMAIL) o el JSON local."
        )
    creds = Credentials.from_service_account_info(creds_dict, scopes=config.get_scopes())
    return gspread.authorize(creds)


def norm(value) -> str:
    return str(value).strip()


def to_int(value) -> int:
    try:
        return int(float(norm(value)))
    except (ValueError, TypeError):
        return 0


def to_float(value) -> float:
    try:
        return float(norm(value))
    except (ValueError, TypeError):
        return 0.0


def col_letter(idx_0based: int) -> str:
    """0-based column index -> letra de hoja (A, B, ..., Z, AA, ...)."""
    result = ""
    idx = idx_0based
    while idx >= 0:
        result = chr(ord("A") + idx % 26) + result
        idx = idx // 26 - 1
    return result


def compute_real_metrics(uniones_records: list[dict]) -> dict[str, dict]:
    """Agrega métricas reales por OT desde las filas de Uniones."""
    by_ot: dict[str, dict] = defaultdict(
        lambda: {
            "arm_completadas": 0,
            "sold_completadas": 0,
            "pulgadas_arm": 0.0,
            "pulgadas_sold": 0.0,
        }
    )
    for r in uniones_records:
        ot = norm(r.get("OT", ""))
        if not ot:
            continue
        # Touch the OT so it's registered even with ZERO completions — these
        # are precisely the spools whose counter is corrupt-high (e.g. =3 while
        # no union has ARM_FECHA_FIN) and must be reset to 0.
        _ = by_ot[ot]
        dn = to_float(r.get("DN_UNION", 0))
        if norm(r.get("ARM_FECHA_FIN", "")):
            by_ot[ot]["arm_completadas"] += 1
            by_ot[ot]["pulgadas_arm"] += dn
        if norm(r.get("SOL_FECHA_FIN", "")):
            by_ot[ot]["sold_completadas"] += 1
            by_ot[ot]["pulgadas_sold"] += dn
    # redondear pulgadas a 2 decimales (igual que calculate_metrics)
    for ot in by_ot:
        by_ot[ot]["pulgadas_arm"] = round(by_ot[ot]["pulgadas_arm"], 2)
        by_ot[ot]["pulgadas_sold"] = round(by_ot[ot]["pulgadas_sold"], 2)
    return by_ot


def main() -> None:
    apply = "--apply" in sys.argv

    client = get_client()
    ss = client.open_by_key(PROD_SHEET_ID)

    oper_ws = ss.worksheet(OPER_TAB)
    uni_ws = ss.worksheet(UNIONES_TAB)

    # Leer con UNFORMATTED_VALUE: algunas celdas de contadores tienen formato
    # de FECHA aplicado, por lo que la lectura formateada devuelve "1900-01-03"
    # en vez del entero 4 → falsos mismatches. El backend (sheets_repository)
    # también lee UNFORMATTED, así que esta es la verdad que ve la app.
    unformatted = gspread.utils.ValueRenderOption.unformatted
    oper_values = oper_ws.get_values(value_render_option=unformatted)
    oper_header = oper_values[0]
    oper_rows = oper_values[1:]

    # Índices de columnas en Operaciones (0-based).
    def oidx(name: str):
        return oper_header.index(name) if name in oper_header else None

    ot_idx = oidx("OT")
    tag_idx = oidx("TAG") if "TAG" in oper_header else oidx("TAG_SPOOL")
    counter_idx = {c: oidx(c) for c in COUNTER_COLS}

    missing = [c for c, i in counter_idx.items() if i is None]
    if ot_idx is None or missing:
        sys.exit(
            f"ERROR: faltan columnas en Operaciones. OT={ot_idx}, "
            f"contadores faltantes={missing}"
        )

    # Uniones también unformatted, por consistencia con el backend.
    uni_values = uni_ws.get_values(value_render_option=unformatted)
    uni_header = uni_values[0]
    uni_records = [dict(zip(uni_header, r)) for r in uni_values[1:]]
    real = compute_real_metrics(uni_records)

    # Detectar mismatches y construir batch.
    batch_updates = []
    mismatches = []
    for row_offset, row in enumerate(oper_rows):
        sheet_row = row_offset + 2  # 1-based + header
        ot = norm(row[ot_idx]) if ot_idx < len(row) else ""
        if not ot or ot not in real:
            continue
        tag = norm(row[tag_idx]) if tag_idx is not None and tag_idx < len(row) else ""

        cur = {
            "Uniones_ARM_Completadas": to_int(row[counter_idx["Uniones_ARM_Completadas"]]) if counter_idx["Uniones_ARM_Completadas"] < len(row) else 0,
            "Uniones_SOLD_Completadas": to_int(row[counter_idx["Uniones_SOLD_Completadas"]]) if counter_idx["Uniones_SOLD_Completadas"] < len(row) else 0,
            "Pulgadas_ARM": to_float(row[counter_idx["Pulgadas_ARM"]]) if counter_idx["Pulgadas_ARM"] < len(row) else 0.0,
            "Pulgadas_SOLD": to_float(row[counter_idx["Pulgadas_SOLD"]]) if counter_idx["Pulgadas_SOLD"] < len(row) else 0.0,
        }
        want = {
            "Uniones_ARM_Completadas": real[ot]["arm_completadas"],
            "Uniones_SOLD_Completadas": real[ot]["sold_completadas"],
            "Pulgadas_ARM": real[ot]["pulgadas_arm"],
            "Pulgadas_SOLD": real[ot]["pulgadas_sold"],
        }

        diff_cols = [c for c in COUNTER_COLS if cur[c] != want[c]]
        if not diff_cols:
            continue

        mismatches.append((ot, tag, {c: (cur[c], want[c]) for c in diff_cols}))
        for c in diff_cols:
            letter = col_letter(counter_idx[c])
            batch_updates.append({"range": f"{letter}{sheet_row}", "values": [[want[c]]]})

    # Reporte.
    print("=" * 78)
    print("CORRECCIÓN DE CONTADORES — Operaciones vs Uniones (PROD)")
    print("=" * 78)
    if not mismatches:
        print("\n✅ No hay mismatches. Nada que corregir.")
        return

    print(f"\n{len(mismatches)} spool(s) con contadores desincronizados:\n")
    for ot, tag, diffs in mismatches:
        print(f"  OT={ot}  TAG={tag}")
        for c, (cur_v, want_v) in diffs.items():
            print(f"      {c}: {cur_v}  ->  {want_v}")
    print(f"\nTotal de celdas a escribir: {len(batch_updates)}")

    if not apply:
        print("\n[DRY-RUN] No se escribió nada. Re-ejecuta con --apply para corregir.")
        return

    confirm = input(
        f"\n⚠️  Vas a ESCRIBIR en PRODUCCIÓN ({len(batch_updates)} celdas). "
        f"Escribe 'SI' para confirmar: "
    )
    if confirm.strip() != "SI":
        print("Cancelado. No se escribió nada.")
        return

    oper_ws.batch_update(batch_updates, value_input_option="RAW")
    print(f"\n✅ Listo. {len(batch_updates)} celdas actualizadas en {len(mismatches)} spool(s).")
    print("   Re-ejecuta el script (sin --apply) para verificar 0 mismatches.")


if __name__ == "__main__":
    main()
