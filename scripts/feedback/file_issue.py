"""Create a GitHub issue as the *current user* — gh if authed, else a prefilled
browser URL. No project token, no server: the issue is always the user's.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import urllib.parse
import webbrowser
from typing import Callable

URL_LIMIT = 8000


def build_url(repo: str, title: str, body: str, labels: list[str]) -> str:
    params = {"title": title, "body": body}
    if labels:
        params["labels"] = ",".join(labels)
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"https://github.com/{repo}/issues/new?{query}"


def build_gh_command(repo: str, title: str, body_file: str, labels: list[str]) -> list[str]:
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", body_file]
    if labels:
        cmd += ["--label", ",".join(labels)]
    return cmd


def _default_status_runner(cmd: list[str]) -> int:
    return subprocess.run(cmd, capture_output=True, text=True).returncode


def gh_available(runner: Callable[[list[str]], int] | None = None) -> bool:
    runner = runner or _default_status_runner
    try:
        return runner(["gh", "auth", "status"]) == 0
    except Exception:
        return False


def _default_capture_runner(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def create(repo: str, title: str, body: str, labels: list[str], *,
           dry_run: bool = False,
           gh_check: Callable[[], bool] | None = None,
           gh_runner: Callable[[list[str]], str] | None = None,
           url_opener: Callable[[str], object] | None = None) -> dict:
    gh_check = gh_check or gh_available
    if gh_check():
        if dry_run:
            cmd = build_gh_command(repo, title, "<body-file>", labels)
            return {"method": "gh", "issue": None, "url": None, "command": cmd, "truncated": False}
        runner = gh_runner or _default_capture_runner
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(body)
            body_file = fh.name
        try:
            out = runner(build_gh_command(repo, title, body_file, labels))
        finally:
            os.unlink(body_file)
        url = out.strip().splitlines()[-1] if out.strip() else None
        issue = None
        if url and "/issues/" in url:
            try:
                issue = int(url.rsplit("/", 1)[-1])
            except ValueError:
                issue = None
        return {"method": "gh", "issue": issue, "url": url,
                "command": build_gh_command(repo, title, "<body-file>", labels), "truncated": False}

    # URL fallback (user submits as themselves in their logged-in browser).
    url = build_url(repo, title, body, labels)
    truncated = False
    if len(url) > URL_LIMIT:
        overhead = len(build_url(repo, title, "", labels))
        room = max(URL_LIMIT - overhead - 200, 0)
        short = body[:room] + "\n\n(truncated — full body printed in terminal)"
        url = build_url(repo, title, short, labels)
        truncated = True
        # Ensure final URL length (after percent-encoding) stays under limit
        while len(url) > URL_LIMIT and short:
            # Remove chars from body portion (before the truncation message)
            body_part = short[:short.rfind("\n\n(truncated")]
            if body_part:
                body_part = body_part[:-1]  # Remove one character
                short = body_part + "\n\n(truncated — full body printed in terminal)"
                url = build_url(repo, title, short, labels)
            else:
                break
    if not dry_run:
        (url_opener or webbrowser.open)(url)
    return {"method": "url", "issue": None, "url": url, "command": None, "truncated": truncated}
