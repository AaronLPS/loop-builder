"""Tier 3 candidate ledger: curated recurring-workflow candidates.

Machine-global at ~/.loop-builder/scan-ledger.jsonl (override with
LOOP_DISTILLER_LEDGER_FILE for tests). Dedup by signature+status: a signature
already dismissed/built is never resurrected. Changing state — not in any SKILL.md.
"""
from __future__ import annotations

import json
import os
import pathlib
import uuid

LEDGER_FILE_ENV = "LOOP_DISTILLER_LEDGER_FILE"
SCHEMA = 1
_TERMINAL = ("dismissed", "built")


def ledger_path() -> pathlib.Path:
    override = os.environ.get(LEDGER_FILE_ENV)
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".loop-builder" / "scan-ledger.jsonl"


def read_all() -> list:
    p = ledger_path()
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _rewrite(records: list) -> None:
    p = ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def upsert(signature: str, label: str, projects: list, evidence: list,
           blocks: list, ts: int) -> dict:
    records = read_all()
    for r in records:
        if r["signature"] == signature:
            if r["status"] in _TERMINAL:
                return r                       # do not resurrect dismissed/built
            ev = sorted(set(r["evidence"]) | set(evidence))
            r["evidence"] = ev
            r["count"] = len(ev)
            r["projects"] = sorted(set(r["projects"]) | set(projects))
            r["blocks"] = sorted(set(r["blocks"]) | set(blocks))
            r["last_seen"] = max(r["last_seen"], ts)
            r["label"] = label or r["label"]
            _rewrite(records)
            return r
    ev = sorted(set(evidence))
    rec = {
        "id": uuid.uuid4().hex,
        "signature": signature,
        "label": label,
        "count": len(ev),
        "projects": sorted(set(projects)),
        "first_seen": ts,
        "last_seen": ts,
        "evidence": ev,
        "blocks": sorted(set(blocks)),
        "status": "new",
        "schema": SCHEMA,
    }
    records.append(rec)
    _rewrite(records)
    return rec


def mark(candidate_id: str, status: str) -> dict:
    records = read_all()
    hit = None
    for r in records:
        if r["id"] == candidate_id:
            r["status"] = status
            hit = r
    if hit is None:
        raise KeyError(f"no candidate with id {candidate_id!r}")
    _rewrite(records)
    return hit
