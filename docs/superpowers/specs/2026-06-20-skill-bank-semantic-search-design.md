# skill-bank semantic search — design

Date: 2026-06-20
Status: approved (brainstorm) — pending implementation plan
Branch: `feature/skill-bank`
Supersedes the query model of: `2026-06-20-skill-bank-two-tier-design.md`

## Problem

The bank's retrieval has been either lexical or curation-bound:
- The curated `INDEX.md` (16 standouts) is high-signal but narrow — it can only surface what a human pre-picked.
- The comprehensive `catalog/*.md` (285 entries) has recall but no block index, so reaching it meant either loading everything (expensive) or a keyword filter (lexical — a TDD skill described as "red-green discipline" never matches a search for "verifier").

The two-tier split existed to manage token cost, not because two tiers are inherently good. The real need is: **search the whole bank with understanding, cheaply.**

## Goal

Replace the multi-step, tier-aware lookup with a single agent-facing operation —
"search the skill-bank" — that uses semantic (LLM) matching for quality and stays
token-bounded by running the full-bank read inside a disposable sub-agent. Preserve
curation as a "recommended" preference, and keep the corpus and tooling we already
built.

Success: during loop design (Phase 1.5), loop-builder dispatches one search sub-agent
that reads the whole bank, returns a small semantically-relevant shortlist (preferring
curated standouts), and the main agent borrows from it — surfacing fitting entries that
a keyword search or the 16-entry curated list would have missed.

## Decisions (locked during brainstorm)

1. **Search = sub-agent semantic search.** Phase 1.5 dispatches a sub-agent that reads
   the bank in its own context and returns a shortlist judged by LLM understanding,
   not keyword grep. The main agent pays only for the dispatch + the shortlist.
2. **Curation kept as a "recommended" preference.** The curated standouts are the
   recommended set; the searcher is instructed to prefer them when they fit. No
   separate flag file — membership in the curated file is the signal.
3. **Rename `INDEX.md` → `recommended.md`.** Its role is no longer a scannable index;
   it is the curated/preferred subset the searcher reads. Update all references.
4. **Keep the corpus and deterministic tooling.** `catalog/*.md`, the builder, the
   formatter, and the linters stay. Only the *query method* (Phase 1.5 wiring)
   changes; nothing tested is torn down (the index linter is renamed, not removed).

## Architecture

### Storage (the bank — corpus for the searcher)

```
references/skill-bank/
├── recommended.md       curated standouts (renamed from INDEX.md); the "prefer these" set
├── catalog/<source>.md  comprehensive per-source listings (name + description)
├── sources.yml          unchanged
└── search-agent.md      NEW: the bundled prompt for the search sub-agent
```

Both `recommended.md` and `catalog/*.md` are read by the search sub-agent. The main
loop-builder agent reads neither directly in the normal path.

### The search sub-agent

`references/skill-bank/search-agent.md` is a bundled prompt template. In Phase 1.5,
loop-builder dispatches a general-purpose sub-agent with it, parameterized by the
loop's block needs. The sub-agent:

1. reads `references/skill-bank/recommended.md` and `references/skill-bank/catalog/*.md`
   (a few thousand tokens, in its own disposable context),
2. judges, per stated need, which entries fit — semantically, by understanding each
   description, not by keyword match,
3. returns a compact shortlist: for each surfaced entry — name, source, the loop block
   it serves, a one-line why, and whether it is a curated standout (from
   `recommended.md`). It prefers standouts when they genuinely fit and only reaches
   into the comprehensive catalog when they do not.

The main agent receives only the shortlist and borrows as usual: recommend-and-record,
named fallback, license/mechanics confirmed against source at borrow time.

**Timing:** this runs once during loop *design* (Phase 1.5), not during the built
loop's execution. A single sub-agent dispatch per loop-creation session is negligible.

### Fallback (graceful degradation)

If the sub-agent mechanism is unavailable, loop-builder degrades to reading
`recommended.md` directly (always cheap) and may scan a specific `catalog/<source>.md`
for an uncovered block. This mirrors the prior behavior and honors the skill's
"named fallback" discipline.

### Phase 1.5 change (SKILL.md)

Replace the current two-step `1.5b` ("scan Tier-1 INDEX, then conditionally read a
Tier-2 catalog") with a single step: **dispatch the skill-bank search sub-agent**
(`references/skill-bank/search-agent.md`) with the loop's block needs, then borrow
from its shortlist. The "do not skip" framing and recommend-and-record/fallback rules
carry over. The checklist gate becomes "skill-bank searched (sub-agent or fallback);
relevant entries surfaced or 'none applicable' recorded."

### Renames and reference updates

- `references/skill-bank/INDEX.md` → `references/skill-bank/recommended.md`
- `scripts/lint_skill_bank_index.sh` → `scripts/lint_skill_bank_recommended.sh`
  (logic unchanged; default path and messages updated)
- Update references in: `scripts/refresh_skill_bank.sh`, `scripts/tests/test_skill_bank.sh`,
  `scripts/tests/fixtures/skill_bank/` (rename index fixtures to recommended), `SKILL.md`,
  `README.md`, and the `catalog/*.md` builder header note if it points at INDEX.
- The block-tag column in `recommended.md` is no longer required by the query path; keep
  it as harmless extra signal for the searcher.

## Testing

- **Deterministic tests stay:** catalog formatter golden test, catalog linter,
  recommended linter (renamed index linter), refresh drift checker — all keep passing
  after the rename.
- **The search is an LLM** — not unit-tested. It is guarded by the behavior evals.
  Both bank-consult evals (`evals/evals.json` ids 6 and 7) currently reference the old
  INDEX/two-tier model and must be updated to the search-sub-agent model: id 6 asserts
  Phase 1.5 dispatches the search sub-agent (or fallback) rather than scanning INDEX;
  id 7 asserts that a loop whose need isn't in the curated standouts still surfaces a
  relevant comprehensive-catalog entry via the searcher, preferring a standout when one
  fits.

## Scope

In scope:
- Rename `INDEX.md` → `recommended.md` and `lint_skill_bank_index.sh` →
  `lint_skill_bank_recommended.sh`, with all reference/fixture/test updates green.
- Add `references/skill-bank/search-agent.md` (the searcher prompt).
- Rewrite Phase 1.5 `1.5b` in `SKILL.md` to dispatch the searcher (with the fallback),
  and update the checklist gate.
- Update the behavior eval to assert the search-sub-agent path.
- Update `README.md` layout/wording.

Out of scope (YAGNI):
- Embedding/vector search.
- Searching during the built loop's execution (it is a design-time step).
- Auto block-tagging; enumerating non-enumerable sources (unchanged from prior scope).
- Removing the comprehensive catalogs or the curated set — both remain as corpus.

## Non-goals / risks

- **Non-determinism:** an LLM searcher varies run to run. Mitigated by a tight
  `search-agent.md` prompt (explicit output shape, "prefer recommended", "only reach
  into the catalog when standouts don't fit") and the behavioral eval.
- **Sub-agent dispatch cost:** one dispatch per loop-design session — acceptable, and
  far cheaper than loading the full catalog into the main context every build.
- **Searcher ignoring the recommended preference:** the prompt enforces it and the
  eval checks that a fitting standout is surfaced first.
- **Mechanic uncertainty:** sub-agent dispatch is a harness capability; the skill keeps
  the direct-read fallback so a cold start still works if it's unavailable.
