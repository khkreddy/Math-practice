#!/usr/bin/env python3
"""Run the DeepSeek science mint in the background and push JEV-pass hourly.

This process does not need a Cursor agent. Stop by writing the STOP file:
  systems/modify/jev_loop/mint_learning/science_gap_STOP
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTWIN_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import bank_gate  # noqa: E402

PUSH_S = 3600
CHECK_S = 20
STOP_FILE = HERE / "mint_learning" / "science_gap_STOP"
LOG_FILE = HERE / "mint_learning" / "science_gap_supervisor.log"
CAMPAIGN_PID = HERE / "mint_learning" / "science_gap_campaign.pid"
SUPERVISOR_PID = HERE / "mint_learning" / "science_gap_supervisor.pid"
CAMPAIGN_OUT = HERE / "mint_learning" / "science_gap_campaign.out.log"
SCIENCE_JSONL = TTWIN_ROOT / "data" / "questions" / "JEV-pass" / "middle_6_8" / "science.jsonl"
MANIFEST = TTWIN_ROOT / "data" / "questions" / "MANIFEST.json"

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = utc() + " " + msg
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except SystemError:
        return False
    return True


def read_pid(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid) + "\n", encoding="utf-8")


def start_campaign() -> int:
    CAMPAIGN_OUT.parent.mkdir(parents=True, exist_ok=True)
    handle = CAMPAIGN_OUT.open("a", encoding="utf-8")
    flags = CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        [sys.executable, "-u", str(HERE / "science_gap_campaign.py")],
        cwd=str(HERE),
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=flags,
        close_fds=False,
    )
    write_pid(CAMPAIGN_PID, proc.pid)
    log(f"campaign started pid={proc.pid}")
    return proc.pid


def ensure_campaign() -> None:
    pid = read_pid(CAMPAIGN_PID)
    if pid_alive(pid):
        return
    start_campaign()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(TTWIN_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def strip_held_manifest() -> None:
    if not MANIFEST.is_file():
        return
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = list(man.get("files") or [])
    kept = []
    dropped_n = 0
    for rec in files:
        path = str(rec.get("path") or "")
        stem = Path(path).stem
        if stem.endswith("_held"):
            dropped_n += int(rec.get("n") or 0)
            continue
        kept.append(rec)
    if len(kept) == len(files):
        return
    man["files"] = kept
    man["n"] = int(man.get("n") or 0) - dropped_n
    man["held"] = int(man.get("held") or 0) - dropped_n
    MANIFEST.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    log(f"manifest stripped held={dropped_n}")


def hourly_push() -> None:
    try:
        bank_gate.sync_manifest(TTWIN_ROOT)
    except Exception as exc:
        log(f"sync_manifest failed: {type(exc).__name__}: {exc}")
        return
    strip_held_manifest()
    add = git("add", "--", str(SCIENCE_JSONL), str(MANIFEST))
    if add.returncode != 0:
        log("git add failed: " + (add.stderr or add.stdout or "")[-400:])
        return
    porcelain = git("status", "--porcelain", "--", str(SCIENCE_JSONL), str(MANIFEST))
    if not (porcelain.stdout or "").strip():
        log("hourly push: no new JEV-pass rows")
        return
    commit = git(
        "commit",
        "-m",
        "Add MIQG TOP middle-school science questions written for empty hinges.",
    )
    if commit.returncode != 0:
        log("git commit failed: " + (commit.stderr or commit.stdout or "")[-400:])
        return
    push = git("push", "origin", "HEAD")
    if push.returncode != 0:
        log("git push failed: " + (push.stderr or push.stdout or "")[-400:])
        return
    log("hourly push ok")


def main() -> int:
    STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_pid(SUPERVISOR_PID, os.getpid())
    log(f"supervisor start pid={os.getpid()}")
    if STOP_FILE.is_file():
        STOP_FILE.unlink()
        log("cleared leftover STOP file")
    ensure_campaign()
    hourly_push()
    next_push = time.time() + PUSH_S
    while True:
        if STOP_FILE.is_file():
            log("STOP file present; supervisor exiting (campaign left running)")
            return 0
        ensure_campaign()
        now = time.time()
        if now >= next_push:
            hourly_push()
            next_push = now + PUSH_S
        time.sleep(CHECK_S)


if __name__ == "__main__":
    raise SystemExit(main())
