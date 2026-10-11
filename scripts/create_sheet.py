#!/usr/bin/env python3
"""Push a practice sheet and its answer key to the Worker.

Prints a fresh student token and the Pages link. The key file stays on the
admin machine; this script does not write it anywhere.

Environment: WORKER_URL, ADMIN_TOKEN.
Optional: PAGES_URL (default https://khkreddy.github.io/Math-practice/).
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worker_admin


def main():
    parser = argparse.ArgumentParser(description="Create or replace a practice sheet")
    parser.add_argument("--sheet", required=True, help="Student-facing sheet JSON")
    parser.add_argument("--key", required=True, help="Answer key JSON (not committed)")
    parser.add_argument(
        "--allow-resubmit",
        action="store_true",
        help="Allow another final submit after one is stored",
    )
    args = parser.parse_args()
    sheet = json.loads(Path(args.sheet).read_text())
    key = json.loads(Path(args.key).read_text())
    sheet_id = sheet["id"]
    if key.get("sheet_id") and key["sheet_id"] != sheet_id:
        sys.exit("answer key sheet_id does not match the sheet")
    status, payload = worker_admin.request(
        "PUT",
        f"/admin/sheet/{sheet_id}",
        {"sheet": sheet, "answer_key": key, "allow_resubmit": args.allow_resubmit},
    )
    pages = os.environ.get("PAGES_URL", "https://khkreddy.github.io/Math-practice/").rstrip("/") + "/"
    token = payload["token"]
    link = f"{pages}?sheet={sheet_id}&t={token}"
    print(f"status: {status}")
    print(f"sheet: {sheet_id}")
    print(f"token: {token}")
    print(f"link: {link}")


if __name__ == "__main__":
    main()
