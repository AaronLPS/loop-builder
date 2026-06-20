# skill-bank Semantic Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tier-aware skill-bank lookup with one operation — a semantic search sub-agent that reads the whole bank and returns a shortlist — and rename `INDEX.md` to `recommended.md` to reflect its new role.

**Architecture:** Keep the corpus (`recommended.md` + `catalog/*.md`) and all deterministic tooling. Add a bundled searcher prompt (`search-agent.md`). Rewrite Phase 1.5 to dispatch a general-purpose sub-agent with that prompt (it reads the bank in its own context, judges relevance semantically, returns a shortlist preferring curated standouts), with a direct-read fallback. Update evals and docs.

**Tech Stack:** Bash (existing tooling), markdown (prompt + data), JSON (evals). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-20-skill-bank-semantic-search-design.md`
**Branch:** `feature/skill-bank` (already checked out).

## Notes for the implementer
- **No emoji in any file** (`AGENTS.md`). Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- This builds on the existing skill-bank: `references/skill-bank/{INDEX.md,catalog/,sources.yml}` and `scripts/{lint_skill_bank_index.sh,refresh_skill_bank.sh,build_skill_bank_catalog.sh,format_catalog.sh,lint_skill_bank_catalog.sh}`, with `scripts/tests/test_skill_bank.sh`.
- The search is an LLM sub-agent — it is NOT unit-tested; the deterministic tests guard the corpus/tooling, and the evals guard the search behavior.

---

## File Structure

| Path | Responsibility | Action |
|------|----------------|--------|
| `references/skill-bank/INDEX.md` → `recommended.md` | curated standouts (the preferred set) | Rename + edit intro |
| `scripts/lint_skill_bank_index.sh` → `lint_skill_bank_recommended.sh` | lint the curated list | Rename + edit defaults |
| `references/skill-bank/search-agent.md` | the search sub-agent prompt | Create |
| `scripts/refresh_skill_bank.sh` | drift checker — default path update | Modify |
| `references/skill-bank/sources.yml` | comment mentions INDEX.md | Modify |
| `scripts/tests/test_skill_bank.sh` | linter calls + seeded-file path | Modify |
| `SKILL.md` | Phase 1.5 `1.5b` → dispatch searcher; todo note; checklist; map lead-in | Modify |
| `evals/evals.json` | ids 6 & 7 → search-sub-agent model | Modify |
| `README.md` | rename refs + tiers→search wording | Modify |

---

## Task 1: Rename INDEX → recommended (data file + linter) and update references

**Files:**
- Rename: `references/skill-bank/INDEX.md` → `references/skill-bank/recommended.md`
- Rename: `scripts/lint_skill_bank_index.sh` → `scripts/lint_skill_bank_recommended.sh`
- Modify: the renamed linter, `scripts/refresh_skill_bank.sh`, `references/skill-bank/sources.yml`, `scripts/tests/test_skill_bank.sh`

- [ ] **Step 1: Rename the two files with git**

```bash
git mv references/skill-bank/INDEX.md references/skill-bank/recommended.md
git mv scripts/lint_skill_bank_index.sh scripts/lint_skill_bank_recommended.sh
```

- [ ] **Step 2: Update the renamed linter's default path, header, and message**

In `scripts/lint_skill_bank_recommended.sh`:

Find the header comment line:
```bash
# Lint the skill-bank INDEX table. Every data row must have all 8 columns, a known
```
Replace with:
```bash
# Lint the skill-bank recommended list. Every data row must have all 8 columns, a known
```

Find:
```bash
FILE="references/skill-bank/INDEX.md"
```
Replace with:
```bash
FILE="references/skill-bank/recommended.md"
```

Find:
```bash
  echo "OK: skill-bank index clean ($row entries)"
```
Replace with:
```bash
  echo "OK: skill-bank recommended list clean ($row entries)"
```

- [ ] **Step 3: Update the `recommended.md` intro to the search model**

In `references/skill-bank/recommended.md`, find the title line:
```
# skill-bank index
```
Replace with:
```
# skill-bank — recommended (curated standouts)
```

Then find this exact passage (the two-tier note added earlier):
```
Sources and
the refresh procedure live in `sources.yml`. This file is **Tier 1** — the curated
standouts, loaded on every loop build. For comprehensive coverage, `catalog/<source>.md`
holds the full per-source listing (auto-generated), read on demand when these standouts
don't cover a block the loop needs.
```
Replace it with:
```
Sources and
the refresh procedure live in `sources.yml`. This file is the **curated standouts** —
the entries the skill-bank search sub-agent prefers. It is not loaded directly each
build; in Phase 1.5 loop-builder dispatches a searcher (see
`references/skill-bank/search-agent.md`) that reads this file plus the comprehensive
`catalog/<source>.md` listings and returns the best-fit shortlist.
```

- [ ] **Step 4: Update the refresh script's default path**

In `scripts/refresh_skill_bank.sh`, find:
```bash
INDEX="references/skill-bank/INDEX.md"
```
Replace with:
```bash
INDEX="references/skill-bank/recommended.md"
```

- [ ] **Step 5: Update the sources.yml comments**

In `references/skill-bank/sources.yml`, find:
```
#      and curate the reported diff into INDEX.md (we list only standout entries,
```
Replace with:
```
#      and curate the reported diff into recommended.md (we list only standout entries,
```

Then update the `awesome-claude-skills` note. Replace these exact substrings (each unique):
- `An entry's INDEX` + `source` → `An entry's recommended-list` + `source`
  (i.e. the line `  # Note: this is an aggregator list. An entry's INDEX `source` may point at the`
  becomes `  # Note: this is an aggregator list. An entry's recommended-list `source` may point at the`)
- `# Tier-2: not cleanly enumerable in v1` → `# Catalog: not cleanly enumerable in v1`
- `Stays Tier-1 curated-only.` → `Stays curated-only (recommended list).`

- [ ] **Step 6: Update the test harness references**

In `scripts/tests/test_skill_bank.sh`, replace every occurrence of `lint_skill_bank_index.sh` with `lint_skill_bank_recommended.sh` (there are several in the lint cases).

Then find:
```bash
# the real seeded index must always lint clean
bash "$SCRIPTS/lint_skill_bank_recommended.sh" --file "$ROOT/references/skill-bank/INDEX.md" >/dev/null 2>&1
check "lint: seeded INDEX.md is clean" 0 $?
```
Replace with:
```bash
# the real curated list must always lint clean
bash "$SCRIPTS/lint_skill_bank_recommended.sh" --file "$ROOT/references/skill-bank/recommended.md" >/dev/null 2>&1
check "lint: seeded recommended.md is clean" 0 $?
```

(The fixture files `index_good.md` / `index_bad.md` keep their names — they are internal linter fixtures, used by both the recommended-linter cases and the refresh `--index` cases; renaming them is unnecessary churn.)

- [ ] **Step 7: Run the full suite**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: `ALL TESTS PASSED` (the renamed linter validates `recommended.md` and the fixtures; refresh cases unchanged).

Also confirm the CLI default works:
Run: `bash scripts/lint_skill_bank_recommended.sh`
Expected: `OK: skill-bank recommended list clean (16 entries)`, exit 0.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(skill-bank): rename INDEX.md -> recommended.md and its linter"
```

---

## Task 2: Add the search sub-agent prompt

**Files:**
- Create: `references/skill-bank/search-agent.md`

- [ ] **Step 1: Create the searcher prompt**

Create `references/skill-bank/search-agent.md` with this content:

```markdown
# skill-bank search agent

You are the **skill-bank searcher** for loop-builder. Given a loop's reuse needs, find
the best-fitting external skills/plugins/workflows in the bank and return a short
shortlist. Judge relevance by understanding each entry's description — not by keyword
match (a "red-green TDD" skill can be the right verifier even if it never says
"verifier").

## Inputs (provided by the dispatcher)

A list of the loop's block needs, for example:
- "verifier (block 5): confirm a docs site has no broken links"
- "connector (block 4): read and update GitHub issues"

## What to read

- `references/skill-bank/recommended.md` — the curated standouts (the preferred set).
- `references/skill-bank/catalog/*.md` — the comprehensive per-source listings
  (name + one-line description). Read these to widen beyond the standouts.

## How to choose

1. For each need, look in `recommended.md` first. If a standout genuinely fits, prefer it.
2. If the standouts don't cover a need, search the catalogs and surface the best
   semantic match(es).
3. Recommend only what genuinely helps — 1-3 candidates per need is plenty. If nothing
   fits, say so.

## Output — return exactly this shape

For each need:

```
NEED: <the need>
- <name> | source: <repo or url> | block: <n> | recommended: yes|no
  why: <one line on why it fits>
```

If nothing fits a need, write: `none applicable — <reason>`.

## Rules

- **Recommend-and-record only.** Do not fetch, clone, or inline any external code —
  surface the pointer; installing/borrowing is the main agent's call.
- Note that each entry's license and exact mechanics must be confirmed against its
  source before wiring it in (bank entries are externally evolving).
- Keep the shortlist short and high-signal; prefer recommended standouts when they fit.
```

- [ ] **Step 2: Commit**

```bash
git add references/skill-bank/search-agent.md
git commit -m "feat(skill-bank): add search sub-agent prompt"
```

---

## Task 3: Rewrite Phase 1.5 to dispatch the searcher (`SKILL.md`)

**Files:**
- Modify: `SKILL.md` (the `1.5b` block, the Process todo note, the checklist gate, the map lead-in)

- [ ] **Step 1: Replace the `1.5b` block**

In `SKILL.md`, find this exact passage:

```
**1.5b — skill-bank — do not skip, even if 1.5a already seems to cover a block.** The
bank has two tiers; use them in order:

*Tier 1 (always).* **Read `references/skill-bank/INDEX.md`** — a curated, block-tagged
catalog of standout external skills/plugins/workflows — and scan it for the blocks
this loop needs.

*Tier 2 (when Tier 1 falls short).* For any block the loop needs that the Tier-1
standouts don't cover well, **read the relevant `references/skill-bank/catalog/<source>.md`**
— the full per-source listing (name + one-line description) — and judge candidates by
their description. Widen only the *uncovered* block(s), and only the source(s)
plausibly holding them — not every catalog. Record "skill-bank: none applicable —
<reason>" only *after* this widening, never before.

Borrow semantics are unchanged: recommend-and-record only (surface source + install
pointer + a named fallback; never inline external code), and confirm license and
mechanics against source at borrow time. The point is to surface proven prior art
before you settle, so you compose instead of rebuild — an installed capability
covering a block is exactly when people skip this and miss a better-fitting borrow.
```

Replace it with:

```
**1.5b — skill-bank — do not skip, even if 1.5a already seems to cover a block.**
**Search the bank** for capabilities matching the blocks this loop needs. The bank is
large, so don't read it inline — dispatch a search sub-agent:

Dispatch a general-purpose sub-agent using the prompt in
`references/skill-bank/search-agent.md`, passing the loop's block needs (e.g. "verifier
for X; connector for Y"). It reads the whole bank — `references/skill-bank/recommended.md`
(curated standouts) and `references/skill-bank/catalog/*.md` (the comprehensive
listings) — in its own context, judges relevance semantically, and returns a short
shortlist per need: the best-fit entries (name, source, block, one-line why, and whether
it's a recommended standout), or "none applicable — <reason>". It prefers standouts when
they fit and only reaches into the catalogs when they don't.

*Fallback (if sub-agents aren't available):* read `references/skill-bank/recommended.md`
directly, and scan a specific `catalog/<source>.md` for any block the standouts don't
cover — same discipline.

Borrow from the shortlist: recommend-and-record only (surface source + install pointer +
a named fallback; never inline external code), confirming license and mechanics against
source at borrow time. The point is to surface proven prior art before you settle, so
you compose instead of rebuild.
```

- [ ] **Step 2: Update the Process todo note**

In `SKILL.md`, find:

```
Create a TodoWrite item per phase so nothing is skipped — and a **distinct** item for
the Phase 1.5 skill-bank search (`references/skill-bank/INDEX.md`), the step most
easily missed because installed capabilities are already in view and the bank is not.
```

Replace with:

```
Create a TodoWrite item per phase so nothing is skipped — and a **distinct** item for
the Phase 1.5 skill-bank search (dispatch the searcher over `references/skill-bank/`),
the step most easily missed because installed capabilities are already in view and the
bank is not.
```

- [ ] **Step 3: Update the checklist gate**

In `SKILL.md`, find:

```
- [ ] **skill-bank consulted** (1.5b): Tier-1 `INDEX.md` scanned; for any block its standouts don't cover, the relevant Tier-2 `catalog/<source>.md` was read. "none applicable — <reason>" recorded only after that widening. Not skippable.
```

Replace with:

```
- [ ] **skill-bank searched** (1.5b): the search sub-agent (or the direct-read fallback) was run over `recommended.md` + `catalog/*.md`; relevant entries surfaced, or "none applicable — <reason>" recorded. Not skippable.
```

- [ ] **Step 4: Update the "Map what you find" lead-in**

In `SKILL.md`, find:

```
Map what you find — from **both** the installed set (1.5a) and the skill-bank INDEX
(1.5b) — to the blocks the loop needs; recommend only what **genuinely changes the
design**, not an exhaustive inventory:
```

Replace with:

```
Map what you find — from **both** the installed set (1.5a) and the skill-bank search
results (1.5b) — to the blocks the loop needs; recommend only what **genuinely changes
the design**, not an exhaustive inventory:
```

- [ ] **Step 4.5: Update worked-example REUSE lines that mention INDEX**

The three worked examples each have a `REUSE (skill-bank):` line that references the old INDEX. Replace these exact substrings (each is unique; surrounding whitespace is unaffected):

- `checked INDEX block 5; nothing fits better` → `searched the bank; nothing fits better`
- `sub-agent (checked INDEX block 5)` → `sub-agent (searched the bank)`
- `surfaced from INDEX for root-causing` → `surfaced by the bank search for root-causing`

- [ ] **Step 5: Verify and commit**

Run: `grep -n "search-agent.md" SKILL.md && grep -c "INDEX" SKILL.md && wc -l SKILL.md`
Expected: the searcher reference prints; the `INDEX` count (uppercase, matches both `INDEX.md` and bare `INDEX`) is `0` — no stale references remain; `SKILL.md` under 500 lines.

```bash
git add SKILL.md
git commit -m "feat(skill-bank): Phase 1.5 dispatches the search sub-agent"
```

---

## Task 4: Update the behavior evals (ids 6 & 7)

**Files:**
- Modify: `evals/evals.json`

- [ ] **Step 1: Replace the id 6 object**

In `evals/evals.json`, find the object with `"id": 6` (its `prompt` is about an overnight broken-links agent) and replace the WHOLE object with:

```json
    {
      "id": 6,
      "prompt": "I want to set up an overnight agent that keeps our docs site's broken links fixed, and I'd rather reuse good existing tooling than build link-checking from scratch",
      "expected_output": "Triggers loop-builder; in Phase 1.5 it searches the skill-bank by dispatching the search sub-agent (references/skill-bank/search-agent.md) over recommended.md + catalog/*.md (or uses the direct-read fallback), and records the returned candidates with source + a named fallback. Recommends, never inlines external code.",
      "files": [],
      "expectations": [
        "The loop-builder skill is invoked",
        "Phase 1.5 searches the skill-bank by dispatching the search sub-agent (or the documented direct-read fallback), rather than only surveying installed skills",
        "The search covers the whole bank: references/skill-bank/recommended.md and the comprehensive references/skill-bank/catalog/*.md",
        "At least one returned candidate is mapped to a specific loop block (e.g. verifier or connector) with a named fallback",
        "External code is recommended/referenced, never inlined into the scaffolded loop",
        "The recommendation carries the 'verify license and mechanics against source' caution"
      ]
    }
```

- [ ] **Step 2: Replace the id 7 object**

Find the object with `"id": 7` and replace the WHOLE object with:

```json
    {
      "id": 7,
      "prompt": "I need a weekly agent that proofreads our changelog entries for tone and house style before release — and I'd like to reuse a proven writing/editing skill rather than invent a style checker, even a fairly niche one",
      "expected_output": "Triggers loop-builder; the Phase 1.5 search sub-agent finds no curated standout for the 'style/editing verifier' need, so it surfaces a relevant entry from the comprehensive catalogs by semantic match (or records 'none applicable' after searching). Prefers a recommended standout when one fits; recommends, never inlines.",
      "files": [],
      "expectations": [
        "The loop-builder skill is invoked",
        "Phase 1.5 dispatches the skill-bank search sub-agent (or the direct-read fallback)",
        "Because no curated standout in recommended.md covers the need, the search surfaces a candidate from the comprehensive catalog/*.md by semantic relevance (matching meaning, not just keywords) — or records 'none applicable' only after searching the catalogs",
        "A recommended standout is preferred when one genuinely fits",
        "Each surfaced entry is recorded with its source and a named fallback; external code is never inlined",
        "The recommendation carries the 'verify against source' caution"
      ]
    }
```

- [ ] **Step 3: Verify JSON parses**

Run: `python3 -c "import json; d=json.load(open('evals/evals.json')); print('valid ·', len(d['evals']), 'evals')"`
Expected: `valid · 7 evals`

- [ ] **Step 4: Commit**

```bash
git add evals/evals.json
git commit -m "test(skill-bank): update bank-consult evals to the search-sub-agent model"
```

---

## Task 5: Update README to the search model

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the repo-layout block**

In `README.md`, read the repository-layout code fence. Find the skill-bank subtree and scripts list (it currently labels things "Tier 1"/"Tier 2" and lists `INDEX.md` / `lint_skill_bank_index.sh`). Replace that region with:

```
│   └── skill-bank/                         catalog of borrowable external skills/plugins
│       ├── recommended.md                  curated standouts (preferred by the search sub-agent)
│       ├── catalog/                        comprehensive per-source listings (searched on demand)
│       ├── search-agent.md                 prompt for the skill-bank search sub-agent
│       └── sources.yml                     upstream sources + refresh/build procedure
├── scripts/
│   ├── verifier_template.sh               generic predicate runner (exits non-zero on fail)
│   ├── verify_no_p1_unassigned.sh         worked example (operates on gh-style JSON)
│   ├── lint_skill_bank_recommended.sh     validates the curated recommended-list schema
│   ├── refresh_skill_bank.sh              reports recommended-list drift vs upstream
│   ├── format_catalog.sh                  SKILL.md frontmatter -> catalog rows
│   ├── build_skill_bank_catalog.sh        generate per-source catalogs from upstream
│   ├── lint_skill_bank_catalog.sh         validates catalog schema
│   └── tests/                             red-green tests + fixtures
```

If the actual text differs slightly, adapt to it while preserving intent: rename `INDEX.md`→`recommended.md` and `lint_skill_bank_index.sh`→`lint_skill_bank_recommended.sh`; add `search-agent.md`; drop the "Tier 1/Tier 2" labels in favor of "curated standouts" / "comprehensive ... searched".

- [ ] **Step 2: Update any prose mention of the bank lookup**

Search the README for `INDEX.md` and `Tier`:
Run: `grep -n "INDEX.md\|Tier 1\|Tier 2" README.md`
For each remaining hit, reword to the search model (the bank is searched by a sub-agent over `recommended.md` + `catalog/*.md`). If there are none beyond the layout block, nothing further is needed.

- [ ] **Step 3: Verify both suites pass + commit**

Run: `bash scripts/tests/test_verifiers.sh && bash scripts/tests/test_skill_bank.sh`
Expected: both print `ALL TESTS PASSED`.

```bash
git add README.md
git commit -m "docs(skill-bank): document the search-sub-agent model"
```

---

## Final verification

- [ ] **Run everything**

Run:
```bash
bash scripts/tests/test_verifiers.sh && bash scripts/tests/test_skill_bank.sh
bash scripts/lint_skill_bank_recommended.sh
for c in references/skill-bank/catalog/*.md; do bash scripts/lint_skill_bank_catalog.sh --file "$c"; done
python3 -c "import json; json.load(open('evals/evals.json'))" && echo "evals OK"
echo "stale INDEX refs in code/docs:"; grep -rn "INDEX.md\|lint_skill_bank_index" SKILL.md README.md scripts references/skill-bank || echo "none"
wc -l SKILL.md
```
Expected: both suites `ALL TESTS PASSED`; recommended list + every catalog `clean`; evals OK; **no** stale `INDEX.md`/`lint_skill_bank_index` references in `SKILL.md`, `README.md`, `scripts/`, or `references/skill-bank/`; `SKILL.md` under 500 lines.

(Historical `docs/superpowers/specs/` and `plans/` files may still mention INDEX.md — those are frozen records and are intentionally left unchanged.)
```
