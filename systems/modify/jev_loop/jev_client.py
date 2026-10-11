"""JEV System One client for T-PLAN and T-JEV-CLASSIFY. Key from env only."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

JEV_URL = os.environ.get("TTWIN_JEV_URL") or "https://jev-ai.pro/api/v1/systemone"
MODEL = os.environ.get("TTWIN_JEV_MODEL") or "jev-latest"


def load_jev_key() -> str:
    raw = (os.environ.get("TTWIN_JEV_KEY") or "").strip()
    if raw.startswith("sk_"):
        return raw
    path = os.environ.get("TTWIN_JEV_KEY_FILE")
    if path:
        p = Path(path)
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("sk_"):
                    return line
    raise RuntimeError(
        "JEV key missing. Set TTWIN_JEV_KEY or TTWIN_JEV_KEY_FILE. Never commit the key."
    )


def jev_call(key: str, state, questions: dict, retries: int = 5) -> dict:
    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode("utf-8")
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            JEV_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 TTwinModifyJevLoop/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace") if e.fp else str(e)
            last = f"HTTP {e.code} {err[:500]}"
            if e.code == 402:
                raise RuntimeError("JEV 402 Payment Required — credits exhausted.") from e
            if e.code in {403, 429, 500, 502, 503, 520, 521, 522, 523, 524}:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise RuntimeError(last) from e
        except Exception as e:
            last = str(e)
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(last or "JEV call failed")
