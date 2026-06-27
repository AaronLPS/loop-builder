# loop-distiller scanning loop — Phase 2a (deterministic substrate) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic, fully-unit-tested memory substrate for the machine-wide scanning loop — transcript enumeration, the high-recall signature/blocking key, the digest index, the candidate ledger, and the separate verifier — with no LLM involved.

**Architecture:** Five deterministic `python3` modules under `skills/loop-distiller/scripts/distiller/` (plus the verifier), reusing the Phase 1 kernel (`parse`/`condense`). Tier 1 (digest) reads each transcript once and appends a compact digest to `~/.loop-builder/digests.jsonl`; the signature module provides the coarse high-recall blocking key; the ledger curates candidates in `~/.loop-builder/scan-ledger.jsonl` with signature+status dedup; `verify_scan` is the separate deterministic check. The LLM cluster/label step and the review UX are Phase 2b — out of scope here.

**Tech Stack:** `python3` stdlib only (`json`, `os`, `pathlib`, `uuid`, `unittest`); existing `test_loop_distiller.sh` runner (auto-discovers `test_*.py`); markdown.

## Global Constraints

- **Python stdlib only**; deterministic and red-green (TDD) tested under `skills/loop-distiller/scripts/tests/`. (AGENTS.md / Phase 1 precedent)
- **Env-overridable paths** following the `feedback_log` precedent: every home-relative path has a `LOOP_DISTILLER_*` env override so tests never touch the real `~/.loop-builder` or `~/.claude`.
- **Machine-global state** lives under `~/.loop-builder/` (alongside `feedback-to-issue`'s `feedback.jsonl`) — never in a project's `loops/` dir.
- **Determinism is lossless structuring, never the quality gate.** The signature is a high-recall *blocking key*; the pre-pass drops only size-1 families (bar **below** threshold N). No semantic keep/discard judgment lives in these modules — that is Phase 2b's LLM step.
- **No mutable state in any `SKILL.md`** (not touched in 2a, but the rule stands).
- **No `/home/<user>/` or `/Users/<user>/` literal absolute paths** anywhere (privacy pre-commit gate); use `~`, `pathlib.Path.home()`, or neutral `/work/...` test paths.
- **Commit trailer:** every commit ends with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Work lands on `feature/loop-distiller-scan`.
- The transcript path scheme (`~/.claude/projects/*/`) and JSONL schema are **observed Claude Code conventions** — keep code comments flagging "verify against current docs"; do not present them as guaranteed APIs.

## File Structure

| Path | Responsibility | Form |
| --- | --- | --- |
| `skills/loop-distiller/scripts/distiller/transcript_reader.py` (extend) | add `fingerprint()` + `list_transcripts()` (machine-wide); honor a projects-root env override | deterministic |
| `skills/loop-distiller/scripts/distiller/signature.py` (new) | `signature()` coarse blocking key + `group_by_signature()` + `drop_singletons()` | deterministic |
| `skills/loop-distiller/scripts/distiller/digest_store.py` (new) | `digest()` one transcript; append/read the digest index; watermark via fingerprints | deterministic |
| `skills/loop-distiller/scripts/distiller/ledger.py` (new) | candidate `upsert`/`read_all`/`mark`; dedup by signature+status | deterministic |
| `skills/loop-distiller/scripts/distiller/verify_scan.py` (new) | separate verifier: each active candidate clears ≥N recurrences and ≥K blocks | deterministic verifier |
| `skills/loop-distiller/scripts/tests/test_*.py` (new, one per module) | red-green unit tests; auto-discovered by the existing runner | unittest |
| `skills/loop-distiller/scripts/tests/fixtures/` (extend) | extra fixture transcripts for digest tests | test data |

**Module API (locked here so every task agrees on names/types):**

```python
# transcript_reader.py — ADDITIONS (Phase 1 surface unchanged)
PROJECTS_ROOT_ENV = "LOOP_DISTILLER_PROJECTS_ROOT"   # overrides ~/.claude/projects
def fingerprint(path) -> str: ...                    # f"{path}|{st_mtime_ns}|{st_size}"
def list_transcripts(projects_root=None) -> list[pathlib.Path]: ...
    # sorted glob of <projects_root>/*/*.jsonl ; default root = _projects_root()

# signature.py
def signature(condensed: dict) -> str: ...
    # coarse high-recall key: "<sorted nonempty block names>|<sorted verb set>"
def _verb(ref: dict) -> str: ...                     # Bash -> first cmd token; else tool.lower()
def group_by_signature(digests: list[dict]) -> dict: ...   # {sig: [digest,...]}, digest has "signature"
def drop_singletons(groups: dict) -> dict: ...       # remove families with < 2 members

# digest_store.py
DIGESTS_FILE_ENV = "LOOP_DISTILLER_DIGESTS_FILE"     # default ~/.loop-builder/digests.jsonl
def digests_path() -> "pathlib.Path": ...
def digest(path) -> dict: ...                        # builds one digest record (shape below)
def append(d: dict) -> None: ...
def read_all() -> list[dict]: ...
def seen_fingerprints() -> set: ...                  # watermark
def digest_new(paths: list) -> list[dict]: ...       # digest+append only unseen; return new

# ledger.py
LEDGER_FILE_ENV = "LOOP_DISTILLER_LEDGER_FILE"       # default ~/.loop-builder/scan-ledger.jsonl
def ledger_path() -> "pathlib.Path": ...
def upsert(signature: str, label: str, projects: list, evidence: list,
           blocks: list, ts: int) -> dict: ...       # dedup by signature+status
def read_all() -> list[dict]: ...
def mark(candidate_id: str, status: str) -> dict: ...

# verify_scan.py
DEFAULT_N = 3   # min recurrences (distinct evidence sessions)
DEFAULT_K = 4   # min distinct blocks
def verify(candidates: list[dict], n: int = DEFAULT_N, k: int = DEFAULT_K) -> tuple: ...
    # returns (ok: bool, problems: list[str]); only "new"/"surfaced" candidates are checked
```

**Digest record** (one per transcript): `{"fingerprint","project","path","ts","signature","blocks":[...],"commands":[...],"schema":1}`.

**Candidate record** (one per recurring pattern): `{"id","signature","label","count","projects":[...],"first_seen","last_seen","evidence":[fingerprint,...],"blocks":[...],"status":"new|surfaced|dismissed|built","schema":1}`. (`blocks` is added vs. the spec's shape so the verifier can check ≥K; `count` = number of distinct `evidence` fingerprints.)

---

### Task 1: `transcript_reader` — `fingerprint()` + `list_transcripts()`

**Files:**
- Modify: `skills/loop-distiller/scripts/distiller/transcript_reader.py`
- Modify: `skills/loop-distiller/scripts/tests/test_transcript_reader.py`

**Interfaces:**
- Consumes: existing `_projects_root()`.
- Produces: `PROJECTS_ROOT_ENV`, `fingerprint(path) -> str`, `list_transcripts(projects_root=None) -> list[pathlib.Path]`.

- [ ] **Step 1: Write the failing tests (append to the existing test file)**

```python
class ListAndFingerprintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        os.environ.pop(tr.PROJECTS_ROOT_ENV, None)

    def tearDown(self):
        os.environ.pop(tr.PROJECTS_ROOT_ENV, None)
        self.tmp.cleanup()

    def test_fingerprint_is_stable_and_path_sensitive(self):
        f = self.root / "a.jsonl"; f.write_text("{}\n", encoding="utf-8")
        fp1 = tr.fingerprint(f)
        self.assertEqual(fp1, tr.fingerprint(f))           # stable
        self.assertIn(str(f), fp1)                          # path-sensitive
        other = self.root / "b.jsonl"; other.write_text("{}\n", encoding="utf-8")
        self.assertNotEqual(fp1, tr.fingerprint(other))     # different file -> different fp

    def test_list_transcripts_globs_all_projects_sorted(self):
        (self.root / "proj-one").mkdir(); (self.root / "proj-two").mkdir()
        a = self.root / "proj-one" / "s1.jsonl"; a.write_text("{}\n", encoding="utf-8")
        b = self.root / "proj-two" / "s2.jsonl"; b.write_text("{}\n", encoding="utf-8")
        (self.root / "proj-one" / "notes.txt").write_text("x", encoding="utf-8")  # ignored
        os.environ[tr.PROJECTS_ROOT_ENV] = str(self.root)
        got = tr.list_transcripts()
        self.assertEqual(got, sorted([a, b]))               # only .jsonl, sorted

    def test_list_transcripts_empty_root_returns_empty(self):
        os.environ[tr.PROJECTS_ROOT_ENV] = str(self.root)
        self.assertEqual(tr.list_transcripts(), [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader.ListAndFingerprintTest`
Expected: FAIL — `AttributeError: module 'transcript_reader' has no attribute 'fingerprint'`.

- [ ] **Step 3: Write minimal implementation**

In `transcript_reader.py`, add the env constant near the others, make `_projects_root()` honor it, and add the two functions:

```python
PROJECTS_ROOT_ENV = "LOOP_DISTILLER_PROJECTS_ROOT"
```

Replace the existing `_projects_root` with:

```python
def _projects_root() -> pathlib.Path:
    override = os.environ.get(PROJECTS_ROOT_ENV)
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".claude" / "projects"
```

Then add:

```python
def fingerprint(path) -> str:
    st = pathlib.Path(path).stat()
    return f"{path}|{st.st_mtime_ns}|{st.st_size}"


def list_transcripts(projects_root=None) -> list:
    root = pathlib.Path(projects_root) if projects_root else _projects_root()
    if not root.is_dir():
        return []
    return sorted(root.glob("*/*.jsonl"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader`
Expected: PASS (all prior Phase 1 tests + the 3 new ones; the `LocateTest` cases that rely on `_projects_root` still pass because they set `TRANSCRIPT_DIR_ENV`/`TRANSCRIPT_FILE_ENV`, which take precedence).

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/transcript_reader.py \
        skills/loop-distiller/scripts/tests/test_transcript_reader.py
git commit -m "$(printf 'feat(loop-distiller): machine-wide list_transcripts + fingerprint\n\nProjects-root env override for testability; fingerprint = path|mtime_ns|size.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: `signature.py` — the high-recall blocking key

**Files:**
- Create: `skills/loop-distiller/scripts/distiller/signature.py`
- Create: `skills/loop-distiller/scripts/tests/test_signature.py`

**Interfaces:**
- Consumes: a `condense()`-shaped dict (`{"discovery":[ref],"action":[ref],"verify":[ref],"vcs":[ref],"counts":{...}}`, `ref={"i","tool","hint"}`); and digest dicts carrying a `"signature"` key.
- Produces: `signature(condensed) -> str`, `group_by_signature(digests) -> dict`, `drop_singletons(groups) -> dict`.

- [ ] **Step 1: Write the failing tests**

```python
# skills/loop-distiller/scripts/tests/test_signature.py
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import signature as sig  # noqa: E402


def _cond(discovery=(), action=(), verify=(), vcs=()):
    b = {"discovery": list(discovery), "action": list(action),
         "verify": list(verify), "vcs": list(vcs)}
    b["counts"] = {k: len(v) for k, v in b.items()}
    return b


def _ref(tool, hint):
    return {"i": 0, "tool": tool, "hint": hint}


class SignatureTest(unittest.TestCase):
    def test_same_workflow_surface_variation_same_signature(self):
        a = _cond(discovery=[_ref("Bash", "gh issue list --label P1")],
                  action=[_ref("Bash", "gh issue edit 41 --add-assignee me")],
                  verify=[_ref("Bash", "pytest -q")])
        b = _cond(discovery=[_ref("Bash", "gh issue list --label bug --limit 50")],
                  action=[_ref("Bash", "gh issue edit 99 --add-assignee you")],
                  verify=[_ref("Bash", "pytest tests/ -x")])
        self.assertEqual(sig.signature(a), sig.signature(b))   # high recall: args/order ignored

    def test_different_tools_different_signature(self):
        a = _cond(action=[_ref("Bash", "gh issue edit 1")])
        b = _cond(action=[_ref("Edit", "/work/x.py")])
        self.assertNotEqual(sig.signature(a), sig.signature(b))

    def test_signature_ignores_empty_blocks(self):
        a = _cond(action=[_ref("Bash", "gh x")])
        self.assertNotIn("discovery", sig.signature(a))

    def test_group_and_drop_singletons(self):
        digests = [{"signature": "s1"}, {"signature": "s1"}, {"signature": "s2"}]
        groups = sig.group_by_signature(digests)
        self.assertEqual(len(groups["s1"]), 2)
        kept = sig.drop_singletons(groups)
        self.assertIn("s1", kept)        # family of 2 survives
        self.assertNotIn("s2", kept)     # singleton dropped (bar < threshold N)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_signature`
Expected: FAIL — `ModuleNotFoundError: No module named 'signature'`.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/loop-distiller/scripts/distiller/signature.py
"""Coarse, high-recall blocking key over a condense()-shaped dict.

This is NOT a semantic judgment — it only groups likely-related sessions cheaply
so the (Phase 2b) LLM clustering is batchable. Tuned to OVER-group: surface
variation in command args/order must not change the key. The keep/discard call
belongs to the LLM, never here.
"""
from __future__ import annotations

_BUCKETS = ("discovery", "action", "verify", "vcs")


def _verb(ref: dict) -> str:
    tool = ref.get("tool") or ""
    if tool == "Bash":
        toks = (ref.get("hint") or "").split()
        return toks[0].lower() if toks else "bash"
    return tool.lower()


def signature(condensed: dict) -> str:
    counts = condensed.get("counts", {})
    blocks = tuple(b for b in _BUCKETS if counts.get(b, 0) > 0)
    verbs = set()
    for b in _BUCKETS:
        for ref in condensed.get(b, []):
            v = _verb(ref)
            if v:
                verbs.add(v)
    return f"{','.join(blocks)}|{','.join(sorted(verbs))}"


def group_by_signature(digests: list) -> dict:
    groups: dict = {}
    for d in digests:
        groups.setdefault(d["signature"], []).append(d)
    return groups


def drop_singletons(groups: dict) -> dict:
    # Drop only size-1 families. The candidate threshold N (>=3) is applied later
    # by verify_scan; this bar sits deliberately below N so determinism stays
    # conservative and the LLM/threshold make the real call.
    return {sig_key: members for sig_key, members in groups.items() if len(members) >= 2}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_signature`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/signature.py \
        skills/loop-distiller/scripts/tests/test_signature.py
git commit -m "$(printf 'feat(loop-distiller): high-recall signature blocking key\n\nOver-groups by block profile + tool/verb vocabulary; drop_singletons removes\nonly size-1 families (bar below threshold N). LLM owns keep/discard.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 3: `digest_store.py` — Tier 1 digest index

**Files:**
- Create: `skills/loop-distiller/scripts/distiller/digest_store.py`
- Create: `skills/loop-distiller/scripts/tests/test_digest_store.py`
- Create: `skills/loop-distiller/scripts/tests/fixtures/session_b.jsonl`

**Interfaces:**
- Consumes: `transcript_reader.parse`/`condense`/`fingerprint`; `signature.signature`.
- Produces: `digests_path`, `digest(path) -> dict`, `append`, `read_all`, `seen_fingerprints`, `digest_new(paths) -> list[dict]`, `DIGESTS_FILE_ENV`.

- [ ] **Step 1: Add a second fixture transcript** (distinct from Phase 1's `session.jsonl`)

```jsonl
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"deploy the docs site"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"npm run build"}}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"git push origin gh-pages"}}]}}
```

- [ ] **Step 2: Write the failing tests**

```python
# skills/loop-distiller/scripts/tests/test_digest_store.py
import os, sys, json, pathlib, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "distiller"))
import digest_store as ds  # noqa: E402

FIX = HERE / "fixtures" / "session.jsonl"          # Phase 1 fixture (gh + pytest)


class DigestStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = pathlib.Path(self.tmp.name) / "digests.jsonl"
        os.environ[ds.DIGESTS_FILE_ENV] = str(self.file)

    def tearDown(self):
        os.environ.pop(ds.DIGESTS_FILE_ENV, None)
        self.tmp.cleanup()

    def test_digest_builds_record_with_signature_and_blocks(self):
        d = ds.digest(FIX)
        self.assertIn("signature", d)
        self.assertIn("action", d["blocks"])
        self.assertIn(str(FIX), d["fingerprint"])             # fingerprint embeds the path
        self.assertEqual(d["project"], FIX.parent.name)       # project = parent dir name
        self.assertEqual(d["schema"], 1)

    def test_append_then_read_roundtrip(self):
        d = ds.digest(FIX); ds.append(d)
        got = ds.read_all()
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["signature"], d["signature"])

    def test_seen_fingerprints_is_the_watermark(self):
        d = ds.digest(FIX); ds.append(d)
        self.assertIn(d["fingerprint"], ds.seen_fingerprints())

    def test_digest_new_skips_already_seen(self):
        first = ds.digest_new([FIX])
        self.assertEqual(len(first), 1)
        second = ds.digest_new([FIX])          # same file, already digested
        self.assertEqual(second, [])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_digest_store`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest_store'`.

- [ ] **Step 4: Write minimal implementation**

```python
# skills/loop-distiller/scripts/distiller/digest_store.py
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_digest_store`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/digest_store.py \
        skills/loop-distiller/scripts/tests/test_digest_store.py \
        skills/loop-distiller/scripts/tests/fixtures/session_b.jsonl
git commit -m "$(printf 'feat(loop-distiller): Tier 1 digest index with fingerprint watermark\n\nReads each transcript once; digest_new skips already-seen fingerprints.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 4: `ledger.py` — Tier 3 candidate ledger

**Files:**
- Create: `skills/loop-distiller/scripts/distiller/ledger.py`
- Create: `skills/loop-distiller/scripts/tests/test_ledger.py`

**Interfaces:**
- Consumes: nothing (pure store).
- Produces: `ledger_path`, `upsert(signature,label,projects,evidence,blocks,ts) -> dict`, `read_all`, `mark(id,status) -> dict`, `LEDGER_FILE_ENV`.

- [ ] **Step 1: Write the failing tests**

```python
# skills/loop-distiller/scripts/tests/test_ledger.py
import os, sys, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import ledger  # noqa: E402


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ[ledger.LEDGER_FILE_ENV] = str(pathlib.Path(self.tmp.name) / "l.jsonl")

    def tearDown(self):
        os.environ.pop(ledger.LEDGER_FILE_ENV, None)
        self.tmp.cleanup()

    def test_new_candidate_starts_new_with_count_from_evidence(self):
        c = ledger.upsert("sigA", "triage", ["repo1"], ["fp1", "fp2"], ["discovery", "action"], 100)
        self.assertEqual(c["status"], "new")
        self.assertEqual(c["count"], 2)
        self.assertEqual(sorted(c["evidence"]), ["fp1", "fp2"])

    def test_upsert_same_signature_merges_evidence_and_count(self):
        ledger.upsert("sigA", "triage", ["repo1"], ["fp1"], ["action"], 100)
        c = ledger.upsert("sigA", "triage", ["repo2"], ["fp1", "fp3"], ["verify"], 200)
        self.assertEqual(c["count"], 2)                       # fp1 + fp3 distinct
        self.assertEqual(sorted(c["projects"]), ["repo1", "repo2"])
        self.assertEqual(c["last_seen"], 200)
        self.assertIn("verify", c["blocks"])
        self.assertEqual(len(ledger.read_all()), 1)           # still one candidate

    def test_dismissed_signature_does_not_resurrect(self):
        c = ledger.upsert("sigA", "triage", ["repo1"], ["fp1"], ["action"], 100)
        ledger.mark(c["id"], "dismissed")
        again = ledger.upsert("sigA", "triage", ["repo1"], ["fp9"], ["action"], 300)
        self.assertEqual(again["status"], "dismissed")        # not reactivated
        self.assertNotIn("fp9", again["evidence"])            # no new evidence added

    def test_mark_changes_status(self):
        c = ledger.upsert("sigA", "triage", ["repo1"], ["fp1"], ["action"], 100)
        self.assertEqual(ledger.mark(c["id"], "built")["status"], "built")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_ledger`
Expected: FAIL — `ModuleNotFoundError: No module named 'ledger'`.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/loop-distiller/scripts/distiller/ledger.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_ledger`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/ledger.py \
        skills/loop-distiller/scripts/tests/test_ledger.py
git commit -m "$(printf 'feat(loop-distiller): Tier 3 candidate ledger with signature+status dedup\n\nupsert merges evidence/count; dismissed/built signatures never resurrect.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 5: `verify_scan.py` — the separate deterministic verifier

**Files:**
- Create: `skills/loop-distiller/scripts/distiller/verify_scan.py`
- Create: `skills/loop-distiller/scripts/tests/test_verify_scan.py`

**Interfaces:**
- Consumes: candidate records (the `ledger.py` shape).
- Produces: `DEFAULT_N`, `DEFAULT_K`, `verify(candidates, n=DEFAULT_N, k=DEFAULT_K) -> (ok, problems)`.

- [ ] **Step 1: Write the failing tests**

```python
# skills/loop-distiller/scripts/tests/test_verify_scan.py
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import verify_scan as vs  # noqa: E402


def _cand(status="surfaced", count=3, blocks=("discovery", "action", "verify", "vcs"), sig="s"):
    return {"id": "x", "signature": sig, "status": status,
            "count": count, "blocks": list(blocks)}


class VerifyScanTest(unittest.TestCase):
    def test_passing_candidate_ok(self):
        ok, problems = vs.verify([_cand()])
        self.assertTrue(ok)
        self.assertEqual(problems, [])

    def test_too_few_recurrences_fails(self):
        ok, problems = vs.verify([_cand(count=2)])   # < DEFAULT_N (3)
        self.assertFalse(ok)
        self.assertTrue(any("recurrence" in p for p in problems))

    def test_too_few_blocks_fails(self):
        ok, problems = vs.verify([_cand(blocks=("discovery", "action"))])  # < DEFAULT_K (4)
        self.assertFalse(ok)
        self.assertTrue(any("block" in p for p in problems))

    def test_terminal_candidates_are_not_checked(self):
        ok, _ = vs.verify([_cand(status="dismissed", count=1, blocks=())])
        self.assertTrue(ok)                          # dismissed/built skipped

    def test_duplicate_active_signatures_flagged(self):
        ok, problems = vs.verify([_cand(sig="dup"), _cand(sig="dup")])
        self.assertFalse(ok)
        self.assertTrue(any("dup" in p.lower() or "duplicate" in p.lower() for p in problems))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_verify_scan`
Expected: FAIL — `ModuleNotFoundError: No module named 'verify_scan'`.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/loop-distiller/scripts/distiller/verify_scan.py
"""Separate deterministic verifier for surfaced scan candidates.

A candidate is sound only if it recurred enough (>= N distinct sessions), spans
enough of the loop blocks (>= K), and active signatures are unique. This is the
maker/checker split: the scan proposes; this program checks. Run standalone to
exit non-zero on any problem.
"""
from __future__ import annotations

import json
import sys

DEFAULT_N = 3
DEFAULT_K = 4
_ACTIVE = ("new", "surfaced")


def verify(candidates: list, n: int = DEFAULT_N, k: int = DEFAULT_K) -> tuple:
    problems = []
    seen_sigs = set()
    for c in candidates:
        if c.get("status") not in _ACTIVE:
            continue
        label = c.get("label") or c.get("id") or c.get("signature")
        if c.get("count", 0) < n:
            problems.append(f"{label}: only {c.get('count', 0)} recurrence(s), need {n}")
        if len(c.get("blocks", [])) < k:
            problems.append(f"{label}: only {len(c.get('blocks', []))} block(s), need {k}")
        sig_key = c.get("signature")
        if sig_key in seen_sigs:
            problems.append(f"{label}: duplicate active signature {sig_key!r}")
        seen_sigs.add(sig_key)
    return (len(problems) == 0, problems)


def _main() -> int:
    # Reads a JSON array of candidates from stdin; exit 0 == all sound.
    candidates = json.load(sys.stdin)
    ok, problems = verify(candidates)
    for p in problems:
        print(f"FAIL: {p}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_verify_scan`
Expected: PASS (5 tests).

- [ ] **Step 5: Run the whole loop-distiller suite to confirm no regressions**

Run: `bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh`
Expected: all tests across `test_transcript_reader`, `test_signature`, `test_digest_store`, `test_ledger`, `test_verify_scan` discovered and green (the runner auto-discovers the new `test_*.py` files — no runner/CI edit needed).

- [ ] **Step 6: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/verify_scan.py \
        skills/loop-distiller/scripts/tests/test_verify_scan.py
git commit -m "$(printf 'feat(loop-distiller): separate deterministic scan verifier\n\nChecks recurrence >= N, block coverage >= K, unique active signatures.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Final verification (after all tasks)

- [ ] Run the full loop-distiller suite: `bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh` → all green (Phase 1 kernel + the five new 2a modules).
- [ ] Run the sibling suites to confirm no regressions: `bash skills/loop-builder/scripts/tests/test_verifiers.sh` and `bash skills/feedback-to-issue/scripts/tests/test_feedback.sh`.
- [ ] Confirm no new mutable state was written into any `SKILL.md` (2a touches none).
- [ ] Confirm CI needs no edit: the `loop-distiller kernel tests` step already runs `test_loop_distiller.sh`, which discovers the new `test_*.py` files.
- [ ] Push `feature/loop-distiller-scan` and open a PR (outward-facing — confirm with the maintainer first, per AGENTS.md).
