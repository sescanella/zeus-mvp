"""
T-136 Load test seeding — populates a staging Sheet with 200 synthetic spools.

USAGE:
    source venv/bin/activate
    python scripts/seed_load_test.py [--dry-run] [--yes]

SAFETY:
    - Hardcoded blocklist on PROD spreadsheet ID. Refuses to run if matched.
    - Refuses to run unless GOOGLE_SHEET_ID is set AND distinct from PROD.
    - Validates Sheet title contains "TEST" / "STAGING" before writing.
    - Validates schema (headers) on Operaciones/Uniones/Metadata before writing.
    - Wipes only Operaciones/Uniones/Metadata (rows 2..N). Never touches
      Trabajadores, Roles, FluorReporte, Param, Ponderaciones, NoConformidad.
    - Synthetic TAGs use OT="9999" — identifiable as load-test data at a glance.

OUTPUT:
    200 spools across 10 estados (LIBRE / EN_ARM / ARM_PEND / ARM_TERM /
    EN_SOLD / SOLD_PEND / SOLD_TERM / MET_PEND / RECHAZADO / EN_REPARACION),
    1-10 unions per spool, 8 hardcoded worker IDs from real Trabajadores.

DETERMINISM:
    random.seed(42). Same dataset every run.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import string
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# --- env loading ---
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env.local"
if not ENV_PATH.exists():
    print(f"FATAL: .env.local not found at {ENV_PATH}", file=sys.stderr)
    sys.exit(2)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ENV_PATH)

import gspread  # noqa: E402
from google.oauth2.service_account import Credentials  # noqa: E402

# ---------------------------------------------------------------------------
# Hard safety: PROD blocklist
# ---------------------------------------------------------------------------
PROD_SHEET_IDS = frozenset(
    {
        "17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ",  # current PROD
        "11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM",  # legacy v1.0
    }
)

# Required title fragment for staging — Sheet title must contain one of these
# (case-insensitive). Refuses to write if not matched.
STAGING_TITLE_MARKERS = ("TEST", "STAGING")


def assert_not_prod(sheet_id: str | None, title: str) -> None:
    if not sheet_id:
        print("FATAL: GOOGLE_SHEET_ID not set", file=sys.stderr)
        sys.exit(2)
    if sheet_id in PROD_SHEET_IDS:
        print(
            f"FATAL: GOOGLE_SHEET_ID={sheet_id} matches PROD blocklist. ABORT.",
            file=sys.stderr,
        )
        sys.exit(2)
    title_upper = title.upper()
    if not any(m in title_upper for m in STAGING_TITLE_MARKERS):
        print(
            f"FATAL: Sheet title '{title}' does not contain any of "
            f"{STAGING_TITLE_MARKERS}. Refusing to write to non-staging Sheet.",
            file=sys.stderr,
        )
        sys.exit(2)


# ---------------------------------------------------------------------------
# Schema — column order matches staging Sheet headers (verified 2026-04-29)
# ---------------------------------------------------------------------------
OPERACIONES_HEADERS = [
    "id", "NV", "OT", "CT", "ITEM", "SPLIT", "TAG_SPOOL", "STATUS_NV",
    "Status_Spool", "Ubicación", "Cliente", "OC", "Item_OC",
    "PLANO_KRONOS N°", "Rev.", "Plano_Referencia", "Marca_Placa", "Prioridad",
    "Notas", "Fecha_Compromiso", "Fecha_Estimada_Entrega", "DIAM",
    "PD_Soldadura", "PD_Ranurado", "PD_Hilo", "Peso_Kg", "Area_m2",
    "Tipo Armado", "Tipo_NDT", "Tipo_PH", "Tipo_Revestimiento", "Tipo_Pintura",
    "Tipo_Embalaje", "Fecha_Ingenieria", "Fecha_Materiales", "Fecha_Armado",
    "Armador", "Fecha_Soldadura", "Soldador", "Fecha_QC_Metrología",
    "Fecha_NDT", "OK NDT si/no/Rep", "N°_nforme_PT", "N°_Informe_UT_ RX",
    "Fecha_PH", "N°_Informe_PH", "Fecha_Revestimiento",
    "Fecha_QC_Revestimiento", "Fecha_Envio_Pintura", "GD_envio_Pintura",
    "Fecha_Pintura", "Taller_Pintura", "Informe_Pintura", "Fecha_QC_Pintura",
    "Fecha_Liberación", "N°_Acta_Libración", "Packing_list", "Fecha_GD",
    "Guia_Despacho", "Precio Fabricación", "Precio Revestimiento",
    "Precio Pintura", "Precio Embalaje", "Precio Total", "FLAG", "MatSys",
    "Ocupado_Por", "Fecha_Ocupacion", "version", "Estado_Detalle",
    "Total_Uniones", "Uniones_ARM_Completadas", "Uniones_SOLD_Completadas",
    "Pulgadas_ARM", "Pulgadas_SOLD",
]

UNIONES_HEADERS = [
    "ID", "OT", "N_UNION", "TAG_SPOOL", "DN_UNION", "TIPO_UNION",
    "ARM_FECHA_INICIO", "ARM_FECHA_FIN", "ARM_WORKER",
    "SOL_FECHA_INICIO", "SOL_FECHA_FIN", "SOL_WORKER",
    "NDT_UNION", "R_NDT_UNION", "NDT_FECHA", "NDT_STATUS", "version",
]

METADATA_HEADERS = [
    "id", "timestamp", "evento_tipo", "tag_spool", "worker_id",
    "worker_nombre", "operacion", "accion", "fecha_operacion",
    "metadata_json", "N_UNION",
]

# ---------------------------------------------------------------------------
# Worker pool — hardcoded from real Trabajadores sheet (2026-04-29 snapshot)
# Format used by the app: "INICIALES(ID)" (e.g. "MR(93)")
# ---------------------------------------------------------------------------
ARMADORES = [
    {"id": 93, "nombre": "Mauricio", "apellido": "Rodriguez", "iniciales": "MR"},
    {"id": 94, "nombre": "Nicolás",  "apellido": "Rodriguez", "iniciales": "NR"},
    {"id": 10, "nombre": "Nahuel",   "apellido": "Huiriqueo", "iniciales": "NH"},
]
SOLDADORES = [
    {"id": 11, "nombre": "Manuel",      "apellido": "Marchetti", "iniciales": "MM"},
    {"id": 12, "nombre": "Maximiliano", "apellido": "Liberona",  "iniciales": "ML"},
    {"id": 13, "nombre": "José",        "apellido": "Pozo",      "iniciales": "JP"},
]
METROLOGOS = [
    {"id": 129, "nombre": "Fernando", "apellido": "Figueroa", "iniciales": "FF"},
    {"id": 76,  "nombre": "Alexis",   "apellido": "Pinto",    "iniciales": "AP"},
]


def w_token(w: dict) -> str:
    return f"{w['iniciales']}({w['id']})"


def w_fullname(w: dict) -> str:
    return f"{w['nombre']} {w['apellido']}"


# ---------------------------------------------------------------------------
# Distribution
# ---------------------------------------------------------------------------
DISTRIBUTION = [
    ("LIBRE",          60),
    ("EN_ARM",         30),
    ("ARM_PEND",       20),
    ("ARM_TERM",       20),
    ("EN_SOLD",        30),
    ("SOLD_PEND",      10),
    ("SOLD_TERM",      10),
    ("MET_PEND",       10),
    ("RECHAZADO",       6),
    ("EN_REPARACION",   4),
]
TOTAL_SPOOLS = sum(n for _, n in DISTRIBUTION)
assert TOTAL_SPOOLS == 200, f"distribution sums to {TOTAL_SPOOLS}, not 200"

OT_VALUE = "9999"  # marker — distinguishes load-test rows from real ones
TIPOS_SOLDADURA = ["CW", "TW", "BW", "SW"]
TIPOS_UNION = ["BW", "SW", "TW"]
DN_OPTIONS = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
NV_POOL = [f"NV{1000 + i}" for i in range(10)]
CT_POOL = ["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# Date helpers (Chile timezone-aware via pytz, format DD-MM-YYYY)
# ---------------------------------------------------------------------------
import pytz  # noqa: E402

CHILE_TZ = pytz.timezone("America/Santiago")


def now_cl() -> datetime:
    return datetime.now(CHILE_TZ)


def fmt_date(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d-%m-%Y %H:%M:%S")


# ---------------------------------------------------------------------------
# Tag generation
# ---------------------------------------------------------------------------
def gen_tag(seq: int) -> str:
    """MK-9999-XX-NNNNN-NNN — same structure & length as real TAGs."""
    xx = random.choice(TIPOS_SOLDADURA)
    nnnnn = f"{random.randint(10000, 99999)}"
    nnn = f"{seq:03d}"
    return f"MK-9999-{xx}-{nnnnn}-{nnn}"


# ---------------------------------------------------------------------------
# Spool builder — returns (operaciones_row, [uniones_rows], [metadata_rows])
#
# State semantics derived from backend/models/spool_status.py _derive_estado:
#   LIBRE          → no Ocupado_Por, no fechas, no estado_detalle
#   EN_ARM         → Ocupado_Por=armador, no Fecha_Armado yet (arm_done=0)
#   ARM_PEND       → arm_done < total, soldadura no iniciada, NOT occupied
#                    (paused mid-arm: counters partial, fecha_armado empty)
#   ARM_TERM       → Fecha_Armado set, sold not done, no occupant
#   EN_SOLD        → Ocupado_Por=soldador, sold_done < total
#   SOLD_PEND      → sold_done < total, paused, no occupant
#   SOLD_TERM      → Fecha_Soldadura set, no occupant, met not done
#                    (also surfaces as PENDIENTE_METROLOGIA in derivation)
#   MET_PEND       → estado_detalle="PENDIENTE_METROLOGIA"
#   RECHAZADO      → estado_detalle="RECHAZADO (Ciclo X/3) - Pendiente reparación"
#   EN_REPARACION  → Ocupado_Por=worker, estado_detalle="EN_REPARACION (Ciclo X/3)"
# ---------------------------------------------------------------------------

# Reuse start counters across spools (so Uniones IDs are unique)
_union_id_counter = 1


def _next_union_id() -> int:
    global _union_id_counter
    val = _union_id_counter
    _union_id_counter += 1
    return val


_metadata_id_counter = 1


def _next_metadata_id() -> int:
    global _metadata_id_counter
    val = _metadata_id_counter
    _metadata_id_counter += 1
    return val


def build_spool(seq: int, estado: str) -> tuple[list, list[list], list[list]]:
    tag = gen_tag(seq)
    nv = random.choice(NV_POOL)
    ct = random.choice(CT_POOL)
    item = f"{random.randint(1, 999):03d}"
    split = "1"
    total_uniones = random.randint(1, 10)

    # Base date: between 30 and 90 days ago
    base_dt = now_cl() - timedelta(days=random.randint(30, 90))
    fecha_materiales = base_dt.date()

    # Initialize all op fields empty
    fecha_ing = fecha_materiales - timedelta(days=random.randint(7, 30))
    fecha_armado = ""
    fecha_soldadura = ""
    fecha_qc_met = ""
    armador_token = ""
    soldador_token = ""
    ocupado_por = ""
    fecha_ocupacion = ""
    estado_detalle = ""
    arm_done = 0
    sold_done = 0
    pulgadas_arm = 0.0
    pulgadas_sold = 0.0

    # Pre-pick workers for this spool
    armador = random.choice(ARMADORES)
    soldador = random.choice(SOLDADORES)
    metrologo = random.choice(METROLOGOS)
    reparador = armador  # repair worker is an armador in our pool

    # Generate union DN values up front so we can compute sums consistently
    union_dns = [random.choice(DN_OPTIONS) for _ in range(total_uniones)]

    # Build per-state shape for spool row
    if estado == "LIBRE":
        pass  # all empty

    elif estado == "EN_ARM":
        ocupado_por = w_token(armador)
        fecha_ocupacion = fmt_dt(now_cl() - timedelta(hours=random.randint(1, 8)))
        armador_token = w_token(armador)
        # mid-arm: some unions already done
        arm_done = random.randint(0, max(0, total_uniones - 1))
        pulgadas_arm = sum(union_dns[:arm_done])
        estado_detalle = f"EN_PROGRESO trabajando ARM"

    elif estado == "ARM_PEND":
        # paused mid-arm: counters partial but NOT occupied
        armador_token = w_token(armador)
        arm_done = random.randint(1, max(1, total_uniones - 1))
        pulgadas_arm = sum(union_dns[:arm_done])

    elif estado == "ARM_TERM":
        # ARM fully done, awaiting SOLD
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)

    elif estado == "EN_SOLD":
        # ARM done, soldering in progress
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)
        soldador_token = w_token(soldador)
        ocupado_por = w_token(soldador)
        fecha_ocupacion = fmt_dt(now_cl() - timedelta(hours=random.randint(1, 8)))
        sold_done = random.randint(0, max(0, total_uniones - 1))
        pulgadas_sold = sum(union_dns[:sold_done])
        estado_detalle = "EN_PROGRESO trabajando SOLD"

    elif estado == "SOLD_PEND":
        # SOLD partial, paused, NOT occupied
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)
        soldador_token = w_token(soldador)
        sold_done = random.randint(1, max(1, total_uniones - 1))
        pulgadas_sold = sum(union_dns[:sold_done])

    elif estado == "SOLD_TERM":
        # ARM + SOLD done, awaiting metrologia (no occupant)
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)
        soldador_token = w_token(soldador)
        fecha_soldadura = fmt_date(
            base_dt.date() + timedelta(days=random.randint(6, 15))
        )
        sold_done = total_uniones
        pulgadas_sold = sum(union_dns)

    elif estado == "MET_PEND":
        # Same as SOLD_TERM but with explicit estado_detalle marker
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)
        soldador_token = w_token(soldador)
        fecha_soldadura = fmt_date(
            base_dt.date() + timedelta(days=random.randint(6, 15))
        )
        sold_done = total_uniones
        pulgadas_sold = sum(union_dns)
        estado_detalle = "PENDIENTE_METROLOGIA"

    elif estado == "RECHAZADO":
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)
        soldador_token = w_token(soldador)
        fecha_soldadura = fmt_date(
            base_dt.date() + timedelta(days=random.randint(6, 15))
        )
        sold_done = total_uniones
        pulgadas_sold = sum(union_dns)
        ciclo = random.randint(1, 2)  # 1 or 2 — cycle 3 means BLOQUEADO
        estado_detalle = f"RECHAZADO (Ciclo {ciclo}/3) - Pendiente reparación"

    elif estado == "EN_REPARACION":
        armador_token = w_token(armador)
        fecha_armado = fmt_date(base_dt.date() + timedelta(days=random.randint(1, 5)))
        arm_done = total_uniones
        pulgadas_arm = sum(union_dns)
        soldador_token = w_token(soldador)
        fecha_soldadura = fmt_date(
            base_dt.date() + timedelta(days=random.randint(6, 15))
        )
        sold_done = total_uniones
        pulgadas_sold = sum(union_dns)
        ciclo = random.randint(1, 2)
        ocupado_por = w_token(reparador)
        fecha_ocupacion = fmt_dt(now_cl() - timedelta(hours=random.randint(1, 8)))
        estado_detalle = f"EN_REPARACION (Ciclo {ciclo}/3) - Ocupado: {ocupado_por}"

    else:
        raise ValueError(f"Unknown estado: {estado}")

    # Build Operaciones row in column order
    op_id = seq  # synthetic id — used as primary key in some downstream views
    diam = random.choice(DN_OPTIONS)
    pd_sold = random.uniform(1.0, 50.0)
    peso = random.uniform(5.0, 500.0)

    op_row: list = [""] * len(OPERACIONES_HEADERS)
    op_row[0] = op_id                                            # id
    op_row[1] = nv                                               # NV
    op_row[2] = OT_VALUE                                         # OT
    op_row[3] = ct                                               # CT
    op_row[4] = item                                             # ITEM
    op_row[5] = split                                            # SPLIT
    op_row[6] = tag                                              # TAG_SPOOL
    op_row[7] = "ACTIVA"                                         # STATUS_NV
    op_row[8] = "ACTIVO"                                         # Status_Spool
    op_row[9] = "Taller"                                         # Ubicación
    op_row[10] = "LOAD-TEST"                                     # Cliente
    op_row[21] = round(diam, 2)                                  # DIAM
    op_row[22] = round(pd_sold, 2)                               # PD_Soldadura
    op_row[25] = round(peso, 2)                                  # Peso_Kg
    op_row[33] = fmt_date(fecha_ing)                             # Fecha_Ingenieria
    op_row[34] = fmt_date(fecha_materiales)                      # Fecha_Materiales
    op_row[35] = fecha_armado                                    # Fecha_Armado
    op_row[36] = armador_token                                   # Armador
    op_row[37] = fecha_soldadura                                 # Fecha_Soldadura
    op_row[38] = soldador_token                                  # Soldador
    op_row[39] = fecha_qc_met                                    # Fecha_QC_Metrología
    op_row[66] = ocupado_por                                     # Ocupado_Por (col 67)
    op_row[67] = fecha_ocupacion                                 # Fecha_Ocupacion (col 68)
    op_row[68] = "v4.0"                                          # version (col 69)
    op_row[69] = estado_detalle                                  # Estado_Detalle (col 70)
    op_row[70] = total_uniones                                   # Total_Uniones (col 71)
    op_row[71] = arm_done                                        # Uniones_ARM_Completadas
    op_row[72] = sold_done                                       # Uniones_SOLD_Completadas
    op_row[73] = round(pulgadas_arm, 2)                          # Pulgadas_ARM
    op_row[74] = round(pulgadas_sold, 2)                         # Pulgadas_SOLD

    # Build Uniones rows
    union_rows: list[list] = []
    for n_union in range(1, total_uniones + 1):
        dn = union_dns[n_union - 1]
        tipo = random.choice(TIPOS_UNION)

        arm_inicio = ""
        arm_fin = ""
        arm_worker = ""
        sol_inicio = ""
        sol_fin = ""
        sol_worker = ""

        # Mark per-union ARM/SOLD progress consistent with spool counters
        is_arm_done = n_union <= arm_done
        is_sold_done = n_union <= sold_done

        if is_arm_done or estado in ("EN_ARM",) and n_union == arm_done + 1:
            # Done unions get full ARM range
            if is_arm_done:
                arm_inicio = fmt_dt(base_dt - timedelta(days=2))
                arm_fin = fmt_dt(base_dt - timedelta(days=1))
                arm_worker = armador_token

        if is_sold_done:
            sol_inicio = fmt_dt(base_dt + timedelta(days=5))
            sol_fin = fmt_dt(base_dt + timedelta(days=6))
            sol_worker = soldador_token

        u_row = [
            _next_union_id(),         # ID
            OT_VALUE,                 # OT
            n_union,                  # N_UNION
            tag,                      # TAG_SPOOL
            dn,                       # DN_UNION
            tipo,                     # TIPO_UNION
            arm_inicio,               # ARM_FECHA_INICIO
            arm_fin,                  # ARM_FECHA_FIN
            arm_worker,               # ARM_WORKER
            sol_inicio,               # SOL_FECHA_INICIO
            sol_fin,                  # SOL_FECHA_FIN
            sol_worker,               # SOL_WORKER
            "",                       # NDT_UNION
            "",                       # R_NDT_UNION
            "",                       # NDT_FECHA
            "",                       # NDT_STATUS
            "v4.0",                   # version
        ]
        union_rows.append(u_row)

    # Metadata rows: minimal — one synthetic SEED event per spool
    md_row = [
        _next_metadata_id(),                     # id
        fmt_dt(now_cl()),                        # timestamp
        "SEED_LOAD_TEST",                        # evento_tipo
        tag,                                     # tag_spool
        "",                                      # worker_id
        "",                                      # worker_nombre
        "",                                      # operacion
        "",                                      # accion
        "",                                      # fecha_operacion
        json.dumps({"estado_objetivo": estado, "seed": 42}),  # metadata_json
        "",                                      # N_UNION
    ]
    return op_row, union_rows, [md_row]


# ---------------------------------------------------------------------------
# Sheets I/O
# ---------------------------------------------------------------------------
def get_gspread_client() -> gspread.Client:
    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
    if not private_key:
        print("FATAL: GOOGLE_PRIVATE_KEY not set", file=sys.stderr)
        sys.exit(2)
    creds_dict = {
        "type": "service_account",
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
        "private_key": private_key,
        "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def validate_headers(ws: gspread.Worksheet, expected: list[str], name: str) -> None:
    actual = ws.row_values(1)
    if actual != expected:
        print(f"FATAL: {name} headers mismatch.", file=sys.stderr)
        print(f"  expected ({len(expected)}): {expected}", file=sys.stderr)
        print(f"  actual   ({len(actual)}): {actual}", file=sys.stderr)
        sys.exit(2)
    print(f"  ✓ {name} headers OK ({len(actual)} cols)")


def wipe_data_rows(ws: gspread.Worksheet, name: str) -> int:
    """Delete rows 2..end (keep header row 1). Returns rows deleted."""
    last_row = ws.row_count
    # row_count returns the sheet allocation, not the populated row count.
    # We need actual data extent — use len(get_all_values()).
    all_vals = ws.get_all_values()
    populated_rows = len(all_vals)
    if populated_rows <= 1:
        print(f"  ✓ {name}: already empty (no data rows to wipe)")
        return 0
    # Use batch_clear with explicit data range
    end_col = chr(ord("A") + ws.col_count - 1) if ws.col_count <= 26 else None
    if end_col:
        range_to_clear = f"A2:{end_col}{populated_rows}"
    else:
        # gspread A1 conversion for cols > 26
        from gspread.utils import rowcol_to_a1

        end = rowcol_to_a1(populated_rows, ws.col_count)
        range_to_clear = f"A2:{end}"
    ws.batch_clear([range_to_clear])
    deleted = populated_rows - 1
    print(f"  ✓ {name}: cleared {deleted} data rows (range {range_to_clear})")
    return deleted


def write_rows_at_a2(
    ws: gspread.Worksheet, rows: list[list], name: str, chunk_size: int = 500
) -> None:
    """
    Write rows starting at A2 using explicit range update.

    We avoid ws.append_rows() because it auto-detects the "data range"
    based on populated cells. After a wipe, if column A is fully empty
    the auto-detect can shift the insert range by +1 column, scrambling
    the entire dataset (observed empirically against staging on first run).

    Using ws.update(range, values) with an explicit A2:<endcol><endrow>
    range pins the write to the exact column 1 origin.
    """
    if not rows:
        print(f"  • {name}: no rows to write")
        return
    from gspread.utils import rowcol_to_a1

    n_cols = len(rows[0])
    total = len(rows)
    print(f"  • {name}: writing {total} rows × {n_cols} cols at A2 in chunks of {chunk_size}...")
    for i in range(0, total, chunk_size):
        chunk = rows[i : i + chunk_size]
        start_row = 2 + i
        end_row = start_row + len(chunk) - 1
        end_a1 = rowcol_to_a1(end_row, n_cols)
        cell_range = f"A{start_row}:{end_a1}"
        ws.update(cell_range, chunk, value_input_option="USER_ENTERED")
        print(f"    {i + len(chunk)}/{total} (range {cell_range})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Seed staging Sheet with 200 spools.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate dataset and validate, but do NOT write to Sheets.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    args = parser.parse_args()

    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    print("=" * 70)
    print("T-136 Load Test — Seed Staging Sheet")
    print("=" * 70)
    print(f"Sheet ID: {sheet_id}")
    print(f"Service account: {os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL')}")
    print(f"Mode: {'DRY-RUN (no writes)' if args.dry_run else 'LIVE WRITE'}")
    print()

    # Authenticate + open
    gc = get_gspread_client()
    sh = gc.open_by_key(sheet_id)
    print(f"Opened spreadsheet: {sh.title}")

    # Hard guards
    assert_not_prod(sheet_id, sh.title)
    print("  ✓ PROD blocklist check passed")
    print("  ✓ Title contains TEST/STAGING marker")
    print()

    # Schema validation
    print("Validating schema...")
    ws_op = sh.worksheet("Operaciones")
    ws_un = sh.worksheet("Uniones")
    ws_md = sh.worksheet("Metadata")
    validate_headers(ws_op, OPERACIONES_HEADERS, "Operaciones")
    validate_headers(ws_un, UNIONES_HEADERS, "Uniones")
    validate_headers(ws_md, METADATA_HEADERS, "Metadata")
    print()

    # Generate dataset (deterministic)
    random.seed(42)
    print("Generating synthetic dataset (seed=42)...")
    op_rows: list[list] = []
    union_rows: list[list] = []
    metadata_rows: list[list] = []

    seq = 1
    counts: dict[str, int] = {}
    for estado, n in DISTRIBUTION:
        for _ in range(n):
            op, unions, metas = build_spool(seq, estado)
            op_rows.append(op)
            union_rows.extend(unions)
            metadata_rows.extend(metas)
            counts[estado] = counts.get(estado, 0) + 1
            seq += 1

    print(f"  ✓ Generated {len(op_rows)} spools, {len(union_rows)} unions, "
          f"{len(metadata_rows)} metadata events")
    for estado, n in DISTRIBUTION:
        actual = counts.get(estado, 0)
        marker = "✓" if actual == n else "✗"
        print(f"    {marker} {estado:<16}: {actual:3d} (expected {n})")
    print()

    if args.dry_run:
        print("DRY-RUN: stopping before any writes. Sample rows:")
        print(f"  Operaciones[0]: {op_rows[0][:10]}...")
        print(f"  Uniones[0]:     {union_rows[0]}")
        print(f"  Metadata[0]:    {metadata_rows[0]}")
        return 0

    # Final confirmation
    if not args.yes:
        print(f"About to WIPE rows 2..N in: Operaciones, Uniones, Metadata")
        print(f"  (Trabajadores, Roles, FluorReporte, etc. will NOT be touched)")
        print(f"Then INSERT {len(op_rows)} spools + {len(union_rows)} unions "
              f"+ {len(metadata_rows)} metadata events.")
        ans = input("Proceed? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted by user.")
            return 1

    # Wipe + write
    print()
    print("Wiping target sheets...")
    wipe_data_rows(ws_op, "Operaciones")
    wipe_data_rows(ws_un, "Uniones")
    wipe_data_rows(ws_md, "Metadata")
    print()

    print("Writing synthetic dataset...")
    write_rows_at_a2(ws_op, op_rows, "Operaciones")
    write_rows_at_a2(ws_un, union_rows, "Uniones")
    write_rows_at_a2(ws_md, metadata_rows, "Metadata")
    print()

    print("=" * 70)
    print(f"DONE — staging Sheet now has {len(op_rows)} spools.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
