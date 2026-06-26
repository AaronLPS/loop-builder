# Multi-Skill Plugin Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the loop-builder repo from a single root-level skill into a Claude Code **plugin** that bundles two self-contained peer skills (`loop-builder`, `feedback-to-issue`) under `skills/`, with no behavior change and the green test suite intact.

**Architecture:** Each skill becomes a self-contained directory (`skills/<name>/` holding its own `SKILL.md`, `references/`, `scripts/`). A `.claude-plugin/` manifest makes the repo an installable plugin. Cross-skill runtime references use the `${CLAUDE_PLUGIN_ROOT}` token; within-skill references stay relative (they move together, so the skill base-dir resolves them unchanged). All persistent state (`~/.loop-builder/feedback.jsonl`, generated-loop `STATE.md`) is HOME/project-anchored and does not move.

**Tech Stack:** Claude Code plugin/skill system, `python3` stdlib (feedback module + tests), `bash` (verifier/skill-bank tooling + test runners), GitHub Actions CI.

## Global Constraints

- **Distribution target:** Claude Code only. Do **not** create `.codex-plugin`, `.cursor-plugin`, `.pi`, `gemini-extension.json`, or `hooks/`.
- **Plugin name = `loop-builder`**; flagship skill dir = `skills/loop-builder/`; second skill dir = `skills/feedback-to-issue/`. Cross-references read `loop-builder:feedback-to-issue`.
- **No behavior change.** This is a structural move + path rewiring only. No logic edits to any `.py` or generator step.
- **Preserve git history:** use `git mv` for every move (never delete+recreate).
- **Persistent paths unchanged:** keep `~/.loop-builder/feedback.jsonl` and the env-var names `LOOP_BUILDER_FEEDBACK_FILE` and `LOOP_BUILDER_SCRIPTS`.
- **Skill dir name = invocation name.** Frontmatter `name` is a display label only; the directory name is what Claude Code uses to invoke.
- **Docs style (AGENTS.md):** no emoji in docs; structure via tables/box-diagrams/badges. Commit trailer required: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Branch:** all work on `restructure/multi-skill-plugin` (already created); land via PR, never push to `main`.

---

## File Structure (target)

```
loop-builder/                                  ← repo root = PLUGIN root
├── .claude-plugin/
│   ├── plugin.json                            ← NEW: manifest (name, description, version, …)
│   └── marketplace.json                       ← NEW: self-install entry (source "./")
├── skills/
│   ├── loop-builder/                          ← flagship skill (moved from root)
│   │   ├── SKILL.md                           ← moved; cross-skill cli.py ref rewired
│   │   ├── references/                        ← moved verbatim (loops-and-loop-engineering,
│   │   │                                         pattern-*.md, deploy-*.md, skill-bank/)
│   │   └── scripts/                           ← moved: verifier_template.sh,
│   │       │                                     verify_no_p1_unassigned.sh,
│   │       │                                     build_skill_bank_catalog.sh, format_catalog.sh,
│   │       │                                     lint_skill_bank_*.sh, refresh_skill_bank.sh
│   │       └── tests/                          ← moved: test_verifiers.sh, test_skill_bank.sh, fixtures/
│   └── feedback-to-issue/                     ← NEW peer skill
│       ├── SKILL.md                           ← NEW: thin trigger wrapper
│       ├── references/
│       │   └── feedback-to-issue.md           ← moved playbook; script paths updated
│       └── scripts/
│           ├── feedback/                       ← moved: cli.py, feedback_log.py, sanitize.py,
│           │                                     dedupe.py, file_issue.py
│           └── tests/                          ← moved: test_*.py + test_feedback.sh runner
├── AGENTS.md                                  ← + governing rule + new layout description
├── README.md                                  ← rewritten as plugin README
├── docs/ · evals/ · LICENSE                   ← stay at root
├── .github/workflows/tests.yml               ← CI paths updated
└── .gitignore · .gitleaks.toml · .pre-commit-config.yaml   ← stay at root
```

**Task ordering rationale:** Manifest first (Task 1) so the plugin is loadable as soon as skills land. Then each skill moves and re-greens its own tests independently (Tasks 2–3). Then cross-skill rewiring (Task 4) which depends on both skills existing. Then CI (Task 5), then docs (Tasks 6–7), then a whole-plugin verification (Task 8).

---

### Task 1: Plugin manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`

**Interfaces:**
- Produces: a plugin named `loop-builder` that Claude Code can install; later tasks place skills at `skills/<name>/` for auto-discovery.

- [ ] **Step 1: Create the plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "loop-builder",
  "description": "Design and scaffold self-running agent loops, and file feedback as GitHub issues under your own account.",
  "version": "0.1.0",
  "author": { "name": "AaronLPS" },
  "homepage": "https://github.com/AaronLPS/loop-builder",
  "repository": "https://github.com/AaronLPS/loop-builder",
  "license": "MIT"
}
```

- [ ] **Step 2: Create the marketplace entry**

Create `.claude-plugin/marketplace.json` (single self-hosted plugin at the marketplace root):

```json
{
  "name": "loop-builder",
  "owner": { "name": "AaronLPS" },
  "plugins": [
    {
      "name": "loop-builder",
      "source": "./",
      "description": "Design and scaffold self-running agent loops, plus a feedback-to-issue skill."
    }
  ]
}
```

- [ ] **Step 3: Validate JSON parses**

Run: `python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat(plugin): add plugin.json + marketplace.json manifest

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

> NOTE: `marketplace.json`'s full schema is not exhaustively documented; Task 8 validates the manifest by actually installing the plugin locally. If install fails on a schema error, fix the manifest there.

---

### Task 2: Move feedback-to-issue into its own skill

**Files:**
- Move: `scripts/feedback/*.py` → `skills/feedback-to-issue/scripts/feedback/`
- Move: `scripts/tests/feedback/test_*.py` → `skills/feedback-to-issue/scripts/tests/`
- Move: `scripts/tests/test_feedback.sh` → `skills/feedback-to-issue/scripts/tests/test_feedback.sh`
- Move: `references/feedback-to-issue.md` → `skills/feedback-to-issue/references/feedback-to-issue.md`
- Create: `skills/feedback-to-issue/SKILL.md`
- Modify: the 5 test files' `sys.path` line; `test_feedback.sh` discover path; `references/feedback-to-issue.md` script paths

**Interfaces:**
- Produces: skill dir `skills/feedback-to-issue/` whose 22-test suite passes from `bash skills/feedback-to-issue/scripts/tests/test_feedback.sh`.

- [ ] **Step 1: Move the Python module + playbook + tests with git mv**

```bash
mkdir -p skills/feedback-to-issue/scripts skills/feedback-to-issue/references
git mv scripts/feedback skills/feedback-to-issue/scripts/feedback
git mv scripts/tests/feedback skills/feedback-to-issue/scripts/tests
git mv scripts/tests/test_feedback.sh skills/feedback-to-issue/scripts/tests/test_feedback.sh
git mv references/feedback-to-issue.md skills/feedback-to-issue/references/feedback-to-issue.md
```

- [ ] **Step 2: Run the suite to confirm it FAILS (paths now stale)**

Run: `python3 -m unittest discover -s skills/feedback-to-issue/scripts/tests -p 'test_*.py' 2>&1 | tail -5`
Expected: FAIL — `ModuleNotFoundError: No module named 'feedback_log'` (the `parents[3]` path no longer resolves to the module).

- [ ] **Step 3: Fix the sys.path line in all 5 test files**

In each of `test_feedback_log.py`, `test_sanitize.py`, `test_dedupe.py`, `test_file_issue.py`, `test_cli.py` under `skills/feedback-to-issue/scripts/tests/`, replace:

```python
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts" / "feedback"))
```

with (module is now two levels up from the test dir, i.e. `scripts/feedback` relative to `scripts/tests`):

```python
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "feedback"))
```

Apply across all five:

```bash
cd skills/feedback-to-issue/scripts/tests
sed -i 's#parents\[3\] / "scripts" / "feedback"#parents[1] / "feedback"#' test_*.py
cd -
```

- [ ] **Step 4: Rewrite the test runner to self-resolve**

Replace the body of `skills/feedback-to-issue/scripts/tests/test_feedback.sh` with:

```bash
#!/usr/bin/env bash
# Runs the feedback module unit tests (python3 stdlib only).
# Red-green contract: exit 0 == all pass.
# Run: bash skills/feedback-to-issue/scripts/tests/test_feedback.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
python3 -m unittest discover -s . -p 'test_*.py' -v
```

- [ ] **Step 5: Run the suite to confirm it PASSES from the new location**

Run: `bash skills/feedback-to-issue/scripts/tests/test_feedback.sh 2>&1 | tail -3`
Expected: `Ran 22 tests` … `OK`

- [ ] **Step 6: Update the LOOP_BUILDER_SCRIPTS note in the moved playbook**

The playbook's `python3 scripts/feedback/cli.py …` invocations are **unchanged** — within this skill the module still sits at `scripts/feedback/`, so that relative path stays correct (it resolves against the skill base dir). The only edit needed is the `LOOP_BUILDER_SCRIPTS` definition note. In `skills/feedback-to-issue/references/feedback-to-issue.md`, change:

```
- `LOOP_BUILDER_SCRIPTS` — path to `scripts/feedback/` in the loop-builder repo.
```

to:

```
- `LOOP_BUILDER_SCRIPTS` — absolute path to this skill's `scripts/feedback/`
  directory, i.e. `${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback`,
  resolved at scaffold time and baked into the generated loop.
```

Verify no stale references remain: `grep -n "scripts/feedback/" skills/feedback-to-issue/references/feedback-to-issue.md` — every hit must be a within-skill relative `scripts/feedback/cli.py` example (correct) or the updated `LOOP_BUILDER_SCRIPTS` note.

- [ ] **Step 7: Create the thin SKILL.md**

Create `skills/feedback-to-issue/SKILL.md`:

```markdown
---
name: feedback-to-issue
description: >-
  Capture, review, and file a bug report or feedback as a GitHub issue under the
  user's OWN account. Use whenever the user wants to report a bug, give feedback,
  file an issue, or review collected feedback about loop-builder or a loop it
  generated. Sanitizes private content and requires explicit consent before any
  public issue is filed.
---

# Feedback to Issue

Capture feedback locally, then — only on the user's explicit yes — file a clean,
sanitized GitHub issue under the user's own account (via their `gh` session, or a
prefilled browser URL). Nothing is auto-filed.

The full step-by-step flow, guarantees, sanitization rules, dedupe, consent gate,
and the generated-loop opt-in hook live in the reference. Load it on demand:

- `references/feedback-to-issue.md` — the complete playbook (capture → list-open →
  cluster → draft → dedupe → sanitize → **mandatory consent gate** → file →
  mark-filed), plus the maintainer label setup and the generated-loop hook snippet.

Bundled deterministic tooling lives in `scripts/feedback/` (red-green tested under
`scripts/tests/`). Invoke it with `python3 scripts/feedback/cli.py <subcommand>`.
```

- [ ] **Step 8: Commit**

```bash
git add skills/feedback-to-issue
git commit -m "refactor(feedback): graduate feedback-to-issue into a peer skill

Move the feedback module, tests, and playbook under skills/feedback-to-issue/;
fix test sys.path + runner; add a thin SKILL.md trigger wrapper.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Move loop-builder into its own skill

**Files:**
- Move: `SKILL.md` → `skills/loop-builder/SKILL.md`
- Move: `references/` (everything left) → `skills/loop-builder/references/`
- Move: loop-builder scripts → `skills/loop-builder/scripts/`
- Move: `scripts/tests/test_verifiers.sh`, `scripts/tests/test_skill_bank.sh`, `scripts/tests/fixtures/` → `skills/loop-builder/scripts/tests/`

**Interfaces:**
- Produces: skill dir `skills/loop-builder/` whose verifier + skill-bank suites pass from their new location with no script-internal edits (they are `HERE`-relative).

- [ ] **Step 1: Move SKILL.md, references, and loop-builder's scripts/tests**

```bash
mkdir -p skills/loop-builder/scripts
git mv SKILL.md skills/loop-builder/SKILL.md
git mv references skills/loop-builder/references
git mv scripts/build_skill_bank_catalog.sh skills/loop-builder/scripts/
git mv scripts/format_catalog.sh skills/loop-builder/scripts/
git mv scripts/lint_skill_bank_catalog.sh skills/loop-builder/scripts/
git mv scripts/lint_skill_bank_recommended.sh skills/loop-builder/scripts/
git mv scripts/refresh_skill_bank.sh skills/loop-builder/scripts/
git mv scripts/verifier_template.sh skills/loop-builder/scripts/
git mv scripts/verify_no_p1_unassigned.sh skills/loop-builder/scripts/
git mv scripts/tests skills/loop-builder/scripts/tests
```

- [ ] **Step 2: Confirm the now-empty root `scripts/` is gone**

Run: `test ! -e scripts && echo "root scripts/ removed" || ls -la scripts`
Expected: `root scripts/ removed` (all of `scripts/` has moved; if anything remains, it was missed above — move it under the correct skill).

- [ ] **Step 3: Run the verifier tests from the new location**

Run: `bash skills/loop-builder/scripts/tests/test_verifiers.sh 2>&1 | tail -3`
Expected: PASS (the script uses `HERE="$(dirname …)"` + `SCRIPTS="$HERE/.."`, so it self-resolves to `skills/loop-builder/scripts/`).

- [ ] **Step 4: Run the skill-bank tests from the new location**

Run: `bash skills/loop-builder/scripts/tests/test_skill_bank.sh 2>&1 | tail -3`
Expected: PASS (`ROOT="$SCRIPTS/.."` now resolves to `skills/loop-builder/`, and `$ROOT/references/skill-bank/` moved there too).

- [ ] **Step 5: Confirm loop-builder's own within-skill paths still read correctly**

loop-builder's `SKILL.md` references `references/…` and `scripts/verifier_template.sh` / `scripts/verify_no_p1_unassigned.sh`. These are relative to the skill base dir and moved together, so they remain textually correct. Verify the targets exist:

Run:
```bash
test -f skills/loop-builder/references/loops-and-loop-engineering.md \
  && test -f skills/loop-builder/scripts/verifier_template.sh \
  && test -d skills/loop-builder/references/skill-bank/catalog \
  && echo "within-skill targets present"
```
Expected: `within-skill targets present`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(loop-builder): move flagship skill under skills/loop-builder/

Relocate SKILL.md, references/, and loop-builder's own scripts + tests into a
self-contained skill dir. Test runners are HERE-relative and need no edits.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Rewire cross-skill references in loop-builder's SKILL.md

**Files:**
- Modify: `skills/loop-builder/SKILL.md` (the three feedback roles)

**Interfaces:**
- Consumes: `skills/feedback-to-issue/` from Task 2 (skill name `feedback-to-issue`; cli at `scripts/feedback/cli.py`).
- Produces: a loop-builder SKILL.md whose feedback wiring points at the sibling skill correctly.

- [ ] **Step 1: Rewire Role 2 — loop-builder's own passive capture**

In `skills/loop-builder/SKILL.md`, the passive-capture command currently reads:

```bash
python3 scripts/feedback/cli.py append --category bug --text "<what broke + context>"
```

Replace with the plugin-root-rooted cross-skill path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback/cli.py" \
  append --category bug --text "<what broke + context>"
```

- [ ] **Step 2: Rewire Role 1 — review/file flow**

Find the "Review and file" paragraph that says to load `references/feedback-to-issue.md`. Replace the instruction to *read the reference* with an instruction to *invoke the sibling skill*:

```markdown
**Review and file.** When the user asks to "report a bug," "give feedback," or
"review feedback," invoke the `loop-builder:feedback-to-issue` skill — it owns the
full flow (list-open → cluster → draft → dedupe → sanitize → **mandatory consent
gate** → file → mark-filed) under the user's own account. Do not inline that flow
here.
```

- [ ] **Step 3: Rewire Role 3 — generated-loop hook reference**

Find the "Generated loops" paragraph that points at `references/feedback-to-issue.md` for the opt-in hook. Update the pointer to the sibling skill's reference and note the path resolution:

```markdown
**Generated loops.** During scaffolding, ask whether to add self-reporting to the
loop (the opt-in hook lives in the `loop-builder:feedback-to-issue` skill's
`references/feedback-to-issue.md`). When opted in, resolve the feedback CLI path via
`${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback` and bake it into
the loop's `LOOP_BUILDER_SCRIPTS` variable. Self-reporting logs failures locally; the
loop never contacts GitHub on its own.
```

- [ ] **Step 4: Verify no stale `scripts/feedback/` or `references/feedback-to-issue.md` references remain in loop-builder**

Run: `grep -n "scripts/feedback\|references/feedback-to-issue" skills/loop-builder/SKILL.md`
Expected: only matches inside the `${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/...` paths (Roles 2 & 3). No bare `scripts/feedback/cli.py` and no `load references/feedback-to-issue.md`.

- [ ] **Step 5: Commit**

```bash
git add skills/loop-builder/SKILL.md
git commit -m "refactor(loop-builder): rewire feedback refs to the sibling skill

Role 1 review/file -> invoke loop-builder:feedback-to-issue. Roles 2 & 3 (own
passive capture, generated-loop hook) -> CLI path via \${CLAUDE_PLUGIN_ROOT}.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Update CI workflow paths

**Files:**
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: the new skill-local script locations from Tasks 2–3.
- Produces: a CI job that runs all four suites + lints + evals from their new paths.

- [ ] **Step 1: Update every moved path in tests.yml**

Edit `.github/workflows/tests.yml` step `run:` lines:

| Old | New |
|-----|-----|
| `bash scripts/tests/test_verifiers.sh` | `bash skills/loop-builder/scripts/tests/test_verifiers.sh` |
| `bash scripts/tests/test_skill_bank.sh` | `bash skills/loop-builder/scripts/tests/test_skill_bank.sh` |
| `bash scripts/lint_skill_bank_recommended.sh` | `bash skills/loop-builder/scripts/lint_skill_bank_recommended.sh --file skills/loop-builder/references/skill-bank/recommended.md` |
| `for c in references/skill-bank/catalog/*.md` | `for c in skills/loop-builder/references/skill-bank/catalog/*.md` |
| `bash scripts/lint_skill_bank_catalog.sh --file "$c"` | `bash skills/loop-builder/scripts/lint_skill_bank_catalog.sh --file "$c"` |
| `bash scripts/tests/test_feedback.sh` | `bash skills/feedback-to-issue/scripts/tests/test_feedback.sh` |

The `Evals parse` step (`evals/evals.json`) is unchanged — evals stay at root.

> The `lint_skill_bank_recommended.sh` invocation gains an explicit `--file` because its built-in default (`references/skill-bank/recommended.md`) is CWD-relative and CI runs from repo root, where that path no longer exists.

- [ ] **Step 2: Dry-run every CI command locally**

Run:
```bash
bash skills/loop-builder/scripts/tests/test_verifiers.sh >/dev/null 2>&1 && echo "verifiers OK"
bash skills/loop-builder/scripts/tests/test_skill_bank.sh >/dev/null 2>&1 && echo "skill-bank OK"
bash skills/loop-builder/scripts/lint_skill_bank_recommended.sh --file skills/loop-builder/references/skill-bank/recommended.md >/dev/null 2>&1 && echo "lint-recommended OK"
for c in skills/loop-builder/references/skill-bank/catalog/*.md; do bash skills/loop-builder/scripts/lint_skill_bank_catalog.sh --file "$c" >/dev/null 2>&1 || { echo "lint FAIL $c"; break; }; done && echo "lint-catalogs OK"
python3 -c "import json; json.load(open('evals/evals.json'))" && echo "evals OK"
bash skills/feedback-to-issue/scripts/tests/test_feedback.sh >/dev/null 2>&1 && echo "feedback OK"
```
Expected: six lines — `verifiers OK`, `skill-bank OK`, `lint-recommended OK`, `lint-catalogs OK`, `evals OK`, `feedback OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/tests.yml
git commit -m "ci: point test + lint steps at the new skills/ paths

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Update AGENTS.md (governing rule + new layout)

**Files:**
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: the convention that answers "should this be a skill or a reference?" for future growth.

- [ ] **Step 1: Update "What this repo is" to describe the plugin**

Replace the current paragraph:

```markdown
`loop-builder` is a Claude Code **skill** that interviews the user and scaffolds a
self-running agent "loop." The skill body is `SKILL.md`; deep knowledge lives in
`references/`; bundled verifier scripts live in `scripts/`; trigger/behavior evals
live in `evals/evals.json`.
```

with:

```markdown
`loop-builder` is a Claude Code **plugin** bundling peer skills under `skills/`:

- `skills/loop-builder/` — interviews the user and scaffolds a self-running agent
  "loop." Body is `SKILL.md`; deep knowledge in `references/`; bundled verifier and
  skill-bank scripts in `scripts/` (tested under `scripts/tests/`).
- `skills/feedback-to-issue/` — captures feedback and files it as a GitHub issue
  under the user's own account. Body is `SKILL.md`; playbook in `references/`;
  deterministic tooling in `scripts/feedback/` (tested under `scripts/tests/`).

The manifest lives in `.claude-plugin/`; trigger/behavior evals in `evals/evals.json`.
```

- [ ] **Step 2: Add the governing rule under "Skill authoring"**

Append to the `## Skill authoring` section:

```markdown
- **Skill vs. reference (what graduates):** a capability becomes its own
  `skills/<name>/` skill only if a user would trigger it *without* going through
  another skill ("report a bug" stands alone; "the Ralph pattern" does not).
  Reference knowledge stays nested under the owning skill's `references/`. Every
  graduated skill's `description` is always-on context in every session, so keep
  the bar high — graduate genuine standalone triggers only.
- **Cross-skill references:** when one skill must run another skill's bundled
  script, reference it via `${CLAUDE_PLUGIN_ROOT}/skills/<other>/…`. Within-skill
  references stay relative to the skill dir.
```

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): describe the plugin layout + skill-vs-reference rule

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Rewrite README as a plugin README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Produces: a plugin-level overview that links to per-skill docs and documents plugin install.

- [ ] **Step 1: Update the hero + "At a glance" to plugin framing**

Change the subtitle and badges so the project reads as a *plugin* containing skills (keep the no-emoji rule; badges/tables only). Update the hero line under the title from "A Claude Code skill that interviews you…" to describe a plugin bundling the `loop-builder` and `feedback-to-issue` skills. In the **At a glance** table, change the `Install` row from the `git clone … ~/.claude/skills/loop-builder` form to the plugin-install form (Step 2).

- [ ] **Step 2: Replace the Install section with plugin install**

Replace the install instructions with:

```markdown
### Install

```bash
# Add this repo as a plugin marketplace, then install the plugin
/plugin marketplace add AaronLPS/loop-builder
/plugin install loop-builder@loop-builder
```

The plugin bundles two skills:

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `loop-builder` | "automate / schedule / monitor this…" | Interviews you and scaffolds a self-running loop |
| `feedback-to-issue` | "report a bug / give feedback" | Files a sanitized GitHub issue under your own account |
```

(Keep the rest of the README — patterns, building blocks, etc. — they describe the `loop-builder` skill and remain valid. Update any in-body links that pointed at root `SKILL.md`/`references/…` to `skills/loop-builder/…`.)

- [ ] **Step 3: Verify no stale root-path links remain**

Run: `grep -nE "\]\((SKILL\.md|references/|scripts/)" README.md`
Expected: no hits, OR every hit rewritten to a `skills/<skill>/…` path. (Anchor links like `(#install)` are fine.)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): reframe as a plugin README with /plugin install

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Whole-plugin verification

**Files:** none (verification only)

**Interfaces:**
- Consumes: everything from Tasks 1–7.

- [ ] **Step 1: Full local test sweep (all suites green from new paths)**

Run:
```bash
bash skills/feedback-to-issue/scripts/tests/test_feedback.sh 2>&1 | tail -2
bash skills/loop-builder/scripts/tests/test_verifiers.sh   2>&1 | tail -2
bash skills/loop-builder/scripts/tests/test_skill_bank.sh  2>&1 | tail -2
```
Expected: each ends in `OK` (and the feedback suite reports `Ran 22 tests`).

- [ ] **Step 2: Confirm no stale references to old paths anywhere in the repo**

Run:
```bash
grep -rnE "(^|[^/])scripts/feedback/|(^|[^-])references/feedback-to-issue|scripts/tests/feedback" \
  --include='*.md' --include='*.sh' --include='*.py' --include='*.yml' \
  skills .github AGENTS.md README.md 2>/dev/null \
  | grep -v "CLAUDE_PLUGIN_ROOT" \
  | grep -v "skills/feedback-to-issue/references/feedback-to-issue.md"
```
Expected: no output (every remaining feedback reference is either the within-skill `scripts/feedback/cli.py` example inside the feedback skill, or a `${CLAUDE_PLUGIN_ROOT}`-rooted path).

- [ ] **Step 3: Install the plugin locally and confirm both skills load**

Per the claude-code-guide finding, validate the manifest by actually loading the plugin. Add the local repo as a marketplace and install:

```bash
# In a Claude Code session (run from the repo root, or pass its absolute path):
/plugin marketplace add .
/plugin install loop-builder@loop-builder
```

Then confirm both skills appear in the available-skills list: `loop-builder` and `feedback-to-issue` (invocable as `loop-builder:loop-builder` and `loop-builder:feedback-to-issue`).
Expected: plugin installs without a manifest/schema error; both skills are listed. If install errors on `marketplace.json` schema, fix the manifest (Task 1) and retry.

- [ ] **Step 4: Smoke-test the feedback CLI from its new home (dry-run, no issue created)**

Run (isolated HOME so no real log is touched):
```bash
HOME=$(mktemp -d) python3 skills/feedback-to-issue/scripts/feedback/cli.py \
  file --repo AaronLPS/loop-builder --title "smoke" --labels via-feedback-tool,bug --dry-run < /dev/null
```
Expected: a JSON result with `"issue": null` (gh dry-run command or URL fallback) — proving the moved module runs in place.

- [ ] **Step 5: Push the branch and open the PR**

```bash
git push -u origin restructure/multi-skill-plugin
gh pr create --title "Restructure loop-builder into a multi-skill plugin" \
  --body "Converts the repo into a Claude Code plugin bundling two peer skills (loop-builder, feedback-to-issue). Structural move + cross-skill rewiring only; no behavior change. All suites green; plugin installs locally. See docs/superpowers/specs/2026-06-25-multi-skill-plugin-design.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

---

## Self-Review

**Spec coverage:**
- Plugin manifest (plugin.json + marketplace.json) → Task 1 ✓
- feedback-to-issue graduates (SKILL.md + references + scripts + tests) → Task 2 ✓
- loop-builder's own references nested (+ its scripts/tests, the spec gap surfaced during planning) → Task 3 ✓
- Three-role cross-reference rewiring → Task 4 ✓
- CI path updates → Task 5 ✓
- Governing rule in AGENTS.md → Task 6 ✓
- Plugin README → Task 7 ✓
- Memory/state unaffected (kept `~/.loop-builder/`, env-var names) → Global Constraints + no task needed (nothing moves) ✓
- Migration acceptance test (green suite + skill load) → Task 8 ✓
- Out-of-scope (skill-bank graduation, multi-platform, deterministic auto-capture) → not implemented, by design ✓

**Placeholder scan:** No TBD/TODO; every code/edit step shows the exact before→after content or command. Step 2-style "verify it fails" steps are intentional TDD red checks.

**Type/path consistency:** `parents[1] / "feedback"` (Task 2 Step 3) matches the new test→module depth; `${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback` used identically in Task 2 Step 6, Task 4 Steps 1 & 3; skill dir names (`loop-builder`, `feedback-to-issue`) used consistently across manifest, CI, README, and cross-refs.

**Decision surfaced during planning (extends the spec):** loop-builder's *own* scripts/tests move under `skills/loop-builder/scripts/` (the spec layout only showed `SKILL.md + references/`). Keeping a shared root `scripts/` while everything else moved into `skills/` would contradict the self-contained-skills goal, so they move too. Flagged here for the reviewer.
