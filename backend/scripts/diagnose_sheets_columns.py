#!/usr/bin/env python3
"""
Script para diagnosticar las columnas de Google Sheets y entender por qué la fórmula no funciona.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import config

def diagnose_sheets():
    """Diagnose column positions and sample data."""

    print("=" * 80)
    print("ZEUES - Google Sheets Column Diagnosis")
    print("=" * 80)

    repo = SheetsRepository()

    # 1. Check Operaciones sheet
    print("\n📊 OPERACIONES SHEET:")
    print("-" * 80)

    operaciones_data = repo.read_worksheet(config.HOJA_OPERACIONES_NOMBRE)

    if len(operaciones_data) > 0:
        headers = operaciones_data[0]
        print(f"Total columns: {len(headers)}")
        print("\nColumn positions:")

        # Find key columns
        for idx, header in enumerate(headers):
            col_letter = repo._index_to_column_letter(idx)
            if header in ["TAG_SPOOL", "SPLIT", "NV", "Total_Uniones", "version"]:
                print(f"  [{col_letter}] Column {idx + 1}: {header}")

        # Show first 3 data rows
        print("\nFirst 3 data rows (showing columns A-H and BM):")
        for i in range(1, min(4, len(operaciones_data))):
            row = operaciones_data[i]
            # Show first 8 columns
            row_preview = row[:8] if len(row) >= 8 else row
            # Show column 68 (Total_Uniones) if exists
            total_uniones = row[67] if len(row) > 67 else "N/A"
            print(f"  Row {i + 1}: {row_preview} ... Total_Uniones(BM)={total_uniones}")

    # 2. Check Uniones sheet
    print("\n\n🔗 UNIONES SHEET:")
    print("-" * 80)

    try:
        uniones_data = repo.read_worksheet("Uniones")

        if len(uniones_data) > 0:
            headers = uniones_data[0]
            print(f"Total columns: {len(headers)}")
            print("\nColumn positions:")

            # Find key columns
            for idx, header in enumerate(headers):
                col_letter = repo._index_to_column_letter(idx)
                if header in ["ID", "TAG_SPOOL", "N_UNION", "DN_UNION"]:
                    print(f"  [{col_letter}] Column {idx + 1}: {header}")

            # Show first 5 data rows
            print(f"\nFirst 5 data rows (total rows: {len(uniones_data) - 1}):")
            for i in range(1, min(6, len(uniones_data))):
                row = uniones_data[i]
                # Show first 5 columns
                row_preview = row[:5] if len(row) >= 5 else row
                print(f"  Row {i + 1}: {row_preview}")

            # Count unions per TAG_SPOOL
            print("\n📊 Union counts by TAG_SPOOL (top 10):")
            from collections import Counter
            tag_col_idx = headers.index("TAG_SPOOL") if "TAG_SPOOL" in headers else 1

            tags = [row[tag_col_idx] for row in uniones_data[1:] if len(row) > tag_col_idx and row[tag_col_idx]]
            tag_counts = Counter(tags)

            for tag, count in tag_counts.most_common(10):
                print(f"  {tag}: {count} unions")

            print(f"\nTotal unique spools with unions: {len(tag_counts)}")
            print(f"Total unions: {sum(tag_counts.values())}")
        else:
            print("⚠️  Uniones sheet is empty")

    except Exception as e:
        print(f"❌ Error reading Uniones sheet: {e}")

    # 3. Formula diagnosis
    print("\n\n🔍 FORMULA DIAGNOSIS:")
    print("-" * 80)

    # Check if TAG_SPOOL is in column G (index 6)
    tag_col_name = headers[6] if len(headers) > 6 else "N/A"
    print(f"Column G (index 6) contains: '{tag_col_name}'")

    if tag_col_name == "TAG_SPOOL" or tag_col_name == "SPLIT":
        print("✅ TAG_SPOOL is in column G - formula should work")
        print("\n📝 Recommended formula for column BM (Total_Uniones):")
        print("   =COUNTIF(Uniones!$B:$B,$G2)")
    else:
        # Find actual TAG_SPOOL column
        try:
            actual_idx = headers.index("TAG_SPOOL")
            actual_col = repo._index_to_column_letter(actual_idx)
            print(f"⚠️  TAG_SPOOL is actually in column {actual_col} (index {actual_idx})")
            print(f"\n📝 Corrected formula for column BM (Total_Uniones):")
            print(f"   =COUNTIF(Uniones!$B:$B,${actual_col}2)")
        except ValueError:
            print("❌ TAG_SPOOL column not found in Operaciones!")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    diagnose_sheets()
