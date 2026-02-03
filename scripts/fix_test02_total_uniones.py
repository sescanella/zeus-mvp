#!/usr/bin/env python3
"""
Fix TEST-02 spool by populating Total_Uniones field in Google Sheets.

ROOT CAUSE: TEST-02 has Total_Uniones=None, causing v4.0 INICIAR endpoint to reject it as v3.0.
FIX: Set Total_Uniones=8 for TEST-02 to enable v4.0 workflow testing.

Debug session: .planning/debug/v4-endpoint-rejects-test02-as-v3.md
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.repositories.sheets_repository import SheetsRepository
from backend.config import Config
import gspread
from google.oauth2.service_account import Credentials


def main():
    """Populate Total_Uniones for TEST-02 spool."""

    print("=" * 60)
    print("FIX TEST-02 TOTAL_UNIONES")
    print("=" * 60)

    # Step 1: Verify current state
    print("\n[1] Checking current TEST-02 state...")
    repo = SheetsRepository()
    spool = repo.get_spool_by_tag('TEST-02')

    if not spool:
        print("ERROR: TEST-02 not found in Operaciones sheet")
        return 1

    print(f"  TAG_SPOOL: {spool.tag_spool}")
    print(f"  Current Total_Uniones: {spool.total_uniones}")
    print(f"  OT: {spool.ot}")
    print(f"  ARM: {spool.arm}")
    print(f"  SOLD: {spool.sold}")

    if spool.total_uniones is not None and spool.total_uniones > 0:
        print(f"\n✅ TEST-02 already has Total_Uniones={spool.total_uniones}")
        print("No fix needed.")
        return 0

    # Step 2: Connect to Google Sheets directly
    print("\n[2] Connecting to Google Sheets...")

    # Set up credentials using service account JSON
    import json
    creds_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'credenciales',
        'zeus-mvp-81282fb07109.json'
    )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(credentials)

    # Open spreadsheet
    spreadsheet = gc.open_by_key(Config.GOOGLE_SHEET_ID)
    operaciones_sheet = spreadsheet.worksheet(Config.HOJA_OPERACIONES_NOMBRE)

    print(f"  Connected to sheet: {Config.HOJA_OPERACIONES_NOMBRE}")

    # Step 3: Find TEST-02 row and Total_Uniones column
    print("\n[3] Finding TEST-02 row...")

    all_rows = operaciones_sheet.get_all_values()
    headers = all_rows[0]

    # Find column indices
    tag_col_idx = headers.index('TAG_SPOOL') if 'TAG_SPOOL' in headers else None
    total_uniones_col_idx = headers.index('Total_Uniones') if 'Total_Uniones' in headers else None

    if tag_col_idx is None:
        print("ERROR: TAG_SPOOL column not found")
        return 1

    if total_uniones_col_idx is None:
        print("ERROR: Total_Uniones column not found")
        return 1

    def col_num_to_letter(n):
        """Convert column number (0-indexed) to Excel-style letter (A, B, ..., Z, AA, AB, ...)."""
        result = ""
        n += 1  # Convert to 1-indexed
        while n > 0:
            n -= 1
            result = chr(n % 26 + 65) + result
            n //= 26
        return result

    tag_col_letter = col_num_to_letter(tag_col_idx)
    total_uniones_col_letter = col_num_to_letter(total_uniones_col_idx)

    print(f"  TAG_SPOOL column: {tag_col_idx + 1} (letter: {tag_col_letter})")
    print(f"  Total_Uniones column: {total_uniones_col_idx + 1} (letter: {total_uniones_col_letter})")

    # Find TEST-02 row
    test02_row_idx = None
    for idx, row in enumerate(all_rows[1:], start=2):  # Skip header, start at row 2
        if len(row) > tag_col_idx and row[tag_col_idx] == 'TEST-02':
            test02_row_idx = idx
            break

    if test02_row_idx is None:
        print("ERROR: TEST-02 row not found")
        return 1

    print(f"  TEST-02 found at row: {test02_row_idx}")

    # Step 4: Update Total_Uniones
    print("\n[4] Updating Total_Uniones to 8...")

    # Convert column index to A1 notation
    cell_address = f"{total_uniones_col_letter}{test02_row_idx}"
    print(f"  Updating cell: {cell_address}")

    operaciones_sheet.update_acell(cell_address, 8)

    print(f"  ✅ Updated {cell_address} = 8")

    # Step 5: Verify update
    print("\n[5] Verifying update...")

    # Create new repository instance to bypass cache
    repo_fresh = SheetsRepository()

    # Re-fetch spool
    updated_spool = repo_fresh.get_spool_by_tag('TEST-02')

    if not updated_spool:
        print("ERROR: Could not re-fetch TEST-02")
        return 1

    print(f"  Updated Total_Uniones: {updated_spool.total_uniones}")

    if updated_spool.total_uniones == 8:
        print("\n" + "=" * 60)
        print("✅ SUCCESS: TEST-02 now configured as v4.0 spool")
        print("=" * 60)
        print(f"\nTEST-02 Details:")
        print(f"  TAG_SPOOL: {updated_spool.tag_spool}")
        print(f"  Total_Uniones: {updated_spool.total_uniones}")
        print(f"  Version: v4.0 (Total_Uniones > 0)")
        print(f"\nYou can now use TEST-02 with /api/v4/occupation/iniciar endpoint")
        return 0
    else:
        print(f"\nERROR: Total_Uniones is {updated_spool.total_uniones}, expected 8")
        return 1


if __name__ == "__main__":
    sys.exit(main())
