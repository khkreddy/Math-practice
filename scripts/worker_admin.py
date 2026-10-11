"""Shared HTTP helper for the admin scripts. Reads WORKER_URL and ADMIN_TOKEN."""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def config():
    url = os.environ.get("WORKER_URL", "").rstrip("/")
    token = os.environ.get("ADMIN_TOKEN", "")
    if not url or not token:
        sys.exit("Set WORKER_URL and ADMIN_TOKEN in the environment.")
    return url, token


def request(method, path, body=None, query=None):
    base, token = config()
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        # Cloudflare error 1010 (HTTP 403) on workers.dev when urllib's
        # default User-Agent is sent. This value is accepted.
        "User-Agent": "math-practice-admin/1.0",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            raw = res.read().decode("utf-8")
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        sys.exit(f"{method} {path} failed: HTTP {err.code} {detail}")

