"""Tier 1 digest index: read each transcript ONCE, append a compact digest.

Machine-global store at ~/.loop-builder/digests.jsonl (override with
LOOP_DISTILLER_DIGESTS_FILE for tests). Changing state — never inside a SKILL.md.
"""
from __future__ import annotations

import json
import os
import pathlib

import transcript_reader as tr
import signature as sig

DIGESTS_FILE_ENV = "LOOP_DISTILLER_DIGESTS_FILE"
SCHEMA = 1
_CMD_CAP = 12


def digests_path() -> pathlib.Path:
    override = os.environ.get(DIGESTS_FILE_ENV)
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".loop-builder" / "digests.jsonl"


def digest(path) -> dict:
    path = pathlib.Path(path)
    condensed = tr.condense(tr.parse(path))
    blocks = [b for b in ("discovery", "action", "verify", "vcs")
              if condensed["counts"].get(b, 0) > 0]
    commands = []
    for b in ("discovery", "action", "verify", "vcs"):
        for ref in condensed[b]:
            commands.append(ref["hint"])
    return {
        "fingerprint": tr.fingerprint(path),
        "project": path.parent.name,
        "path": str(path),
        "ts": int(path.stat().st_mtime),
        "signature": sig.signature(condensed),
        "blocks": blocks,
        "commands": commands[:_CMD_CAP],
        "schema": SCHEMA,
    }


def append(d: dict) -> None:
    p = digests_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(d, ensure_ascii=False) + "\n")


def read_all() -> list:
    p = digests_path()
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def seen_fingerprints() -> set:
    return {d["fingerprint"] for d in read_all()}


def digest_new(paths: list) -> list:
    seen = seen_fingerprints()
    new = []
    for path in paths:
        fp = tr.fingerprint(path)
        if fp in seen:
            continue
        d = digest(path)
        append(d)
        seen.add(fp)
        new.append(d)
    return new
