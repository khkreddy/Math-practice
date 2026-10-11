"""One repair pass for an item the release gate did not admit.

The gate stays strict. A TOP pass is the exception. A rejected item is recorded
with the gate's explanation, then rewritten once from that explanation.
"""
from __future__ import annotations

import json

STANDING = (
    "Repair only the failures named below. Keep the same hinge decision. "
    "Write the stem as complete sentences that name the actor and the action. "
    "'A plant adds a non-metal to water' is ambiguous; name the place, such as a water treatment plant. "
    "Do not state a property the scene does not give, such as electrical conductivity when the stem never mentions it. "
    "Four options are enough. Do not add a fifth option when it would be a weak distractor or would need a fact the stem does not state. "
    "Exactly one option is the key. A distractor must be false, and it must not use the same logic as the key. "
    "An option states a claim a student might choose. It does not describe the mistake with words such as 'instead of', 'by reversing', or 'confuses'. "
    "A claim must not contradict a fact the stem already states. "
    "Wrong options come from testing the routes on this stem and key. Do not paste a stored mix-up sentence. "
    "If two routes reach the same result, keep that result once, as the result itself, without a sentence that explains the route. "
    "Do not copy a border, a law, or a decision sentence into the stem or the options."
)


def _codes(miqg: dict) -> list[str]:
    raw = miqg.get("major_codes") or []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [str(part).strip() for part in raw if str(part).strip()]


def is_admitted(trail: dict) -> bool:
    miqg = trail.get("miqg") if isinstance(trail.get("miqg"), dict) else {}
    return (
        trail.get("status") == "OK"
        and miqg.get("quality_tier") == "TOP"
        and miqg.get("release_gate") == "PASS"
    )


def explain_gate(trail: dict, reviewer: str = "") -> dict:
    """Plain-language record of the release decision. Admitted is TOP and PASS only."""
    miqg = trail.get("miqg") if isinstance(trail.get("miqg"), dict) else {}
    try:
        from miqg_cal import PHRASE
    except ImportError:
        from systems.modify.miqg.miqg_cal import PHRASE

    findings = miqg.get("findings") if isinstance(miqg.get("findings"), list) else []
    lines = []
    admitted = is_admitted(trail)
    tier = str(miqg.get("quality_tier") or "")
    gate = str(miqg.get("release_gate") or "")
    if admitted:
        lines.append(
            "Admitted. Release gate PASS, tier TOP"
            + (". " + str(miqg.get("decisive_reason")) if miqg.get("decisive_reason") else ".")
        )
    else:
        reason = str(trail.get("refusal_reason") or "").strip()
        harness = bool(reason) and not reason.startswith("MIQG:")
        if harness:
            lines.append("Rejected by the harness. " + reason)
            if tier == "TOP" and gate == "PASS":
                lines.append(
                    "MIQG scored this text TOP, and that score does not admit the item. "
                    "The harness rejection stands."
                )
            elif tier or gate:
                because = str(miqg.get("decisive_reason") or "the gate did not pass it")
                lines.append(f"Release gate {gate or 'not run'}, tier {tier or 'none'}, because {because}.")
        else:
            lines.append("Rejected. Most items stop here. A person can still check this item.")
            if tier or gate:
                because = str(miqg.get("decisive_reason") or "the gate did not pass it")
                lines.append(f"Release gate {gate or 'not run'}, tier {tier or 'none'}, because {because}.")
        for code in _codes(miqg):
            if harness and code in {"KNOWN_GOOD_ENVELOPE"}:
                continue
            gloss = PHRASE.get(code) or "named failure"
            quote = ""
            loc = ""
            for finding in findings:
                if isinstance(finding, dict) and finding.get("code") == code:
                    quote = str(finding.get("quote") or "")
                    loc = str(finding.get("loc") or "")
                    break
            bit = f"{code}: {gloss}."
            if quote:
                bit += f" Quoted text: {quote}."
            if loc:
                bit += f" Location: {loc}."
            lines.append(bit)
    note = reviewer.strip()
    if note:
        lines.append("Reviewer: " + note)
    return {
        "admitted": admitted,
        "tier": tier,
        "release_gate": gate,
        "decisive_reason": str(miqg.get("decisive_reason") or ""),
        "explanation": " ".join(lines),
    }


def _slim(item: dict) -> dict:
    if not isinstance(item, dict):
        return {}
    options = []
    for raw in item.get("options") or []:
        if isinstance(raw, dict):
            options.append({"id": raw.get("id"), "text": raw.get("text")})
        else:
            options.append(raw)
    return {
        "stem": item.get("stem"),
        "item_type": item.get("item_type"),
        "options": options,
        "statements": item.get("statements"),
        "answer": item.get("answer"),
        "mx_option_map": item.get("mx_option_map"),
        "statement_mx_map": item.get("statement_mx_map"),
    }


def repair_instruction(trail: dict, reviewer: str, legal_ids: list[str], item: dict) -> str:
    """The one repair prompt. It carries the gate explanation, not a new quality bar.

    legal_ids is accepted so existing callers keep working. Stored mix-up ids
    are not sent to the writer.
    """
    del legal_ids
    record = explain_gate(trail, reviewer)
    failed = json.dumps(_slim(item), ensure_ascii=False)
    if len(failed) > 1800:
        failed = failed[:1800]
    return (
        "ONE REPAIR PASS. The release gate rejected the item below. "
        "Rewrite it so those failures are gone. Do not start a different question.\n"
        + STANDING
        + "\nGate record: "
        + record["explanation"]
        + "\nRejected item:\n"
        + failed
    )
