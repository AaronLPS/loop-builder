# skill-bank — design

Date: 2026-06-19
Status: approved (brainstorm) — pending implementation plan
Branch: `feature/skill-bank`

## Problem

When `loop-builder` designs a loop, it should stand on the shoulders of mature
open-source skills, plugins, and workflows rather than re-deriving capabilities
from scratch each time. Today the skill's reuse step (Phase 1.5) only surveys what
is **already installed** on the machine. It has no awareness of the broader
ecosystem of proven skill/plugin collections, so good prior art is invisible to it.

We want a curated, persisted "skill-bank": a place that catalogs high-quality
skill/plugin collections so that, while building a loop, the agent can broadly
search it, map entries to the loop's building blocks, and discuss with the user
which proven workflows to borrow — composing instead of reinventing.

## Goal

Extend `loop-builder` so its reuse survey draws on a curated catalog of external
capabilities in addition to installed ones, while preserving the skill's existing
discipline: named fallbacks, "verify unverified mechanics," and low per-run token
cost.

Success looks like: a loop-build request causes the agent to consult the skill-bank,
surface a relevant block-tagged shortlist with source + install pointers and a
fallback, and record the chosen entries in the loop's REUSE line and its `SKILL.md`.

## Decisions (locked during brainstorm)

1. **Storage form: index/catalog only.** Store metadata pointers, not vendored copies
   of skill content. Lightweight, easy to refresh, and avoids any license
   re-distribution concern. Actual borrowing pulls from the source repo at build time.
2. **Update mechanism: manual script refresh.** A `scripts/` refresh tool compares the
   index against current upstream and reports a diff; a maintainer/agent runs it.
   No scheduled automation in v1.
3. **Borrow semantics: recommend and record (pointer).** Selecting an entry produces a
   recommendation written into the REUSE line and the loop's `SKILL.md` (source,
   install pointer, named fallback). No fetch-and-inline of external code. Consistent
   with the existing Phase 1.5 and license-friendly.
4. **Catalog architecture: two-tier, block-tagged.** A small top-level `INDEX.md`
   (one row per entry, tagged by which of the six loop blocks it serves) is the
   searchable artifact loaded at survey time; optional per-entry detail files are read
   only when an entry is shortlisted. Mirrors the skill's progressive-disclosure and
   block-centric design, keeping per-run token cost minimal.

## Architecture

### Repository layout

```
references/skill-bank/
├── INDEX.md            searchable top-level index: one-row-per-entry markdown table,
│                       tagged by loop block
├── sources.yml         refresh-script input: the source repos, each with a pinned
│                       ref and a last-synced date
└── entries/<slug>.md   OPTIONAL per-entry detail (curated metadata, not code);
                        written only when an entry needs caveats; read on demand
scripts/
├── refresh_skill_bank.sh   pull upstream state, diff against INDEX, report staleness
└── tests/                  red-green tests + fixtures (existing convention)
```

All artifacts are metadata pointers. No external skill's actual code is vendored.

### INDEX.md entry schema

One row per entry. The agent loads only this small table during the reuse survey
(progressive disclosure, level 1).

| Field     | Meaning |
|-----------|---------|
| `name`    | entry name / slug |
| `type`    | `skill` \| `plugin` \| `mcp` \| `sub-agent` \| `workflow` |
| `blocks`  | which loop block(s) it can serve: (1) scheduling, (2) isolation, (3) skill/conventions, (4) connectors, (5) verifier, (6) state — same taxonomy Phase 1.5 already uses |
| `purpose` | one-line description |
| `source`  | repo URL (+ path within the repo) |
| `install` | pointer to how to obtain it (clone path / plugin marketplace / MCP config) — never inlined |
| `license` | SPDX id (e.g. `MIT`) — attribution/compliance cue before borrowing |
| `synced`  | upstream ref + sync date — the basis for staleness checks |

The `blocks` column is load-bearing: because Phase 1.5 already reasons block-by-block
about what can be reused, tagging the index by the same axis turns retrieval into a
cheap scan ("entries that serve block 5"). `license` and `synced` bake compliance and
freshness directly into the schema.

### Refresh mechanism — staleness checker, not a scraper

The source repos have heterogeneous structures (some `skills/` dirs, some plugin
manifests, some README-only), so reliable full auto-scraping is out of scope. The
script's job is **compare and report**; curation stays with the human/agent.

`refresh_skill_bank.sh`:
1. Reads `sources.yml`.
2. Fetches current upstream state per source (latest commit + skill/dir listing via
   the GitHub API).
3. Compares against what `INDEX.md` records.
4. Reports three diff classes:
   - upstream-added entries not yet in our index (candidates to include),
   - entries in our index that disappeared/renamed upstream (candidates to remove),
   - entries whose `synced` stamp is stale.

The maintainer/agent then curates the diff into `INDEX.md` — we list only the good
entries, not a full mirror. This is isomorphic to loop-builder's own philosophy: a
deterministic check plus human judgment. The seed `INDEX.md` is hand-curated now from
the v1 sources (standout entries per repo, not exhaustive).

Note (future, not v1): this refresh is itself a textbook loop use case and could later
be scaffolded by loop-builder as a scheduled refresh loop (dogfooding). v1 leaves the
seam but does not build it.

### Integration into the loop-building flow — extend Phase 1.5, no new phase

Phase 1.5 currently surveys installed capabilities via `find-skills`. It gains a
second source feeding the same block-mapping:

- **1.5a Installed** (current): skills/MCP/sub-agents already on the machine.
- **1.5b skill-bank** (new): search `references/skill-bank/INDEX.md` by block for
  borrowable candidates.

The shortlist presented to the user is tiered: **installed** (ready to use) then
**bank entries** (need installing/borrowing, shown with source + install pointer).
This matches the "discuss fully to choose" requirement. Each chosen entry is recorded
under the existing Phase 1.5 discipline in the REUSE line and the loop's `SKILL.md`:
source, install pointer, **named fallback**, and the "verify mechanics / don't bind to
unverified behavior" uncertainty flag (bank entries are externally evolving projects;
confirm against source before relying).

`SKILL.md` change is small: add the 1.5b sub-step text and a pointer to the INDEX. No
code is inlined, so it stays license-friendly.

## Testing

Following the existing `scripts/tests/` red-green convention:

- **Refresh-script test:** given a fixture `sources.yml` and fixture upstream state,
  assert the script reports the added/removed/stale diff classes correctly.
- **INDEX schema lint + test:** validate every row has the required columns, `license`
  is a valid SPDX id, and `blocks` tags are within the six-block set.
- **Behavior eval:** add one eval to `evals/evals.json` asserting that a loop-build
  request leads the agent to consult the skill-bank and recommend a relevant entry
  with a named fallback.

## v1 scope (YAGNI)

In scope:
- Seed `INDEX.md` curated from the five v1 source collections.
- `sources.yml` listing those five sources.
- `refresh_skill_bank.sh` (staleness checker) + its test.
- INDEX schema lint + test.
- Phase 1.5 extension (1.5b) + INDEX pointer in `SKILL.md`.
- One bank-consult behavior eval.

Out of scope for v1:
- Auto-scraping every skill in a source repo.
- Vendoring external skill content.
- Scheduled/automated refresh.
- Fetch-and-adapt inlining of external code.

### v1 source collections

- Everything Claude Code (ECC) — https://github.com/affaan-m/ecc
- Awesome Claude Skills — https://github.com/ComposioHQ/awesome-claude-skills
- Superpowers — https://github.com/obra/superpowers
- gstack — https://github.com/garrytan/gstack
- claude-for-legal — https://github.com/anthropics/claude-for-legal

## Non-goals / risks

- **Staleness is inherent** to an index of evolving repos; mitigated by the refresh
  diff + the `synced` stamp + the build-time "verify against source" flag, not by
  pretending the index is always current.
- **Curation cost**: the bank's value is selectivity, so adding entries is a
  judgment step, not an automated dump. Accepted deliberately.
- **License**: pointer-only storage avoids redistribution; the `license` column keeps
  attribution visible when a user chooses to borrow.
