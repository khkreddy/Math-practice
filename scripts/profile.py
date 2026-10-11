#!/usr/bin/env python3
"""Get or replace the student profile stored on the Worker.

Environment: WORKER_URL, ADMIN_TOKEN.

  python3 scripts/profile.py get
  python3 scripts/profile.py put --file profile.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worker_admin


def main():
    parser = argparse.ArgumentParser(description="Get or put the student profile")
    parser.add_argument("action", choices=["get", "put"])
    parser.add_argument("--file", help="Profile JSON for put")
    args = parser.parse_args()
    if args.action == "get":
        _, payload = worker_admin.request("GET", "/admin/profile")
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    if not args.file:
        sys.exit("put requires --file")
    profile = json.loads(Path(args.file).read_text())
    _, payload = worker_admin.request("PUT", "/admin/profile", {"profile": profile})
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
