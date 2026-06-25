"""Append/read/mark-filed feedback entries in a per-user JSONL log.

Lives at ~/.loop-builder/feedback.jsonl (override with LOOP_BUILDER_FEEDBACK_FILE
for tests). Changing state only — never committed, never inside a SKILL.md.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
import uuid

SCHEMA = 1
CATEGORIES = ("bug", "feedback", "idea")


def log_path() -> pathlib.Path:
    override = os.environ.get("LOOP_BUILDER_FEEDBACK_FILE")
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".loop-builder" / "feedback.jsonl"


def append(category: str, text: str, source: str = "loop-builder",
           context: dict | None = None) -> dict:
    if category not in CATEGORIES:
        raise ValueError(f"invalid category: {category!r} (want one of {CATEGORIES})")
    entry = {
        "id": uuid.uuid4().hex,
        "ts": int(time.time()),
        "source": source,
        "category": category,
        "text": text,
        "context": context or {},
        "status": "open",
        "issue": None,
        "schema": SCHEMA,
    }
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_all() -> list[dict]:
    path = log_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def list_open() -> list[dict]:
    return [e for e in read_all() if e.get("status") == "open"]


def mark_filed(ids: list[str], issue: int) -> int:
    path = log_path()
    entries = read_all()
    target = set(ids)
    n = 0
    for e in entries:
        if e.get("id") in target and e.get("status") == "open":
            e["status"] = "filed"
            e["issue"] = issue
            n += 1
    with path.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return n
