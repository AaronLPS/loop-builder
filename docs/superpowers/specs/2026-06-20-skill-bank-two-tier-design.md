# skill-bank two-tier catalog — design

Date: 2026-06-20
Status: approved (brainstorm) — pending implementation plan
Branch: `feature/skill-bank`
Builds on: `docs/superpowers/specs/2026-06-19-skill-bank-design.md`

## Problem

The v1 skill-bank seeds a curated `INDEX.md` of ~16 standout entries (2-4 per
source). Curation gives high signal and low per-build token cost, but it trades away
**recall**: if the skill that would fit a given loop isn't in the shortlist, the agent
consults the bank, finds nothing relevant, and rebuilds anyway — quietly defeating the
"stand on the shoulders of giants" goal. A bigger flat INDEX would fix recall but tax
every loop build, since the INDEX is loaded in Phase 1.5 on every invocation.

## Goal

Make the bank comprehensive without inflating per-build token cost, by splitting it
into two tiers: a compact curated index loaded every build, and a complete per-source
listing read only on demand when the curated tier doesn't cover a needed block.

Success: for a loop needing a block the curated standouts don't cover, the agent reads
the relevant full listing, surfaces a fitting candidate (or records "none applicable"
only after widening) — while builds whose blocks are already covered never load the
comprehensive tier.

## Decisions (locked during brainstorm)

1. **Trigger = conditional/auto.** Scan Tier 1 first; pull a Tier-2 listing only when a
   block the loop needs is not well-covered by Tier-1 standouts. This rule is what
   keeps per-build cost flat — it is not "always load everything."
2. **Tier-2 content = name + one-line description.** Auto-pulled from each skill's
   frontmatter `description`. No license/block columns; those are confirmed at borrow
   time, exactly as Tier 1 already requires. Enough signal to judge block-relevance
   without opening each skill.
3. **Coverage = enumerable sources only.** A source gets a Tier-2 file only if it has a
   machine-listable skills directory. Aggregator/README-only sources stay Tier-1
   curated-only, noted explicitly.
4. **Generation is a separate script.** Tier-2 building (generate files) is a different
   job from the existing refresh (diff Tier 1), so it lives in its own script.

## Architecture

### Two tiers, two artifacts

```
references/skill-bank/
├── INDEX.md            TIER 1 — curated, block-tagged standouts (loaded every build)
├── sources.yml         gains an `enumerate:` field per source
└── catalog/            TIER 2 — comprehensive per-source listings (read on demand)
    ├── superpowers.md
    ├── ecc.md
    ├── gstack.md
    └── claude-for-legal.md
```

- **Tier 1** is the hand-picked standouts: high signal, always loaded in Phase 1.5.
- **Tier 2** is the complete candidate pool per source: high recall, read on demand.
- **Per-source files** (not one big catalog): when widening for a block, the agent
  reads only the one or two relevant source files, never the whole catalog. Refresh
  regenerates each source independently.
- Promoting a Tier-2 entry up into Tier 1 is the human/agent curation act.

### Tier-2 file format

Auto-generated, lightweight, two columns:

```markdown
# superpowers — full catalog (auto-generated; do not hand-edit)
# source: https://github.com/obra/superpowers · synced: obra/superpowers@main 2026-06-20

| name | description |
|------|-------------|
| superpowers:brainstorming | Use before any creative work — explores intent... |
| superpowers:debugging     | Use when encountering any bug or test failure... |
```

`name` is `<source-key>:<slug>` (same convention as INDEX). `description` is the
skill's frontmatter `description`, collapsed to a single line. A `|` inside a
description is replaced with `/` so it cannot break the table.

### sources.yml: the `enumerate` field

Each source gains `enumerate:` — the repo path whose subdirectories are skills (e.g.
`skills`), or `-` for sources that cannot be cleanly enumerated. The builder uses this
to decide whether (and how) to produce a Tier-2 file. README-only/aggregator sources
(`enumerate: -`, e.g. awesome-claude-skills) are skipped and remain Tier-1 only.

## Generation: `scripts/build_skill_bank_catalog.sh`

A new script, separate from `refresh_skill_bank.sh` (which diffs Tier 1). For each
source with an `enumerate:` path it:

1. lists the skill directories (`gh api repos/<owner>/<repo>/contents/<path>`),
2. fetches each skill's `SKILL.md` frontmatter and extracts the `description` first
   line,
3. writes `catalog/<key>.md` (header + the two-column table).

**Honesty split (same as refresh):** the tested core is a pure formatter — given a
list of `(name, raw SKILL.md text)` it produces the catalog table, handling a missing
`description` (emit a placeholder like `(no description)`) and a multi-line/folded
`description` (collapse to one line). The `gh`/raw-fetch network calls are a thin,
documented adapter and are not unit-tested. Sources with `enumerate: -` are skipped
with a printed notice.

The committed seed `catalog/*.md` files are generated once during implementation for
the enumerable sources, then guarded by tests.

## Phase 1.5 two-tier flow (SKILL.md change)

`1.5b` becomes two steps:

```
1.5b-i   Scan Tier 1 (INDEX.md) by the blocks this loop needs.   [unchanged]
1.5b-ii  For any needed block the Tier-1 standouts do NOT cover well:
         read the relevant Tier-2 catalog/<key>.md (the source(s) plausibly
         holding that block — not all of them), judge candidates by their
         description, and surface matches.
         Record "skill-bank: none applicable — <reason>" only AFTER this
         widening, not before.
```

Guardrail that preserves the token savings: **widen only the uncovered block(s), only
the plausibly-relevant source(s)** — never "read every catalog." Borrow semantics are
unchanged (recommend-and-record; license and mechanics verified against source at
borrow time). The Phase 1.5 checklist gate is updated to reflect that "none
applicable" requires the Tier-2 widening first.

## Testing

- **Generator formatter test** (red-green, `scripts/tests/`): fixture
  `(name, frontmatter)` inputs produce exact catalog rows; covers a missing
  description and a multi-line/folded description, and a `|` inside a description.
- **Catalog lint:** a schema check (header present; two columns; `<key>:<slug>` name
  format) added to `test_skill_bank.sh`, guarding the committed seed catalogs.
- **Behavior eval** (`evals/evals.json`, new id 7): a request where Tier-1 standouts
  do not cover a needed block asserts the agent escalates to a Tier-2 catalog and
  surfaces a candidate (or records "none applicable" only after widening).

## Scope (v1 of the two-tier extension)

In scope:
- `references/skill-bank/catalog/<key>.md` for each enumerable source (seed,
  generated once).
- `scripts/build_skill_bank_catalog.sh` (formatter core + network adapter) + tests +
  fixtures.
- `sources.yml` gains `enumerate:` per source.
- `SKILL.md` Phase 1.5 `1.5b` two-step + checklist gate update.
- `INDEX.md` header notes the two tiers and points at `catalog/`.
- `evals/evals.json` escalation eval; `README.md` layout update.

Out of scope (YAGNI):
- Auto-tagging Tier-2 entries by loop block.
- Enumerating aggregator/README-only sources.
- Any live network fetch during a loop build — Tier 2 is read from committed files
  only; refreshing catalogs is a separate manual step.
- Per-entry license/block columns in Tier 2 (confirmed at borrow time).

## Non-goals / risks

- **Tier-2 staleness:** catalogs are generated snapshots, regenerated manually like
  the Tier-1 refresh. The `synced` header line records the snapshot; borrow-time
  verification against source remains the durable control.
- **Description quality varies upstream:** some skills have terse or marketing-style
  descriptions. The agent judges relevance from them but always confirms against
  source before borrowing, so a weak description costs recall, not correctness.
- **Widening discipline depends on the agent honoring the "uncovered block only"
  rule.** The SKILL.md wording and the eval guard this; if it over-widens, the cost is
  tokens, not wrong output.
```
