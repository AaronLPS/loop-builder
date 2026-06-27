# loop-distiller (Phase 1: engine + Trigger A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new `loop-distiller` peer skill that, on demand, turns the current session's transcript into a pre-filled `loop-builder` blueprint and hands off — with a deterministic, fixture-tested transcript-reading kernel that Phase 2 (Trigger C) will reuse.

**Architecture:** A deterministic `python3` kernel (`transcript_reader`: locate → parse → condense) extracts evidence from a Claude Code session JSONL. The `SKILL.md` body orchestrates Trigger A — run the kernel, apply the seven-block detection rubric (judgment), emit the literal loop-builder fill-in template pre-filled with evidence cites and `UNKNOWN → ASK` blanks, then invoke `loop-builder` unchanged. Deterministic work is red-green tested; skill judgment is eval-tested. Mirrors the existing `feedback-to-issue` split.

**Tech Stack:** `python3` stdlib only (`json`, `pathlib`, `os`, `unittest`); bash test runner; markdown skill + references; `loop-builder` skill for the downstream interview/scaffold.

## Global Constraints

- **No emoji in docs** — structure (tables, ASCII, callouts) only. (AGENTS.md)
- **`SKILL.md` under ~500 lines**; depth pushed into `references/`, loaded on demand. (AGENTS.md)
- **Durable knowledge → skill; changing state → external file.** No mutable state in any `SKILL.md`. (AGENTS.md)
- **Python stdlib only** for scripts; deterministic and red-green tested under `scripts/tests/`. (AGENTS.md / feedback-to-issue precedent)
- **Never fabricate.** Any blueprint block without transcript evidence is `UNKNOWN → ASK`, never a guess. Any `/goal` `/loop` `/schedule` or transcript-path mechanic is annotated "verify against current Claude Code docs." (spec)
- **Output is loops only.** The skill never scaffolds a loop or a standalone skill itself — it hands a pre-filled blueprint to `loop-builder`, which stays the single scaffolding authority. (spec)
- **Commit trailer:** every commit ends with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Work lands on `feature/loop-distiller`.
- **Module env overrides** follow the `feedback_log` precedent: a `LOOP_DISTILLER_*` env var overrides any home-relative path so tests never touch real `~/.claude`.

## File Structure

| Path | Responsibility | Form |
| --- | --- | --- |
| `skills/loop-distiller/scripts/distiller/transcript_reader.py` | locate + parse + condense a session transcript into block-signal evidence | python3 module (deterministic) |
| `skills/loop-distiller/scripts/tests/test_transcript_reader.py` | red-green unit tests for the kernel | unittest |
| `skills/loop-distiller/scripts/tests/fixtures/` | fixture JSONL transcripts | test data |
| `skills/loop-distiller/scripts/tests/test_loop_distiller.sh` | runner: `unittest discover` over the tests dir | bash |
| `skills/loop-distiller/references/distillation.md` | the seven-block rubric, the pre-filled blueprint template, evidence-cite format, `UNKNOWN → ASK` rule, loop-builder handoff | markdown reference |
| `skills/loop-distiller/SKILL.md` | skill body: triggering description + Trigger A orchestration + consent posture | markdown skill |
| `.github/workflows/tests.yml:` (modify) | add a CI step running the new test runner | CI |
| `evals/evals.json` (modify) | trigger/behaviour evals for the distiller | json |

**Module API (locked here so every task agrees on names/types):**

```python
# transcript_reader.py — public surface
TRANSCRIPT_FILE_ENV = "LOOP_DISTILLER_TRANSCRIPT_FILE"   # points straight at one .jsonl
TRANSCRIPT_DIR_ENV  = "LOOP_DISTILLER_TRANSCRIPT_DIR"    # a dir to pick the newest .jsonl from

def encode_project_dir(cwd: str) -> str: ...
    # observed Claude Code convention: replace '/' and '_' with '-'. FLAGGED as
    # needing verification against current docs; not a guaranteed API.

def locate(cwd: str | None = None) -> "pathlib.Path | None": ...
    # resolution order: TRANSCRIPT_FILE_ENV -> TRANSCRIPT_DIR_ENV/newest
    # -> ~/.claude/projects/<encode_project_dir(cwd)>/newest -> None

def parse(path) -> list[dict]: ...
    # each event: {"i": int, "role": str, "type": str, "tool": str | None, "text": str}
    # type in {"user","assistant","tool_use","tool_result"}; lines that don't
    # parse are skipped (defensive).

def condense(events: list[dict]) -> dict: ...
    # returns {"discovery": [ref], "action": [ref], "verify": [ref], "vcs": [ref],
    #          "counts": {"discovery": int, "action": int, "verify": int, "vcs": int}}
    # ref = {"i": int, "tool": str, "hint": str}
```

**Assumed transcript line schema** (concrete target for `parse`; flagged for verification at implementation time): each JSONL line is an object `{"type": "user"|"assistant", "message": {"role": ..., "content": [block, ...]}}` where a block is `{"type": "text", "text": ...}`, `{"type": "tool_use", "name": ..., "input": {...}}`, or `{"type": "tool_result", "content": ...}`. Lines not matching degrade gracefully (skipped), never crash.

---

### Task 1: Kernel — `locate()` (find the session transcript)

**Files:**
- Create: `skills/loop-distiller/scripts/distiller/transcript_reader.py`
- Test: `skills/loop-distiller/scripts/tests/test_transcript_reader.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `encode_project_dir(cwd) -> str`, `locate(cwd=None) -> pathlib.Path | None`, the two env-var constants.

- [ ] **Step 1: Write the failing test**

```python
# skills/loop-distiller/scripts/tests/test_transcript_reader.py
import os, sys, json, time, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import transcript_reader as tr  # noqa: E402


class LocateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        for k in (tr.TRANSCRIPT_FILE_ENV, tr.TRANSCRIPT_DIR_ENV):
            os.environ.pop(k, None)

    def tearDown(self):
        for k in (tr.TRANSCRIPT_FILE_ENV, tr.TRANSCRIPT_DIR_ENV):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def test_encode_replaces_slash_and_underscore(self):
        self.assertEqual(tr.encode_project_dir("/work/u/my_ws/loop-builder"),
                         "-work-u-my-ws-loop-builder")

    def test_file_env_takes_precedence(self):
        f = self.dir / "s.jsonl"
        f.write_text("{}\n", encoding="utf-8")
        os.environ[tr.TRANSCRIPT_FILE_ENV] = str(f)
        self.assertEqual(tr.locate(), f)

    def test_dir_env_picks_newest(self):
        old = self.dir / "old.jsonl"; old.write_text("{}\n", encoding="utf-8")
        new = self.dir / "new.jsonl"; new.write_text("{}\n", encoding="utf-8")
        os.utime(old, (1, 1)); os.utime(new, (time.time(), time.time()))
        os.environ[tr.TRANSCRIPT_DIR_ENV] = str(self.dir)
        self.assertEqual(tr.locate(), new)

    def test_returns_none_when_nothing_found(self):
        os.environ[tr.TRANSCRIPT_DIR_ENV] = str(self.dir)  # empty dir
        self.assertIsNone(tr.locate())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader`
(Run from that dir — the package path has a hyphen, so dotted `-m` module paths won't work.)
Expected: FAIL — `ModuleNotFoundError: No module named 'transcript_reader'`.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/loop-distiller/scripts/distiller/transcript_reader.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/transcript_reader.py \
        skills/loop-distiller/scripts/tests/test_transcript_reader.py
git commit -m "$(printf 'feat(loop-distiller): locate session transcript jsonl\n\nObserved-convention path resolution with env overrides for testability.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: Kernel — `parse()` (JSONL → normalized events)

**Files:**
- Modify: `skills/loop-distiller/scripts/distiller/transcript_reader.py`
- Modify: `skills/loop-distiller/scripts/tests/test_transcript_reader.py`
- Create: `skills/loop-distiller/scripts/tests/fixtures/session.jsonl`

**Interfaces:**
- Consumes: `pathlib.Path` from `locate()`.
- Produces: `parse(path) -> list[dict]` with events `{"i","role","type","tool","text"}`.

- [ ] **Step 1: Write the fixture**

```jsonl
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"triage my P1 issues"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"gh issue list --label P1"}}]}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"#41 #42"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"assigning owners"},{"type":"tool_use","name":"Bash","input":{"command":"gh issue edit 41 --add-assignee me"}}]}}
not json at all
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"pytest -q"}}]}}
```

- [ ] **Step 2: Write the failing test (append to test file)**

```python
class ParseTest(unittest.TestCase):
    def setUp(self):
        self.fix = pathlib.Path(__file__).resolve().parent / "fixtures" / "session.jsonl"

    def test_parse_yields_events_with_line_index(self):
        events = tr.parse(self.fix)
        self.assertEqual(events[0]["type"], "user")
        self.assertEqual(events[0]["text"], "triage my P1 issues")
        self.assertEqual(events[0]["i"], 0)

    def test_parse_extracts_tool_uses(self):
        events = tr.parse(self.fix)
        tools = [e for e in events if e["type"] == "tool_use"]
        self.assertEqual(tools[0]["tool"], "Bash")
        self.assertIn("gh issue list", tools[0]["text"])

    def test_parse_skips_unparseable_lines(self):
        events = tr.parse(self.fix)  # "not json at all" must not crash or appear
        self.assertFalse(any("not json" in e["text"] for e in events))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader.ParseTest`
Expected: FAIL — `AttributeError: module 'transcript_reader' has no attribute 'parse'`.

- [ ] **Step 4: Write minimal implementation (append to module)**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader`
Expected: PASS (all Locate + Parse tests).

- [ ] **Step 6: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/transcript_reader.py \
        skills/loop-distiller/scripts/tests/test_transcript_reader.py \
        skills/loop-distiller/scripts/tests/fixtures/session.jsonl
git commit -m "$(printf 'feat(loop-distiller): parse transcript jsonl into normalized events\n\nDefensive line-by-line parse; unparseable lines skipped, never fatal.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 3: Kernel — `condense()` (events → block-signal evidence)

**Files:**
- Modify: `skills/loop-distiller/scripts/distiller/transcript_reader.py`
- Modify: `skills/loop-distiller/scripts/tests/test_transcript_reader.py`

**Interfaces:**
- Consumes: `list[dict]` from `parse()`.
- Produces: `condense(events) -> {"discovery","action","verify","vcs","counts"}`, each bucket a list of `ref = {"i","tool","hint"}`.

- [ ] **Step 1: Write the failing test (append)**

```python
class CondenseTest(unittest.TestCase):
    def setUp(self):
        fix = pathlib.Path(__file__).resolve().parent / "fixtures" / "session.jsonl"
        self.c = tr.condense(tr.parse(fix))

    def test_discovery_captures_list_queries(self):
        hints = " ".join(r["hint"] for r in self.c["discovery"])
        self.assertIn("gh issue list", hints)

    def test_action_captures_mutations(self):
        hints = " ".join(r["hint"] for r in self.c["action"])
        self.assertIn("gh issue edit", hints)

    def test_verify_captures_test_runs(self):
        self.assertTrue(any("pytest" in r["hint"] for r in self.c["verify"]))

    def test_counts_match_bucket_lengths(self):
        for k in ("discovery", "action", "verify", "vcs"):
            self.assertEqual(self.c["counts"][k], len(self.c[k]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader.CondenseTest`
Expected: FAIL — `AttributeError: module 'transcript_reader' has no attribute 'condense'`.

- [ ] **Step 3: Write minimal implementation (append to module)**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/loop-distiller/scripts/tests && python3 -m unittest -v test_transcript_reader`
Expected: PASS (Locate + Parse + Condense).

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/scripts/distiller/transcript_reader.py \
        skills/loop-distiller/scripts/tests/test_transcript_reader.py
git commit -m "$(printf 'feat(loop-distiller): condense events into block-signal evidence\n\nCoarse deterministic categorization with line refs; judgment stays in SKILL.md.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 4: Test runner + CI wiring

**Files:**
- Create: `skills/loop-distiller/scripts/tests/test_loop_distiller.sh`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: the unittest suite from Tasks 1-3.
- Produces: one red-green command CI can call; exit 0 == all pass.

- [ ] **Step 1: Write the runner**

```bash
# skills/loop-distiller/scripts/tests/test_loop_distiller.sh
#!/usr/bin/env bash
# Runs the loop-distiller kernel unit tests (python3 stdlib only).
# Red-green contract: exit 0 == all pass.
# Run: bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
python3 -m unittest discover -s . -p 'test_*.py' -v
```

- [ ] **Step 2: Make it executable and run it (verify green)**

Run: `chmod +x skills/loop-distiller/scripts/tests/test_loop_distiller.sh && bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh`
Expected: PASS — all kernel tests discovered and green.

- [ ] **Step 3: Add the CI step**

In `.github/workflows/tests.yml`, after the `Feedback module tests` step, add:

```yaml
      - name: loop-distiller kernel tests
        run: bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh
```

- [ ] **Step 4: Verify the workflow still parses as YAML**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/tests.yml')); print('ok')"`
Expected: `ok` (if PyYAML is unavailable, instead run `python3 -c "import json"`-style is N/A; visually confirm indentation matches the sibling steps — two spaces under \`steps:\` list items).

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/scripts/tests/test_loop_distiller.sh .github/workflows/tests.yml
git commit -m "$(printf 'test(loop-distiller): add kernel test runner and CI step\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 5: Reference — `references/distillation.md`

**Files:**
- Create: `skills/loop-distiller/references/distillation.md`

**Interfaces:**
- Consumes: the `condense()` bucket names (`discovery/action/verify/vcs`) as evidence inputs.
- Produces: the rubric, the pre-filled blueprint template, the cite format, and the handoff procedure that `SKILL.md` points to.

This task has no unit test; its deliverable is verified by (a) the no-emoji / no-local-home-paths pre-commit hooks and (b) the structural check in Step 3.

- [ ] **Step 1: Write the reference**

Create `skills/loop-distiller/references/distillation.md` with exactly these sections:

````markdown
# Distillation — rubric, blueprint, handoff

The engine answers one question: **does this session fill the loop-builder
blueprint?** Detection and the blueprint are the same rubric.

## Seven-block detection rubric

| Block | Transcript signal | Evidence source |
| --- | --- | --- |
| Goal (verifiable) | a repeated "done" state — tests pass, "that works", a check that flipped green | `verify` bucket + user text |
| Trigger | a recurring stimulus — similar session openings; (Phase 2) a time/frequency pattern | first user turn |
| Discovery | read-only fan-out to find work | `discovery` bucket |
| Action | mutating calls | `action` bucket |
| Verification | a check step (test/build/re-query/review) | `verify` bucket |
| State | progress tracked (TODOs, notes, issue/PR updates) | `action`/`vcs` + text |
| Human gates | irreversible acts (commit, push, send, merge, deploy) | `vcs` bucket |

**Gating.** Trigger A is *lenient* — the user asked, so 4+ blocks with evidence is
enough to pre-fill; the interview corrects the rest. (Strict, recurrence-based
gating is Phase 2 / Trigger C and is out of scope here.)

## Pre-filled blueprint (the literal loop-builder template)

Emit loop-builder's fill-in template with each line drafted from evidence, an
`⟵ ev:` cite (transcript line indices `i` and/or bucket), and a confidence marker.
Blocks with no evidence are `UNKNOWN → ASK` — never guessed.

```
GOAL (verifiable):   <drafted>            ⟵ ev: <i,…> · conf: high|med|low
TRIGGER:             <drafted or UNKNOWN> ⟵ ev: … · conf: …
DISCOVERY:           <drafted>            ⟵ ev: discovery[i] · conf: …
ACTION:              <drafted>            ⟵ ev: action[i] · conf: …
VERIFY:              <drafted or UNKNOWN> ⟵ ev: verify[i] · conf: …
STATE:               UNKNOWN — ASK
HUMAN GATES:         <from vcs bucket, or UNKNOWN — ASK>
BUDGET / stop:       UNKNOWN — ASK
```

**Never fabricate.** No evidence → `UNKNOWN → ASK`. Any `/goal` `/loop`
`/schedule` mechanic, and the transcript-path scheme itself, are annotated
"verify against current Claude Code docs."

## Handoff to loop-builder

1. Present the pre-filled blueprint to the user for correction.
2. Invoke the `loop-builder` skill, passing the corrected answers as the starting
   point for its seven-question interview. loop-builder remains the single
   scaffolding authority — this skill never writes loop files itself.
3. The interview asks exactly the `UNKNOWN → ASK` blocks (and lets the user revise
   any drafted line), then scaffolds as normal.
````

- [ ] **Step 2: Verify the pre-commit hygiene hooks pass on the file**

Run: `pre-commit run --files skills/loop-distiller/references/distillation.md`
Expected: `Detect secrets` and `Block machine-local absolute home paths` both Passed. (If `pre-commit` isn't installed: `grep -nE '/(home|Users)/[A-Za-z0-9._-]+/' skills/loop-distiller/references/distillation.md` must print nothing.)

- [ ] **Step 3: Verify required sections exist**

Run:
```bash
grep -c -E '^## (Seven-block detection rubric|Pre-filled blueprint|Handoff to loop-builder)' skills/loop-distiller/references/distillation.md
```
Expected: `3`.

- [ ] **Step 4: Commit**

```bash
git add skills/loop-distiller/references/distillation.md
git commit -m "$(printf 'docs(loop-distiller): rubric, pre-filled blueprint, handoff reference\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 6: `SKILL.md` (skill body, Trigger A)

**Files:**
- Create: `skills/loop-distiller/SKILL.md`

**Interfaces:**
- Consumes: `transcript_reader` (via `${CLAUDE_PLUGIN_ROOT}/skills/loop-distiller/scripts/distiller/`), `references/distillation.md`, and the `loop-builder` skill.
- Produces: the user-facing skill — its `description` is the trigger surface; its body is the Trigger A procedure.

This task has no unit test; deliverables are verified by frontmatter/line-count/no-mutable-state checks in Steps 2-4 and by the evals in Task 7.

- [ ] **Step 1: Write the skill**

Create `skills/loop-distiller/SKILL.md`:

````markdown
---
name: loop-distiller
description: >-
  Turn a workflow you just performed into a pre-filled loop blueprint. Use when
  the user says "turn what I just did into a loop", "distill my recent work",
  "make a loop out of this session", or otherwise wants to automate a multi-step
  task they already did by hand. Reads the current session transcript, judges
  whether it fills the loop blueprint, drafts the seven answers from evidence
  (never fabricating), and hands off to loop-builder to run the interview and
  scaffold. It never scaffolds loops itself.
---

# Loop Distiller

Turn real session history into a **pre-filled loop-builder blueprint**. This skill
is the evidence front-end; `loop-builder` is the interview and the single
scaffolding authority. Output is always a loop — never a standalone skill.

The backbone knowledge is `references/distillation.md` (rubric + blueprint +
handoff). Load it when you run the flow.

## When this fires

On demand only (Trigger A). The user asks to distill what they just did. There is
no background watching in this phase — a cross-session scanning loop (Trigger C)
is designed in the spec but not built yet.

## Procedure

1. **Read the transcript.** Prefer the current session already in your context.
   For precision or after a `/clear`/compaction, re-read it deterministically:

   ```bash
   python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/loop-distiller/scripts/distiller'); \
   import transcript_reader as tr, json; p = tr.locate(); \
   print(json.dumps(tr.condense(tr.parse(p)), indent=2) if p else 'NO_TRANSCRIPT')"
   ```

   The script's transcript-path scheme is an observed Claude Code convention —
   **verify against current docs**; if it returns `NO_TRANSCRIPT`, fall back to
   the in-context history.

2. **Apply the rubric** from `references/distillation.md`. Count how many of the
   seven blocks have evidence. Lenient gate: 4+ blocks → proceed. Fewer → tell the
   user this session doesn't look like a reusable workflow yet, and stop. (Saying
   no is the point — most sessions are one-offs.)

3. **Draft the blueprint.** Emit loop-builder's fill-in template with each line
   drawn from evidence, an `⟵ ev:` cite, and a confidence marker. Any block
   without evidence is `UNKNOWN → ASK`. **Never fabricate** a value or a `/goal`
   `/loop` `/schedule` flag — flag uncertainty instead.

4. **Hand off to loop-builder.** Present the draft for correction, then invoke the
   `loop-builder` skill with the corrected answers as its interview starting
   point. Do not scaffold loop files here.

## What this skill must not do

- Never write a loop, a `SKILL.md`, a `STATE.md`, or any scaffold file — that is
  loop-builder's job.
- Never emit a standalone skill (no Hermes-style skill sprawl — loops only).
- Never invent evidence. `UNKNOWN → ASK` beats a confident guess.

## Collecting feedback and reporting bugs

On an error or when clearly blocked, capture locally (never auto-filed):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback/cli.py" \
  append --category bug --text "<what broke + context>"
```

To review and file, invoke the `loop-builder:feedback-to-issue` skill.
````

- [ ] **Step 2: Verify the frontmatter parses and required keys exist**

Run:
```bash
python3 - <<'PY'
import re, pathlib
t = pathlib.Path("skills/loop-distiller/SKILL.md").read_text()
m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
assert m, "no frontmatter block"
fm = m.group(1)
assert "name: loop-distiller" in fm, "missing/incorrect name"
assert "description:" in fm, "missing description"
print("frontmatter ok")
PY
```
Expected: `frontmatter ok`.

- [ ] **Step 3: Verify the line-count budget and no-mutable-state rule**

Run:
```bash
test "$(wc -l < skills/loop-distiller/SKILL.md)" -lt 500 && echo "under-500-ok"
! grep -nE '^\s*-\s*\[[ x]\]|STATE row|status:\s*(open|done)' skills/loop-distiller/SKILL.md && echo "no-mutable-state-ok"
```
Expected: `under-500-ok` and `no-mutable-state-ok` (the SKILL.md carries conventions only — no ledgers, no progress).

- [ ] **Step 4: Verify hygiene hooks**

Run: `pre-commit run --files skills/loop-distiller/SKILL.md`
Expected: secret-scan and home-path hooks Passed. (No-emoji is a docs rule; visually confirm none were added.)

- [ ] **Step 5: Commit**

```bash
git add skills/loop-distiller/SKILL.md
git commit -m "$(printf 'feat(loop-distiller): SKILL.md body for on-demand Trigger A\n\nReads the session transcript, applies the seven-block rubric, drafts a\npre-filled blueprint (UNKNOWN->ASK, never fabricated), hands off to loop-builder.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 7: Evals — triggering and behaviour

**Files:**
- Modify: `evals/evals.json`

**Interfaces:**
- Consumes: nothing at runtime; documents the expected trigger boundary and behaviour.
- Produces: two eval entries the CI "Evals parse" step validates as JSON.

- [ ] **Step 1: Add two eval entries**

Append these objects to the `evals` array in `evals/evals.json` (renumber `id` to follow the last existing entry; keep the file valid JSON — comma after the previous last entry):

```json
{
  "id": 101,
  "prompt": "I just spent this whole session triaging P1 issues by hand — turn what I just did into a loop",
  "expected_output": "Triggers loop-distiller (not loop-builder cold); reads the current session transcript; applies the seven-block rubric; emits a pre-filled loop-builder blueprint with evidence cites and UNKNOWN->ASK for unseen blocks; hands off to loop-builder; never scaffolds files itself.",
  "files": [],
  "expectations": [
    "The loop-distiller skill is invoked, not loop-builder directly and not an ad-hoc answer",
    "It reads or summarizes the current session transcript as the evidence source",
    "It emits the loop-builder fill-in template pre-filled from evidence, with cites",
    "Blocks with no transcript evidence are marked UNKNOWN -> ASK rather than guessed",
    "It hands off to loop-builder for the interview and scaffolding, and does not write loop files itself",
    "Any /goal, /loop, /schedule, or transcript-path mechanic is flagged as needing verification against current docs"
  ]
},
{
  "id": 102,
  "prompt": "Distill my recent work into a loop",
  "expected_output": "Triggers loop-distiller; if the session lacks enough block evidence (a one-off), it says so and declines rather than forcing a loop; output is loops only, never a standalone skill.",
  "files": [],
  "expectations": [
    "The loop-distiller skill is invoked",
    "When fewer than four blocks have evidence, it tells the user this is not a reusable workflow yet and stops instead of fabricating a loop",
    "It never emits a standalone skill (loops only)",
    "It does not invent evidence or fabricate command flags"
  ]
}
```

- [ ] **Step 2: Verify the JSON still parses**

Run: `python3 -c "import json; d=json.load(open('evals/evals.json')); print(len(d['evals']), 'evals')"`
Expected: prints the new total count, no exception.

- [ ] **Step 3: Commit**

```bash
git add evals/evals.json
git commit -m "$(printf 'test(loop-distiller): trigger and behaviour evals\n\nAsserts loop-distiller fires (not loop-builder cold), pre-fills the blueprint\nwith UNKNOWN->ASK, declines one-offs, and stays loops-only.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Final verification (after all tasks)

- [ ] Run the full kernel suite: `bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh` → all green.
- [ ] Run the sibling suites to confirm no regressions: `bash skills/loop-builder/scripts/tests/test_verifiers.sh` and `bash skills/feedback-to-issue/scripts/tests/test_feedback.sh`.
- [ ] `python3 -c "import json; json.load(open('evals/evals.json'))"` → no error.
- [ ] Confirm no mutable state lives in `skills/loop-distiller/SKILL.md` and it is under 500 lines.
- [ ] Push `feature/loop-distiller` and open a PR (outward-facing — confirm with the maintainer first, per AGENTS.md).
