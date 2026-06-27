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
PROJECTS_ROOT_ENV = "LOOP_DISTILLER_PROJECTS_ROOT"


def encode_project_dir(cwd: str) -> str:
    # Observed convention: '/' and '_' both become '-'. FLAGGED — verify vs docs.
    out = []
    for ch in cwd:
        out.append("-" if ch in "/_" else ch)
    return "".join(out)


def _projects_root() -> pathlib.Path:
    override = os.environ.get(PROJECTS_ROOT_ENV)
    if override:
        return pathlib.Path(override)
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


def _block_text(block: dict) -> str:
    if block.get("type") == "text":
        return str(block.get("text", ""))
    if block.get("type") == "tool_use":
        inp = block.get("input", {})
        return str(inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp)
    if block.get("type") == "tool_result":
        c = block.get("content", "")
        return c if isinstance(c, str) else json.dumps(c)
    return ""


def parse(path) -> list[dict]:
    events: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (ValueError, TypeError):
                continue
            msg = obj.get("message") or {}
            role = msg.get("role") or obj.get("type") or "unknown"
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type", "")
                etype = "tool_use" if btype == "tool_use" else (
                    "tool_result" if btype == "tool_result" else role)
                events.append({
                    "i": i,
                    "role": role,
                    "type": etype,
                    "tool": block.get("name") if btype == "tool_use" else None,
                    "text": _block_text(block),
                })
    return events


# Deterministic keyword categorization. Coarse on purpose: it surfaces evidence
# with line refs; the SKILL.md makes the loop-worthiness judgment, not this code.
_VERIFY_KW = ("pytest", "go test", "npm test", "npm run test", "cargo test",
              "make test", "make build", "ctest", "jest", "vitest", "tox")
_VCS_KW = ("git commit", "git push", "gh pr create", "gh pr merge", "git merge",
           "gh release", "deploy", "git tag")
_DISCOVERY_TOOLS = {"Read", "Grep", "Glob", "LS", "NotebookRead"}
_ACTION_TOOLS = {"Edit", "Write", "NotebookEdit"}
_DISCOVERY_BASH = ("ls ", "cat ", "find ", "grep ", "rg ", "list", "status", "log ", "diff")


def _hint(text: str) -> str:
    return " ".join(text.split())[:80]


def condense(events: list[dict]) -> dict:
    buckets = {"discovery": [], "action": [], "verify": [], "vcs": []}
    for e in events:
        if e["type"] != "tool_use":
            continue
        tool, text = e["tool"] or "", e["text"] or ""
        low = text.lower()
        ref = {"i": e["i"], "tool": tool, "hint": _hint(text)}
        if any(k in low for k in _VERIFY_KW):
            buckets["verify"].append(ref)
        elif any(k in low for k in _VCS_KW):
            buckets["vcs"].append(ref)
        elif tool in _ACTION_TOOLS:
            buckets["action"].append(ref)
        elif tool in _DISCOVERY_TOOLS:
            buckets["discovery"].append(ref)
        elif tool == "Bash" and any(k in low for k in _DISCOVERY_BASH):
            buckets["discovery"].append(ref)
        elif tool == "Bash":
            buckets["action"].append(ref)  # other shell mutations
    counts = {k: len(v) for k, v in buckets.items()}
    return {**buckets, "counts": counts}


def fingerprint(path) -> str:
    st = pathlib.Path(path).stat()
    return f"{path}|{st.st_mtime_ns}|{st.st_size}"


def list_transcripts(projects_root=None) -> list:
    root = pathlib.Path(projects_root) if projects_root else _projects_root()
    if not root.is_dir():
        return []
    return sorted(root.glob("*/*.jsonl"))
