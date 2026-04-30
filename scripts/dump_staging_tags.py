"""
Dump all TAG_SPOOLs from the staging Operaciones sheet to a JSON fixture
consumed by Playwright load-test specs.

Refuses to run if GOOGLE_SHEET_ID matches the PROD blocklist.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env.local"
FIXTURE_PATH = REPO_ROOT / "zeues-frontend" / "e2e" / "fixtures" / "staging-tags.json"

if not ENV_PATH.exists():
    print(f"FATAL: .env.local not found at {ENV_PATH}", file=sys.stderr)
    sys.exit(2)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ENV_PATH)

PROD_SHEET_IDS = frozenset(
    {
        "17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ",
        "11v8fD5Shn0RSzDceZRvXhE9z4RIOBmPA9lpH5_zF-wM",
    }
)

sheet_id = os.getenv("GOOGLE_SHEET_ID")
if not sheet_id or sheet_id in PROD_SHEET_IDS:
    print(f"FATAL: refusing to dump from prod or unset Sheet ({sheet_id})", file=sys.stderr)
    sys.exit(2)

import gspread  # noqa: E402
from google.oauth2.service_account import Credentials  # noqa: E402

private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
creds = Credentials.from_service_account_info(
    {
        "type": "service_account",
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
        "private_key": private_key,
        "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
    },
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gc = gspread.authorize(creds)
sh = gc.open_by_key(sheet_id)

if "TEST" not in sh.title.upper() and "STAGING" not in sh.title.upper():
    print(f"FATAL: refusing to dump from non-staging Sheet ({sh.title})", file=sys.stderr)
    sys.exit(2)

ws = sh.worksheet("Operaciones")
rows = ws.get_all_values()
header = rows[0]
tag_col = header.index("TAG_SPOOL")
tags = [r[tag_col] for r in rows[1:] if r[tag_col]]

FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
FIXTURE_PATH.write_text(
    json.dumps(
        {"sheet_id": sheet_id, "sheet_title": sh.title, "count": len(tags), "tags": tags},
        indent=2,
    )
)
print(f"Wrote {len(tags)} tags to {FIXTURE_PATH}")
