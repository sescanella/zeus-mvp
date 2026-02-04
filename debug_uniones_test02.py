"""Debug script to check Uniones sheet for TEST-02."""
import sys
sys.path.insert(0, '/Users/sescanella/Proyectos/KM/ZEUES-by-KM')

from backend.repositories.sheets_repository import SheetsRepository
from backend.repositories.union_repository import UnionRepository
from backend.core.column_map_cache import ColumnMapCache

try:
    # Initialize repositories
    sheets_repo = SheetsRepository()
    union_repo = UnionRepository(sheets_repo)

    print(f"\n📊 Uniones Sheet Analysis for TEST-02")
    print("=" * 80)

    # Read all data using read_worksheet
    all_rows = sheets_repo.read_worksheet("Uniones")

    if not all_rows:
        print("❌ Uniones sheet is completely empty!")
        sys.exit(0)

    # Header analysis
    headers = all_rows[0]
    print(f"\n✅ Headers ({len(headers)} columns):")
    for i, h in enumerate(headers):
        print(f"  {i}: {h}")

    # Get column mapping
    column_map = ColumnMapCache.get_or_build("Uniones", sheets_repo)

    def normalize(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "")

    # Find TAG_SPOOL column
    tag_col_key = normalize("TAG_SPOOL")
    if tag_col_key not in column_map:
        print("\n❌ TAG_SPOOL column not found in column map!")
        print(f"Available columns: {list(column_map.keys())}")
        sys.exit(0)

    tag_col_idx = column_map[tag_col_key]
    print(f"\n✅ TAG_SPOOL found at index {tag_col_idx}")

    # Filter TEST-02 rows
    test02_rows = []
    for row_idx, row in enumerate(all_rows[1:], start=2):
        if len(row) > tag_col_idx and row[tag_col_idx] == "TEST-02":
            test02_rows.append((row_idx, row))

    print(f"\n📌 Found {len(test02_rows)} unions for TEST-02:")
    print("=" * 80)

    if not test02_rows:
        print("❌ NO UNIONS FOUND FOR TEST-02!")
        print("\nAll TAG_SPOOL values in sheet:")
        tag_values = set()
        for row in all_rows[1:]:
            if len(row) > tag_col_idx:
                val = row[tag_col_idx]
                if val:
                    tag_values.add(val)
        print(f"Total unique TAG_SPOOL values: {len(tag_values)}")
        for val in sorted(tag_values)[:10]:  # Show first 10
            print(f"  - {val}")
        if len(tag_values) > 10:
            print(f"  ... and {len(tag_values) - 10} more")
    else:
        # Find key columns
        arm_fin_col_key = None
        for key in column_map.keys():
            if "arm" in key and ("fechafin" in key or "fin" in key):
                arm_fin_col_key = key
                break

        arm_fin_col_idx = column_map.get(arm_fin_col_key) if arm_fin_col_key else None
        print(f"ARM_FECHA_FIN column at index: {arm_fin_col_idx}")

        # Find other key columns
        id_col_idx = column_map.get(normalize("ID"))
        n_union_col_idx = column_map.get(normalize("N_UNION"))
        dn_col_idx = column_map.get(normalize("DN_UNION"))
        ot_col_idx = column_map.get(normalize("OT"))

        print(f"ID column: {id_col_idx}, N_UNION: {n_union_col_idx}, DN_UNION: {dn_col_idx}, OT: {ot_col_idx}")
        print()

        for row_num, row in test02_rows:
            # Extract key fields
            id_val = row[id_col_idx] if id_col_idx and len(row) > id_col_idx else ""
            ot_val = row[ot_col_idx] if ot_col_idx and len(row) > ot_col_idx else ""
            n_union = row[n_union_col_idx] if n_union_col_idx and len(row) > n_union_col_idx else ""
            dn_union = row[dn_col_idx] if dn_col_idx and len(row) > dn_col_idx else ""
            arm_fecha_fin = row[arm_fin_col_idx] if arm_fin_col_idx and len(row) > arm_fin_col_idx else ""

            status = "✅ DISPONIBLE" if not arm_fecha_fin or not str(arm_fecha_fin).strip() else "❌ COMPLETADO"

            print(f"  Row {row_num}: ID={id_val}, OT={ot_val}, N_UNION={n_union}, DN={dn_union}, ARM_FIN='{arm_fecha_fin}' {status}")

        # Count disponibles
        disponibles = 0
        for _, row in test02_rows:
            arm_fecha_fin = row[arm_fin_col_idx] if arm_fin_col_idx and len(row) > arm_fin_col_idx else ""
            if not arm_fecha_fin or not str(arm_fecha_fin).strip():
                disponibles += 1

        print(f"\n📊 Summary: {disponibles} disponibles out of {len(test02_rows)} total unions")

        # Now test the repository methods
        print(f"\n\n🔍 Testing UnionRepository methods:")
        print("=" * 80)

        # Get spool to extract OT
        spool = sheets_repo.get_spool_by_tag("TEST-02")
        if spool:
            print(f"✅ Spool found: TAG={spool.tag_spool}, OT={spool.ot}")

            # Test get_by_ot
            unions_by_ot = union_repo.get_by_ot(spool.ot)
            print(f"✅ union_repo.get_by_ot('{spool.ot}'): {len(unions_by_ot)} unions")

            # Test get_disponibles_arm_by_ot
            disponibles_arm = union_repo.get_disponibles_arm_by_ot(spool.ot)
            print(f"✅ union_repo.get_disponibles_arm_by_ot('{spool.ot}'): {len(disponibles_arm)} unions")

            if disponibles_arm:
                print("\nDisponibles ARM:")
                for u in disponibles_arm:
                    print(f"  - ID={u.id}, N_UNION={u.n_union}, DN={u.dn_union}, ARM_FIN={u.arm_fecha_fin}")
            else:
                print("\n❌ NO DISPONIBLES FOUND BY REPOSITORY METHOD!")
        else:
            print("❌ Spool TEST-02 not found in Operaciones sheet!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
