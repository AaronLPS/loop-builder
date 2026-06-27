"""Locate, parse, and condense a Claude Code session transcript (JSONL) into
block-signal evidence for loop-distiller. Deterministic; python3 stdlib only.

The transcript path scheme and line schema are OBSERVED Claude Code conventions,
not guaranteed APIs — verify against current docs. Env overrides keep tests off
the real ~/.claude.
"""
from __future__ import annotations

import json
import os
import pathlib

TRANSCRIPT_FILE_ENV = "LOOP_DISTILLER_TRANSCRIPT_FILE"
TRANSCRIPT_DIR_ENV = "LOOP_DISTILLER_TRANSCRIPT_DIR"


def encode_project_dir(cwd: str) -> str:
    # Observed convention: '/' and '_' both become '-'. FLAGGED — verify vs docs.
    out = []
    for ch in cwd:
        out.append("-" if ch in "/_" else ch)
    return "".join(out)


def _projects_root() -> pathlib.Path:
    return pathlib.Path.home() / ".claude" / "projects"


def _newest_jsonl(d: pathlib.Path) -> "pathlib.Path | None":
    if not d.is_dir():
        return None
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def locate(cwd: "str | None" = None) -> "pathlib.Path | None":
    f = os.environ.get(TRANSCRIPT_FILE_ENV)
    if f:
        return pathlib.Path(f)
    d = os.environ.get(TRANSCRIPT_DIR_ENV)
    if d:
        return _newest_jsonl(pathlib.Path(d))
    cwd = cwd or os.getcwd()
    return _newest_jsonl(_projects_root() / encode_project_dir(cwd))
