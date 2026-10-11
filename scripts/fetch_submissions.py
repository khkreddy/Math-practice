#!/usr/bin/env python3
"""Fetch submissions from the Worker and print JSON.

Environment: WORKER_URL, ADMIN_TOKEN.

  python3 scripts/fetch_submissions.py --since 2026-10-11T00:00:00Z
  python3 scripts/fetch_submissions.py --id 2026-10-11-p1
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worker_admin


def main():
    parser = argparse.ArgumentParser(description="Fetch practice submissions")
    parser.add_argument("--since", help="ISO timestamp; only submissions at or after this time")
    parser.add_argument("--id", help="Sheet id. Prints that submission, including photos")
    args = parser.parse_args()
    if args.id:
        _, payload = worker_admin.request("GET", f"/admin/submission/{args.id}")
    else:
        query = {"since": args.since} if args.since else None
        _, payload = worker_admin.request("GET", "/admin/submissions", query=query)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
