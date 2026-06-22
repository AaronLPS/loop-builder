"""Redact machine-local paths, secrets, and emails from issue text.

Best-effort and deterministic — the real backstop is the human consent gate.
The patterns mirror the repo's secret-scanning work (this is a standalone
redactor, not a call into gitleaks).
"""
from __future__ import annotations

import re

# Machine-local absolute home path prefix -> ~ (keeps the rest of the path).
_HOME = re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+")

_SECRET_PATTERNS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                       # AWS access key id
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),                    # GitHub PAT (classic)
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b"),           # GitHub PAT (fine-grained)
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def sanitize(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    def note(kind: str) -> None:
        if kind not in notes:
            notes.append(kind)

    def home_sub(_m: "re.Match[str]") -> str:
        note("local-path")
        return "~"

    text = _HOME.sub(home_sub, text)

    for pat in _SECRET_PATTERNS:
        if pat.search(text):
            note("secret")
            text = pat.sub("<<REDACTED-SECRET>>", text)

    def email_sub(_m: "re.Match[str]") -> str:
        note("email")
        return "<<REDACTED-EMAIL>>"

    text = _EMAIL.sub(email_sub, text)
    return text, notes
