"""
Mock Uniones data fixture for integration testing.

Provides realistic mock data for 100 unions across 10 different OTs.
"""
from datetime import datetime, timedelta
from typing import Optional
import uuid


def _chile_timestamp(days_ago: int = 0, hours_ago: int = 0) -> str:
    """Generate Chile timezone timestamp in Sheets format (DD-MM-YYYY HH:MM:SS)."""
    dt = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
    return dt.strftime("%d-%m-%Y %H:%M:%S")


def generate_mock_uniones(num_ots: int = 10, unions_per_ot: int = 10) -> list[list]:
    """
    Generate mock Uniones sheet data with realistic values.

    Args:
        num_ots: Number of different OTs to generate (default: 10)
        unions_per_ot: Number of unions per OT (default: 10)

    Returns:
        list[list]: Mock sheet rows including header row
    """
    # Header row (17 columns - v4.0 simplified structure without audit fields)
    headers = [
        "ID",              # A: Composite PK
        "OT",              # B: Foreign key to Operaciones.OT
        "N_UNION",         # C: Union number (1-20)
        "TAG_SPOOL",       # D: TAG_SPOOL identifier
        "DN_UNION",        # E: Diameter in inches
        "TIPO_UNION",      # F: Union type
        "ARM_FECHA_INICIO", # G: ARM start timestamp
        "ARM_FECHA_FIN",   # H: ARM end timestamp
        "ARM_WORKER",      # I: ARM worker (INICIALES(ID))
        "SOL_FECHA_INICIO", # J: SOLD start timestamp
        "SOL_FECHA_FIN",   # K: SOLD end timestamp
        "SOL_WORKER",      # L: SOLD worker
        "NDT_UNION",       # M: NDT union identifier
        "R_NDT_UNION",     # N: NDT repair union
        "NDT_FECHA",       # O: NDT inspection date
        "NDT_STATUS",      # P: NDT result
        "version",         # Q: UUID4 for optimistic locking
    ]

    rows = [headers]

    # Realistic DN_UNION values (inches)
    dn_values = [4.5, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 24.0]

    # Union types
    tipos = ["Brida", "Socket", "Acople", "Codo", "Tee"]

    # Workers
    workers = [
        "MR(93)", "JP(94)", "MG(95)", "CP(96)", "AL(97)",
        "JT(98)", "RG(99)", "LM(100)", "PA(101)", "DF(102)"
    ]

    for ot_idx in range(1, num_ots + 1):
        ot = f"{ot_idx:03d}"  # Format: "001", "002", etc.
        # Use OT-001 for first OT so integration tests (OT-001) find unions
        tag_spool = f"OT-{ot}" if ot_idx == 1 else f"MK-1335-CW-25238-{ot_idx:03d}"

        for n_union in range(1, unions_per_ot + 1):
            union_id = f"{ot}+{n_union}"
            dn_union = dn_values[n_union % len(dn_values)]
            tipo = tipos[n_union % len(tipos)]
            creator = workers[ot_idx % len(workers)]

            # Completion states:
            # - First 7 unions: ARM complete
            # - First 5 unions: SOLD complete (requires ARM complete)
            # - Last 3 unions: Pending

            arm_fecha_inicio = None
            arm_fecha_fin = None
            arm_worker = None
            sol_fecha_inicio = None
            sol_fecha_fin = None
            sol_worker = None
            ndt_fecha = None
            ndt_status = None

            if n_union <= 7:
                # ARM complete
                arm_fecha_inicio = _chile_timestamp(days_ago=5, hours_ago=n_union)
                arm_fecha_fin = _chile_timestamp(days_ago=5, hours_ago=n_union-1)
                arm_worker = workers[(ot_idx + n_union) % len(workers)]

                if n_union <= 5:
                    # SOLD complete
                    sol_fecha_inicio = _chile_timestamp(days_ago=3, hours_ago=n_union)
                    sol_fecha_fin = _chile_timestamp(days_ago=3, hours_ago=n_union-1)
                    sol_worker = workers[(ot_idx + n_union + 1) % len(workers)]

                    # NDT for completed SOLD
                    if n_union <= 4:
                        ndt_fecha = _chile_timestamp(days_ago=1)
                        ndt_status = "APROBADO" if n_union % 2 == 0 else "RECHAZADO"

            row = [
                union_id,                           # ID
                ot,                                 # OT
                str(n_union),                       # N_UNION
                tag_spool,                          # TAG_SPOOL
                str(dn_union),                      # DN_UNION
                tipo,                               # TIPO_UNION
                arm_fecha_inicio or "",             # ARM_FECHA_INICIO
                arm_fecha_fin or "",                # ARM_FECHA_FIN
                arm_worker or "",                   # ARM_WORKER
                sol_fecha_inicio or "",             # SOL_FECHA_INICIO
                sol_fecha_fin or "",                # SOL_FECHA_FIN
                sol_worker or "",                   # SOL_WORKER
                "",                                 # NDT_UNION
                "",                                 # R_NDT_UNION
                ndt_fecha or "",                    # NDT_FECHA
                ndt_status or "",                   # NDT_STATUS
                str(uuid.uuid4()),                  # version
            ]

            rows.append(row)

    return rows


def get_by_state(state: str) -> list[list]:
    """
    Filter mock data by completion state.

    Args:
        state: "arm_complete", "sold_complete", or "pending"

    Returns:
        list[list]: Filtered mock rows (excluding header)
    """
    all_rows = generate_mock_uniones()
    header = all_rows[0]
    data_rows = all_rows[1:]

    # Column indices (updated for 17-column structure)
    arm_fecha_fin_idx = 7
    sol_fecha_fin_idx = 10

    filtered = []
    for row in data_rows:
        if state == "arm_complete":
            if row[arm_fecha_fin_idx]:  # Has ARM_FECHA_FIN
                filtered.append(row)
        elif state == "sold_complete":
            if row[sol_fecha_fin_idx]:  # Has SOL_FECHA_FIN
                filtered.append(row)
        elif state == "pending":
            if not row[arm_fecha_fin_idx]:  # No ARM_FECHA_FIN
                filtered.append(row)

    return filtered


def get_by_ot(ot: str) -> list[list]:
    """
    Filter mock data by OT.

    Args:
        ot: OT number (e.g., "001", "002")

    Returns:
        list[list]: Filtered mock rows for the OT (excluding header)
    """
    all_rows = generate_mock_uniones()
    header = all_rows[0]
    data_rows = all_rows[1:]

    # Column index for OT (Column B, index 1)
    ot_idx = 1

    filtered = [row for row in data_rows if row[ot_idx] == ot]
    return filtered


def get_disponibles(operacion: str = "ARM") -> list[list]:
    """
    Get disponibles unions for a given operation.

    Args:
        operacion: "ARM" or "SOLD"

    Returns:
        list[list]: Filtered mock rows (excluding header)
    """
    all_rows = generate_mock_uniones()
    header = all_rows[0]
    data_rows = all_rows[1:]

    # Column indices (updated for 17-column structure)
    arm_fecha_fin_idx = 7
    sol_fecha_fin_idx = 10

    filtered = []
    for row in data_rows:
        if operacion == "ARM":
            # ARM disponible: no ARM_FECHA_FIN
            if not row[arm_fecha_fin_idx]:
                filtered.append(row)
        elif operacion == "SOLD":
            # SOLD disponible: ARM complete but no SOL_FECHA_FIN
            if row[arm_fecha_fin_idx] and not row[sol_fecha_fin_idx]:
                filtered.append(row)

    return filtered


def get_header() -> list[str]:
    """Get the header row."""
    return generate_mock_uniones()[0]


def get_all_data() -> list[list]:
    """Get all mock data including header."""
    return generate_mock_uniones()


# Pre-generate standard dataset for fast access
STANDARD_MOCK_DATA = generate_mock_uniones(num_ots=10, unions_per_ot=10)


def get_standard_data() -> list[list]:
    """
    Get standard mock dataset (100 unions across 10 OTs).

    Fast access - pre-generated and cached.
    """
    return STANDARD_MOCK_DATA


def alias_by_spool_to_by_ot(repo) -> None:
    """
    Make a MagicMock UnionRepository's TAG_SPOOL-keyed methods mirror the
    OT-keyed ones the tests already configure.

    The FINALIZAR/INICIAR flows now resolve unions by TAG_SPOOL (to survive
    the cross-sheet OT mismatch, audit 2026-06-05), but the existing test
    suite mocks the legacy `*_by_ot` / `calculate_metrics` / `get_total_uniones`
    methods. This binds the new `*_by_spool` methods as side_effects that defer
    to those mocks at call time, so any `.return_value` a test sets afterwards
    on the OT-keyed mock is reflected automatically — no per-test duplication.

    Call this AFTER the OT-keyed mocks are assigned on `repo`.
    """
    repo.get_disponibles_arm_by_spool.side_effect = (
        lambda _tag: repo.get_disponibles_arm_by_ot.return_value
    )
    repo.get_disponibles_sold_by_spool.side_effect = (
        lambda _tag: repo.get_disponibles_sold_by_ot.return_value
    )
    repo.get_total_uniones_by_spool.side_effect = (
        lambda _tag: repo.get_total_uniones.return_value
    )
    repo.calculate_metrics_by_spool.side_effect = (
        lambda _tag: repo.calculate_metrics.return_value
    )
    repo.count_completed_arm_by_spool.side_effect = (
        lambda _tag: repo.count_completed_arm.return_value
    )
    # get_by_spool mirrors get_by_ot ONLY when the test left it unconfigured.
    # A test that set an explicit return_value (list) or its own side_effect has
    # configured get_by_spool deliberately — don't clobber it.
    already_configured = (
        repo.get_by_spool.side_effect is not None
        or isinstance(repo.get_by_spool.return_value, (list, tuple))
    )
    if not already_configured:
        repo.get_by_spool.side_effect = lambda _tag: repo.get_by_ot.return_value
