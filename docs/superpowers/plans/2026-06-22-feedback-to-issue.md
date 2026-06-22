# feedback-to-issue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user capture bugs/feedback during loop-builder use and file a clean GitHub issue under their own account, with no project token or server.

**Architecture:** Deterministic, security-relevant work lives in stdlib-only `python3` modules under `scripts/feedback/` (log, sanitize, dedupe, file-issue), each unit-tested. A CLI exposes them as subcommands. loop-builder's `SKILL.md` plus a `references/feedback-to-issue.md` playbook orchestrate capture, summarization, the mandatory consent gate, and filing. GitHub issue forms make every submission path consistent.

**Tech Stack:** Python 3 (standard library only), bash test harness, GitHub Actions, `gh` CLI (user's own), GitHub issue forms.

## Global Constraints

- **Python 3, standard library only** — no PyYAML, no pytest, no third-party deps. CI runs plain `ubuntu-latest` python3.
- **Repo slug is `AaronLPS/loop-builder`** — used verbatim wherever a repo is named.
- **No project-owned token and no server, ever** — issues are created only via the user's own `gh` auth or a prefilled browser URL.
- **Sanitize-then-consent is mandatory and non-skippable** — every draft is sanitized, then shown in full to the user for explicit confirmation before any issue is created. No auto-file path exists.
- **Feedback log is per-user at `~/.loop-builder/feedback.jsonl`**, overridable with env var `LOOP_BUILDER_FEEDBACK_FILE` (tests use this). Never committed.
- **No emoji in docs** (per `AGENTS.md`).
- **`SKILL.md` stays under ~500 lines** (currently 400) — push depth into `references/`.
- **Commit message trailer:** end every commit with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Test layout:** modules in `scripts/feedback/`, unit tests in `scripts/tests/feedback/test_*.py`, each test inserts the module dir on `sys.path`. A bash harness `scripts/tests/test_feedback.sh` runs `python3 -m unittest` and follows the repo's red-green (exit 0 == clean) contract.
- **Test fixtures must survive the repo's own hooks:** never write a literal machine-local path (`/home/<name>/...`, `/Users/<name>/...`) in a committed file — the `no-local-home-paths` pygrep hook will block the commit. Build such sample strings from fragments (`"/home/" + "someuser" + "/x"`). For a sample secret, use the documented AWS example value `AKIAIOSFODNN7EXAMPLE` (gitleaks allowlists it) — a real-format key would be blocked by the gitleaks hook.

---

### Task 1: feedback_log — append/read/mark-filed

**Files:**
- Create: `scripts/feedback/feedback_log.py`
- Test: `scripts/tests/feedback/test_feedback_log.py`

**Interfaces:**
- Produces:
  - `log_path() -> pathlib.Path`
  - `append(category: str, text: str, source: str = "loop-builder", context: dict | None = None) -> dict` — entry has keys `id, ts, source, category, text, context, status, issue, schema`
  - `read_all() -> list[dict]`
  - `list_open() -> list[dict]`
  - `mark_filed(ids: list[str], issue: int) -> int` (count updated)
  - Valid categories: `"bug"`, `"feedback"`, `"idea"`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/feedback/test_feedback_log.py
import os, sys, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "feedback"))
import feedback_log  # noqa: E402


class FeedbackLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        os.environ["LOOP_BUILDER_FEEDBACK_FILE"] = self.tmp.name

    def tearDown(self):
        os.unlink(self.tmp.name)
        os.environ.pop("LOOP_BUILDER_FEEDBACK_FILE", None)

    def test_append_then_read(self):
        e = feedback_log.append("bug", "verifier crashed", context={"action": "scaffold"})
        self.assertEqual(e["category"], "bug")
        self.assertEqual(e["status"], "open")
        self.assertTrue(e["id"])
        all_entries = feedback_log.read_all()
        self.assertEqual(len(all_entries), 1)
        self.assertEqual(all_entries[0]["text"], "verifier crashed")

    def test_invalid_category_rejected(self):
        with self.assertRaises(ValueError):
            feedback_log.append("nonsense", "x")

    def test_mark_filed_only_targets_given_ids(self):
        a = feedback_log.append("bug", "a")
        b = feedback_log.append("idea", "b")
        n = feedback_log.mark_filed([a["id"]], 42)
        self.assertEqual(n, 1)
        by_id = {e["id"]: e for e in feedback_log.read_all()}
        self.assertEqual(by_id[a["id"]]["status"], "filed")
        self.assertEqual(by_id[a["id"]]["issue"], 42)
        self.assertEqual(by_id[b["id"]]["status"], "open")
        self.assertEqual(feedback_log.list_open(), [e for e in feedback_log.read_all() if e["id"] == b["id"]])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.feedback.test_feedback_log -v` (from repo root; if module discovery complains, run `python3 scripts/tests/feedback/test_feedback_log.py`)
Expected: FAIL — `ModuleNotFoundError: No module named 'feedback_log'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/feedback/feedback_log.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 scripts/tests/feedback/test_feedback_log.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/feedback/feedback_log.py scripts/tests/feedback/test_feedback_log.py
git commit -m "feat(feedback): per-user JSONL feedback log

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: sanitize — redact paths/secrets/emails

**Files:**
- Create: `scripts/feedback/sanitize.py`
- Test: `scripts/tests/feedback/test_sanitize.py`

**Interfaces:**
- Produces: `sanitize(text: str) -> tuple[str, list[str]]` — returns `(redacted_text, notes)`; `notes` is a de-duplicated list drawn from `"local-path"`, `"secret"`, `"email"`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/feedback/test_sanitize.py
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "feedback"))
import sanitize  # noqa: E402


class SanitizeTest(unittest.TestCase):
    def test_home_path_collapses_to_tilde_keeping_structure(self):
        # built from fragments so this design doc embeds no literal home path
        sample = "/home/" + "someuser" + "/proj/app.py"
        out, notes = sanitize.sanitize("see " + sample + " for details")
        self.assertIn("~/proj/app.py", out)
        self.assertNotIn("someuser", out)
        self.assertIn("local-path", notes)

    def test_macos_path_also_redacted(self):
        sample = "/Users/" + "someuser" + "/code/app.js"
        out, notes = sanitize.sanitize(sample)
        self.assertTrue(out.startswith("~/code/app.js"))
        self.assertIn("local-path", notes)

    def test_aws_key_redacted(self):
        # AKIAIOSFODNN7EXAMPLE is the documented AWS sample key (gitleaks allowlists it)
        out, notes = sanitize.sanitize("key=AKIAIOSFODNN7EXAMPLE")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", out)
        self.assertIn("secret", notes)

    def test_email_redacted(self):
        out, notes = sanitize.sanitize("ping me at someone@example.com please")
        self.assertNotIn("someone@example.com", out)
        self.assertIn("email", notes)

    def test_clean_text_untouched(self):
        out, notes = sanitize.sanitize("the verifier returns the wrong exit code")
        self.assertEqual(out, "the verifier returns the wrong exit code")
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 scripts/tests/feedback/test_sanitize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sanitize'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/feedback/sanitize.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 scripts/tests/feedback/test_sanitize.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/feedback/sanitize.py scripts/tests/feedback/test_sanitize.py
git commit -m "feat(feedback): deterministic path/secret/email redactor

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: dedupe — match a draft against live issues

**Files:**
- Create: `scripts/feedback/dedupe.py`
- Test: `scripts/tests/feedback/test_dedupe.py`

**Interfaces:**
- Produces:
  - `match(title: str, issues: list[dict], threshold: float = 0.4) -> list[dict]` — pure; ranks issues (each `{"number", "title"}`) by Jaccard token overlap, highest first.
  - `fetch_open_issues(repo: str, runner: Callable[[list[str]], str] | None = None) -> list[dict]` — gh first, then public REST via curl; returns `[]` on any failure.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/feedback/test_dedupe.py
import sys, pathlib, json, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "feedback"))
import dedupe  # noqa: E402

ISSUES = [
    {"number": 1, "title": "verifier crashes on empty state file"},
    {"number": 2, "title": "scheduler ignores dynamic interval"},
    {"number": 3, "title": "typo in README install section"},
]


class DedupeTest(unittest.TestCase):
    def test_match_ranks_overlapping_issue_first(self):
        res = dedupe.match("verifier crash when state file empty", ISSUES)
        self.assertTrue(res)
        self.assertEqual(res[0]["number"], 1)

    def test_no_match_below_threshold(self):
        self.assertEqual(dedupe.match("billing dashboard colors", ISSUES), [])

    def test_fetch_uses_gh_when_available(self):
        def runner(cmd):
            self.assertEqual(cmd[0], "gh")
            return json.dumps([{"number": 5, "title": "from gh"}])

        out = dedupe.fetch_open_issues("AaronLPS/loop-builder", runner=runner)
        self.assertEqual(out, [{"number": 5, "title": "from gh"}])

    def test_fetch_falls_back_to_curl_and_drops_prs(self):
        def runner(cmd):
            if cmd[0] == "gh":
                raise RuntimeError("no gh")
            # REST shape; entries carrying a pull_request key are PRs, not issues
            return json.dumps([
                {"number": 9, "title": "real issue"},
                {"number": 10, "title": "a PR", "pull_request": {"url": "x"}},
            ])

        out = dedupe.fetch_open_issues("AaronLPS/loop-builder", runner=runner)
        self.assertEqual(out, [{"number": 9, "title": "real issue"}])

    def test_fetch_returns_empty_on_total_failure(self):
        def boom(cmd):
            raise RuntimeError("offline")

        self.assertEqual(dedupe.fetch_open_issues("AaronLPS/loop-builder", runner=boom), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 scripts/tests/feedback/test_dedupe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dedupe'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/feedback/dedupe.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 scripts/tests/feedback/test_dedupe.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/feedback/dedupe.py scripts/tests/feedback/test_dedupe.py
git commit -m "feat(feedback): live-issue dedupe with graceful fallback

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: file_issue — create as the user (gh else URL)

**Files:**
- Create: `scripts/feedback/file_issue.py`
- Test: `scripts/tests/feedback/test_file_issue.py`

**Interfaces:**
- Produces:
  - `build_url(repo, title, body, labels) -> str`
  - `build_gh_command(repo, title, body_file, labels) -> list[str]`
  - `gh_available(runner=None) -> bool`
  - `create(repo, title, body, labels, *, dry_run=False, gh_check=None, gh_runner=None, url_opener=None) -> dict` — returns `{"method": "gh"|"url", "issue": int|None, "url": str|None, "command": list|None, "truncated": bool}`.
- Constant: `URL_LIMIT = 8000`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/feedback/test_file_issue.py
import sys, pathlib, urllib.parse, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "feedback"))
import file_issue  # noqa: E402

REPO = "AaronLPS/loop-builder"


class FileIssueTest(unittest.TestCase):
    def test_build_url_encodes_params(self):
        url = file_issue.build_url(REPO, "bug: x&y", "body with spaces", ["bug", "via-feedback-tool"])
        self.assertTrue(url.startswith(f"https://github.com/{REPO}/issues/new?"))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(q["title"], ["bug: x&y"])
        self.assertEqual(q["labels"], ["bug,via-feedback-tool"])

    def test_build_gh_command_shape(self):
        cmd = file_issue.build_gh_command(REPO, "t", "/tmp/body.md", ["bug"])
        self.assertEqual(cmd[:4], ["gh", "issue", "create", "--repo"])
        self.assertIn("--body-file", cmd)
        self.assertIn("--label", cmd)

    def test_create_dry_run_gh_path(self):
        out = file_issue.create(REPO, "t", "b", ["bug"], dry_run=True, gh_check=lambda: True)
        self.assertEqual(out["method"], "gh")
        self.assertIsNone(out["issue"])
        self.assertEqual(out["command"][:3], ["gh", "issue", "create"])

    def test_create_dry_run_url_path_when_no_gh(self):
        out = file_issue.create(REPO, "t", "b", ["bug"], dry_run=True, gh_check=lambda: False)
        self.assertEqual(out["method"], "url")
        self.assertIn("/issues/new?", out["url"])

    def test_url_path_truncates_oversized_body(self):
        big = "x" * 20000
        out = file_issue.create(REPO, "t", big, [], dry_run=True, gh_check=lambda: False)
        self.assertTrue(out["truncated"])
        self.assertLessEqual(len(out["url"]), file_issue.URL_LIMIT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 scripts/tests/feedback/test_file_issue.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'file_issue'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/feedback/file_issue.py
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
                "command": build_gh_command(repo, title, body_file, labels), "truncated": False}

    # URL fallback (user submits as themselves in their logged-in browser).
    url = build_url(repo, title, body, labels)
    truncated = False
    if len(url) > URL_LIMIT:
        overhead = len(build_url(repo, title, "", labels))
        room = max(URL_LIMIT - overhead - 200, 0)
        short = body[:room] + "\n\n(truncated — full body printed in terminal)"
        url = build_url(repo, title, short, labels)
        truncated = True
    if not dry_run:
        (url_opener or webbrowser.open)(url)
    return {"method": "url", "issue": None, "url": url, "command": None, "truncated": truncated}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 scripts/tests/feedback/test_file_issue.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/feedback/file_issue.py scripts/tests/feedback/test_file_issue.py
git commit -m "feat(feedback): file issue as the user (gh else prefilled URL)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: CLI — subcommands wiring the modules together

**Files:**
- Create: `scripts/feedback/cli.py`
- Test: `scripts/tests/feedback/test_cli.py`

**Interfaces:**
- Consumes: `feedback_log`, `sanitize`, `dedupe`, `file_issue`.
- Produces a CLI with subcommands (each prints JSON to stdout, exit 0 on success):
  - `append --category C --text T [--source S]`
  - `list-open`
  - `mark-filed --ids a,b --issue N`
  - `sanitize` (reads body on stdin, prints `{"text":..., "notes":[...]}`)
  - `dedupe --repo R --title T` (prints ranked candidates)
  - `file --repo R --title T --labels l1,l2 [--dry-run]` (reads body on stdin; never auto-confirms — the caller is responsible for the consent gate)
- Entry: `main(argv: list[str]) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/feedback/test_cli.py
import os, sys, io, json, pathlib, tempfile, contextlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "feedback"))
import cli  # noqa: E402


def run(argv, stdin=""):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        with contextlib.redirect_stdin(io.StringIO(stdin)) if stdin else contextlib.nullcontext():
            code = cli.main(argv)
    return code, out.getvalue()


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        os.environ["LOOP_BUILDER_FEEDBACK_FILE"] = self.tmp.name

    def tearDown(self):
        os.unlink(self.tmp.name)
        os.environ.pop("LOOP_BUILDER_FEEDBACK_FILE", None)

    def test_append_then_list_open(self):
        code, _ = run(["append", "--category", "bug", "--text", "boom"])
        self.assertEqual(code, 0)
        code, out = run(["list-open"])
        self.assertEqual(code, 0)
        items = json.loads(out)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["text"], "boom")

    def test_sanitize_subcommand(self):
        # path built from fragments; key is the documented AWS sample value
        sample = "/home/" + "someuser" + "/x"
        code, out = run(["sanitize"], stdin="path " + sample + " and key AKIAIOSFODNN7EXAMPLE")
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertNotIn("someuser", res["text"])
        self.assertIn("secret", res["notes"])

    def test_file_dry_run_does_not_create(self):
        code, out = run(["file", "--repo", "AaronLPS/loop-builder", "--title", "t",
                         "--labels", "bug", "--dry-run"], stdin="body")
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertIn(res["method"], ("gh", "url"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 scripts/tests/feedback/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/feedback/cli.py
"""Command-line surface over the feedback modules, called by the
loop-builder-feedback playbook. Each subcommand prints JSON to stdout.

This CLI never confirms a filing on the user's behalf: `file` just performs the
action it is told to. The mandatory consent gate lives in the orchestrating
skill (see references/feedback-to-issue.md).
"""
from __future__ import annotations

import argparse
import json
import sys

import dedupe
import feedback_log
import file_issue
import sanitize as sanitize_mod


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="feedback")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append")
    a.add_argument("--category", required=True)
    a.add_argument("--text", required=True)
    a.add_argument("--source", default="loop-builder")

    sub.add_parser("list-open")

    m = sub.add_parser("mark-filed")
    m.add_argument("--ids", required=True)
    m.add_argument("--issue", required=True, type=int)

    sub.add_parser("sanitize")

    d = sub.add_parser("dedupe")
    d.add_argument("--repo", required=True)
    d.add_argument("--title", required=True)

    f = sub.add_parser("file")
    f.add_argument("--repo", required=True)
    f.add_argument("--title", required=True)
    f.add_argument("--labels", default="")
    f.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "append":
        entry = feedback_log.append(args.category, args.text, source=args.source)
        print(json.dumps(entry, ensure_ascii=False))
    elif args.cmd == "list-open":
        print(json.dumps(feedback_log.list_open(), ensure_ascii=False))
    elif args.cmd == "mark-filed":
        n = feedback_log.mark_filed(args.ids.split(","), args.issue)
        print(json.dumps({"updated": n}))
    elif args.cmd == "sanitize":
        text, notes = sanitize_mod.sanitize(sys.stdin.read())
        print(json.dumps({"text": text, "notes": notes}, ensure_ascii=False))
    elif args.cmd == "dedupe":
        issues = dedupe.fetch_open_issues(args.repo)
        print(json.dumps(dedupe.match(args.title, issues), ensure_ascii=False))
    elif args.cmd == "file":
        labels = [x for x in args.labels.split(",") if x]
        res = file_issue.create(args.repo, args.title, sys.stdin.read(), labels,
                                dry_run=args.dry_run)
        print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 scripts/tests/feedback/test_cli.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/feedback/cli.py scripts/tests/feedback/test_cli.py
git commit -m "feat(feedback): CLI subcommands over the feedback modules

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Test harness + CI wiring

**Files:**
- Create: `scripts/tests/test_feedback.sh`
- Modify: `.github/workflows/tests.yml` (add a step after "Evals parse")

**Interfaces:**
- Consumes: all `scripts/tests/feedback/test_*.py`.
- Produces: a red-green bash harness (exit 0 == all python unit tests pass) wired into CI.

- [ ] **Step 1: Write the harness**

```bash
# scripts/tests/test_feedback.sh
#!/usr/bin/env bash
# Runs the feedback module unit tests (python3 stdlib only).
# Red-green contract: exit 0 == all pass. Run: bash scripts/tests/test_feedback.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"
python3 -m unittest discover -s scripts/tests/feedback -p 'test_*.py' -v
```

- [ ] **Step 2: Run the harness to verify green**

Run: `bash scripts/tests/test_feedback.sh`
Expected: `OK` with all tests from Tasks 1-5 passing, exit 0.

- [ ] **Step 3: Wire into CI**

Add this step to `.github/workflows/tests.yml` immediately after the existing `Evals parse` step (same indentation, inside `jobs.tests.steps`):

```yaml
      - name: Feedback module tests
        run: bash scripts/tests/test_feedback.sh
```

- [ ] **Step 4: Verify the workflow still parses**

Run: `python3 -c "import json,sys; print('yaml step added')"` then visually confirm indentation; optionally `git diff .github/workflows/tests.yml`.
Expected: the new step sits under `steps:` at the same level as the others.

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test_feedback.sh .github/workflows/tests.yml
git commit -m "test(feedback): bash harness + CI step for feedback unit tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Skill integration — playbook + SKILL.md hooks

**Files:**
- Create: `references/feedback-to-issue.md`
- Modify: `SKILL.md` (add a "Collecting feedback and reporting bugs" section; add the opt-in question to the scaffolding flow)

**Interfaces:**
- Consumes: the `scripts/feedback/cli.py` subcommands (`append`, `list-open`, `dedupe`, `sanitize`, `file`, `mark-filed`).
- Produces: the human-facing orchestration — passive capture instruction, the review→summarize→dedupe→sanitize→**consent**→file flow, and the generated-loop opt-in hook snippet.

- [ ] **Step 1: Write the playbook reference**

Create `references/feedback-to-issue.md` containing, in prose (no emoji):

1. **Purpose & guarantees** — issues are filed under the *user's* account; nothing is auto-filed; every draft is sanitized and shown before filing.
2. **Passive capture** — when loop-builder hits an error or the user is clearly blocked, append a quiet entry:
   `python3 scripts/feedback/cli.py append --category bug --text "<what broke + brief context>"`
   (use `--source <loop-name>` for a generated loop's own report).
3. **Review & file flow** (triggered by the user asking to report feedback/a bug, or to "review feedback"):
   - `list-open` to load the backlog.
   - Cluster entries into one or more candidate issues; draft title + body (what happened, repro/context, environment).
   - `dedupe --repo AaronLPS/loop-builder --title "<draft title>"`; if a strong match, offer to upvote/comment on that issue instead.
   - Pipe the draft body through `sanitize`; surface any `notes` (local-path/secret/email) to the user.
   - **Consent gate (mandatory):** show the full sanitized title + body + labels + "this will be filed on AaronLPS/loop-builder as YOUR GitHub account" and get explicit yes. Never skip this.
   - On yes: `file --repo AaronLPS/loop-builder --title "<t>" --labels via-feedback-tool,<category>` with the body on stdin. If `method == "url"`, tell the user to submit in the opened browser; if `method == "gh"`, report the created issue number.
   - On success, `mark-filed --ids <ids> --issue <N>`.
4. **Generated-loop opt-in hook** — the exact snippet a scaffolded loop adds to its verifier/wrapper to append its own failures locally:

```bash
# loop self-report (local only; review/file later with loop-builder feedback)
python3 "$LOOP_BUILDER_SCRIPTS/cli.py" append --category bug \
  --source "<loop-name>" --text "verifier failed: $(tail -n 3 "$VERIFIER_LOG")" || true
```

- [ ] **Step 2: Add the SKILL.md section**

Append a concise section to `SKILL.md` (keep total under 500 lines) titled `## Collecting feedback and reporting bugs` that: (a) states feedback/bugs are captured locally and filed under the user's own account; (b) instructs passive capture via `scripts/feedback/cli.py append` on errors; (c) routes the full flow to `references/feedback-to-issue.md` (load it only when the user wants to review/file); (d) adds, to the loop-scaffolding step, the question: "Add self-reporting to this loop? (logs its own errors locally for you to review later — never auto-files)".

- [ ] **Step 3: Verify docs constraints**

Run:
```bash
test "$(wc -l < SKILL.md)" -lt 500 && echo "SKILL.md under 500: OK"
! grep -nP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]' SKILL.md references/feedback-to-issue.md && echo "no emoji: OK"
test -f references/feedback-to-issue.md && echo "reference exists: OK"
```
Expected: all three `OK` lines.

- [ ] **Step 4: Verify the passive-capture command is real**

Run: `python3 scripts/feedback/cli.py append --category bug --text "plan smoke test" --source selftest && LOOP_BUILDER_FEEDBACK_FILE=/tmp/none python3 scripts/feedback/cli.py list-open`
Expected: append prints an entry JSON; the command referenced in the docs exists and runs. (Clean up `~/.loop-builder/feedback.jsonl` test line afterward.)

- [ ] **Step 5: Commit**

```bash
git add references/feedback-to-issue.md SKILL.md
git commit -m "docs(skill): wire feedback-to-issue capture + filing flow

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: GitHub issue forms

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feedback.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`

**Interfaces:**
- Produces: structured issue forms so browser-URL, gh, and manual submissions are consistent. Labels match those used by `cli.py file`: `bug`/`feedback` plus `via-feedback-tool`.

- [ ] **Step 1: Write the bug form**

```yaml
# .github/ISSUE_TEMPLATE/bug_report.yml
name: Bug report
description: Something in loop-builder or a loop it generated misbehaved
labels: ["bug"]
body:
  - type: textarea
    id: what-happened
    attributes:
      label: What happened
      description: What broke, and what you expected instead.
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Steps / context
      description: How to reproduce, plus relevant context. Please remove any private paths or secrets.
  - type: input
    id: env
    attributes:
      label: Environment
      description: Claude Code version, OS, loop-builder version if known.
```

- [ ] **Step 2: Write the feedback form**

```yaml
# .github/ISSUE_TEMPLATE/feedback.yml
name: Feedback / idea
description: A suggestion, feature request, or general feedback
labels: ["feedback"]
body:
  - type: textarea
    id: feedback
    attributes:
      label: Your feedback
      description: What would make loop-builder better?
    validations:
      required: true
```

- [ ] **Step 3: Write the chooser config**

```yaml
# .github/ISSUE_TEMPLATE/config.yml
blank_issues_enabled: true
```

- [ ] **Step 4: Validate without PyYAML (CI has no yaml module)**

Run:
```bash
for f in .github/ISSUE_TEMPLATE/bug_report.yml .github/ISSUE_TEMPLATE/feedback.yml .github/ISSUE_TEMPLATE/config.yml; do
  test -f "$f" && grep -q . "$f" && echo "OK: $f"
done
grep -q 'labels: \["bug"\]' .github/ISSUE_TEMPLATE/bug_report.yml && echo "bug label OK"
```
Expected: three `OK:` lines and `bug label OK`. (GitHub itself validates issue-form schema on push; do not add a PyYAML dependency.)

- [ ] **Step 5: Commit**

```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "feat(feedback): GitHub issue forms for bug + feedback

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes for the implementer

- **Deviation from spec wording, same intent:** the spec calls the orchestration a "companion skill (`/loop-builder-feedback`)". Because this repo ships as a *single* skill installed at `~/.claude/skills/loop-builder/`, a separately-registered slash command does not fit cleanly. The plan instead implements the orchestration as a `references/feedback-to-issue.md` playbook loaded by `SKILL.md` (progressive disclosure, per `AGENTS.md`). Same user-visible capability: the user asks to report a bug / review feedback and the flow runs. Flag this to the maintainer before opening the PR.
- After all tasks, open a PR from `feature/feedback-to-issue` (do not push to `main`; required `tests` check + branch protection). The new `secret-scan` and `tests` checks must pass.

## Self-Review

- **Spec coverage:** log (Task 1), sanitize (Task 2), dedupe (Task 3), file-issue gh/URL (Task 4), CLI orchestration surface (Task 5), passive + explicit capture and consent gate (Tasks 5/7), generated-loop opt-in hook (Task 7), issue forms + labels (Task 8), tests + CI (Task 6, plus per-task tests). Online-only dedupe and python3-stdlib decisions honored. The "companion skill" wording is addressed in Notes.
- **Placeholder scan:** every code step shows complete code; no TBD/TODO; doc-only steps (Task 7 SKILL.md section, playbook prose) specify exact required content and verifiable checks.
- **Type consistency:** entry dict shape (`id/ts/source/category/text/context/status/issue/schema`) is consistent across Tasks 1/5; `create()` return dict (`method/issue/url/command/truncated`) consistent across Tasks 4/5; CLI consumes only the signatures declared in Tasks 1-4.
