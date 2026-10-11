#!/usr/bin/env python3
"""Score a submission against an answer key.

MCQ and short answers are marked automatically. Photo answers are flagged
needs_review and are not given marks. The key stays on the admin machine.

  python3 scripts/score_submission.py --sheet sheet.json --key key.json --submission sub.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


def normalize(text):
    value = str(text).strip().lower()
    value = value.replace("₹", " ")
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\b(rupees|rs\.?|answer|ans)\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .:-")
    return value


def token_set(text):
    return {tok for tok in re.split(r"[,;\s]+", normalize(text)) if tok}


def numbers(text):
    return re.findall(r"-?\d+(?:\.\d+)?", normalize(text))


def matches(value, spec):
    accept = spec.get("accept") or []
    if not accept:
        return False
    mode = spec.get("match", "text")
    got = str(value)
    if mode == "choice":
        return got.strip().lower() in {item.strip().lower() for item in accept}
    if mode == "set":
        return any(token_set(got) == token_set(item) for item in accept)
    if mode == "number":
        got_numbers = numbers(got)
        return bool(got_numbers) and any(numbers(item) == got_numbers for item in accept)
    if mode == "token":
        got_tokens = token_set(got)
        return any(token_set(item) <= got_tokens for item in accept)
    return any(normalize(got) == normalize(item) for item in accept)


def score_leaf(node, spec, response):
    max_marks = node.get("marks")
    photo = node.get("type") == "construction" or node.get("response") == "photo" or spec.get("kind") == "photo"
    if photo:
        has_photo = bool(response.get("photo"))
        return {
            "status": "needs_review" if has_photo else "not_attempted",
            "marks_awarded": None,
            "max_marks": max_marks,
            "rubric": spec.get("rubric") or "",
        }
    value = response.get("value") or ""
    if not str(value).strip():
        return {"status": "not_attempted", "marks_awarded": 0, "max_marks": max_marks}
    ok = matches(value, spec)
    result = {
        "status": "correct" if ok else "incorrect",
        "marks_awarded": max_marks if ok else 0,
        "max_marks": max_marks,
    }
    if not ok and spec.get("wrong"):
        signal = spec["wrong"].get(normalize(str(value))) or spec["wrong"].get(str(value).strip().lower())
        if signal:
            result["misconception"] = signal
    return result


def rollup(parts, max_marks):
    statuses = [part["status"] for part in parts]
    if all(status == "correct" for status in statuses):
        status = "correct"
    elif all(status == "not_attempted" for status in statuses):
        status = "not_attempted"
    elif any(status == "needs_review" for status in statuses):
        status = "needs_review"
    elif any(status == "correct" for status in statuses) or any(status == "partial" for status in statuses):
        status = "partial"
    else:
        status = "incorrect"
    child_marks = [part.get("max_marks") for part in parts]
    if child_marks and all(marks is not None for marks in child_marks):
        if any(part["status"] == "needs_review" for part in parts):
            awarded = None
        else:
            awarded = sum(part.get("marks_awarded") or 0 for part in parts)
        return {"status": status, "marks_awarded": awarded, "max_marks": sum(child_marks)}
    if status == "correct":
        awarded = max_marks
    elif status in ("not_attempted", "incorrect"):
        awarded = 0 if max_marks is not None else None
    else:
        awarded = None
    return {"status": status, "marks_awarded": awarded, "max_marks": max_marks}


def has_nested_parts(node):
    return bool(node.get("parts")) and not node.get("response") and node.get("type") != "mcq"


def score_part(part, spec, response):
    if has_nested_parts(part):
        children = []
        for child in part["parts"]:
            child_response = (response.get("parts") or {}).get(child["id"]) or {}
            child_spec = (spec.get("parts") or {}).get(child["id"]) or {}
            children.append(score_part(child, child_spec, child_response))
        item = {"id": part["id"], "parts": children}
        item.update(rollup(children, part.get("marks")))
        return item
    item = {"id": part["id"]}
    item.update(score_leaf(part, spec, response))
    return item


def score_question(question, spec, response):
    if has_nested_parts(question):
        children = []
        for part in question["parts"]:
            part_response = (response.get("parts") or {}).get(part["id"]) or {}
            part_spec = (spec.get("parts") or {}).get(part["id"]) or {}
            children.append(score_part(part, part_spec, part_response))
        item = {"id": question["id"], "qno": question["qno"], "parts": children}
        item.update(rollup(children, question.get("marks")))
        return item
    item = {"id": question["id"], "qno": question["qno"]}
    item.update(score_leaf(question, spec, response))
    return item


def summarize(results):
    auto = [item for item in results if item["status"] in ("correct", "incorrect", "partial", "not_attempted") and item.get("marks_awarded") is not None]
    review = [item for item in results if item["status"] == "needs_review"]
    awarded = sum(item["marks_awarded"] for item in auto)
    return {
        "auto_marks": awarded,
        "needs_review": [item["id"] for item in review],
        "correct": sum(1 for item in results if item["status"] == "correct"),
        "incorrect": sum(1 for item in results if item["status"] == "incorrect"),
        "partial": sum(1 for item in results if item["status"] == "partial"),
        "not_attempted": sum(1 for item in results if item["status"] == "not_attempted"),
    }


def score(sheet, key, submission):
    answers = submission.get("answers") or {}
    questions = (key or {}).get("questions") or {}
    results = []
    for section in sheet["sections"]:
        for question in section["questions"]:
            results.append(
                score_question(question, questions.get(question["id"]) or {}, answers.get(question["id"]) or {})
            )
    return {"sheet_id": sheet["id"], "results": results, "summary": summarize(results)}


def main():
    parser = argparse.ArgumentParser(description="Score a submission offline")
    parser.add_argument("--sheet", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--submission", required=True)
    args = parser.parse_args()
    sheet = json.loads(Path(args.sheet).read_text())
    key = json.loads(Path(args.key).read_text())
    submission = json.loads(Path(args.submission).read_text())
    json.dump(score(sheet, key, submission), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
