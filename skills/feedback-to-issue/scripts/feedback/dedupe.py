"""Find likely-duplicate issues for a draft, using live GitHub issues.

match() is pure and testable. fetch_open_issues() shells out (gh, then the
public REST API via curl) and degrades to [] on any failure so a dedupe miss
never blocks a filing.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Callable

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return {w for w in _WORD.findall(s.lower()) if len(w) > 2}


def match(title: str, issues: list[dict], threshold: float = 0.4) -> list[dict]:
    q = _tokens(title)
    if not q:
        return []
    scored = []
    for it in issues:
        t = _tokens(it.get("title", ""))
        if not t:
            continue
        overlap = len(q & t) / len(q | t)  # Jaccard
        if overlap >= threshold:
            scored.append((overlap, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored]


def _default_runner(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def fetch_open_issues(repo: str,
                      runner: Callable[[list[str]], str] | None = None) -> list[dict]:
    runner = runner or _default_runner
    try:
        out = runner(["gh", "issue", "list", "--repo", repo, "--state", "open",
                      "--limit", "100", "--json", "number,title"])
        return json.loads(out)
    except Exception:
        pass
    try:
        out = runner(["curl", "-sSf",
                      f"https://api.github.com/repos/{repo}/issues?state=open&per_page=100"])
        data = json.loads(out)
        return [{"number": i["number"], "title": i["title"]}
                for i in data if "pull_request" not in i]
    except Exception:
        return []
