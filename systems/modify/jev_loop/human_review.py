"""Optional human-review appendix for the T-MINT writer prompt.

Enabled when TTWIN_FILL_FEEDBACK_DIR points at fill_review/feedback/next_run.
Missing dir or files are a no-op.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def feedback_dir() -> Path | None:
    raw = (os.environ.get("TTWIN_FILL_FEEDBACK_DIR") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def appendix(req: dict) -> str:
    root = feedback_dir()
    if root is None:
        return ""
    parts: list[str] = []
    block = root / "writer_prompt_block.txt"
    if block.is_file():
        text = block.read_text(encoding="utf-8").strip()
        if text:
            parts.append(text)
    gold_path = root / "gold_examples.json"
    cid = str(req.get("target_construct") or "")
    if gold_path.is_file() and cid:
        try:
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            gold = []
        hits = [g for g in gold if isinstance(g, dict) and g.get("construct") == cid]
        if not hits:
            hits = [g for g in gold if isinstance(g, dict) and g.get("intended") == cid]
        for g in hits[:2]:
            excerpt = str(g.get("stem_excerpt") or "").strip()
            if not excerpt:
                continue
            note = str(g.get("notes") or "").strip()
            line = f"GOLD example for {cid}: {excerpt}"
            if note:
                line += f" Reviewer: {note}"
            parts.append(line)
    skip_path = root / "skip_constructs.json"
    if skip_path.is_file() and cid:
        try:
            skip = json.loads(skip_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            skip = []
        if cid in skip:
            parts.append(
                f"Reviewers marked sitting items for {cid} as cannot_sit. "
                "If you write, the evidence must clearly exceed a definition restatement."
            )
    if not parts:
        return ""
    return "\n".join(parts) + "\n"
