# skill-bank catalog: multi-path enumeration + per-source ref

**Date:** 2026-06-20
**Status:** approved (design)
**Branch:** `feature/catalog-multipath-ref`

## Problem

`references/skill-bank/catalog/` holds full auto-generated catalogs for only two of
the five sources in `sources.yml` (`superpowers`, `ecc`). The other three are
`enumerate: "-"` (curated-only) because `scripts/build_skill_bank_catalog.sh` can
enumerate only a **single** path per source and **hardcodes `ref=main`**:

- **gstack** (`garrytan/gstack`) — skills sit at the repo root, mixed among ~70
  non-skill dirs.
- **claude-for-legal** (`anthropics/claude-for-legal`) — skills live under
  `<area>/skills/<slug>` across nine legal areas; no single root.
- **awesome-claude-skills** (`ComposioHQ/awesome-claude-skills`) — default branch is
  `master`, not `main`.

The catalogs are comprehensive mirrors read on demand by the skill-bank search
sub-agent; `recommended.md` (curated standouts) is separate and unaffected.

## Goal

Generate full catalogs for all three sources by giving the builder two
backward-compatible capabilities: multi-path enumeration and a per-source ref.

## Decisions

- **Scope:** all three sources (clears the curated-only backlog).
- **Multi-path schema:** keep one `enumerate:` key; allow multiple
  whitespace-separated paths. Chosen over a YAML block list because the builder's
  parser is hand-rolled `awk`, not a real YAML library — space-separated keeps the
  parser change minimal and stays backward-compatible with existing single-path
  entries.
- **gstack** needs no multi-path: the builder already filters by SKILL.md presence,
  so `enumerate: "."` over the root yields just the skill dirs (~30).
- **awesome-claude-skills:** enumerate the **root only** (`ref: master`) — the ~25
  distinct standout skills (artifacts-builder, mcp-builder, skill-creator,
  canvas-design, …). The 833 auto-generated `composio-skills/*-automation` wrappers
  are **excluded** as low-signal bulk (ecc is already 271 rows).
- **Slug naming:** claude-for-legal has real cross-area slug collisions
  (`cold-start-interview`, `customize`, `matter-workspace`, `policy-monitor`,
  `reg-gap-analysis`, `use-case-triage` each recur in 6+ areas). When a source has
  **more than one** enumerate path, prefix each slug with the path's first component
  → `claude-for-legal:ip-legal/cease-desist`. Single-path sources keep bare slugs, so
  existing catalogs are unchanged.

## Schema (`references/skill-bank/sources.yml`)

```yaml
- key: gstack
  repo: https://github.com/garrytan/gstack
  enumerate: "."
  ref: main
  list: "..."

- key: claude-for-legal
  repo: https://github.com/anthropics/claude-for-legal
  enumerate: "ai-governance-legal/skills commercial-legal/skills corporate-legal/skills employment-legal/skills ip-legal/skills litigation-legal/skills privacy-legal/skills product-legal/skills regulatory-legal/skills"
  ref: main
  list: "..."

- key: awesome-claude-skills
  repo: https://github.com/ComposioHQ/awesome-claude-skills
  enumerate: "."
  ref: master
  list: "..."
```

`ref:` is **optional**, defaulting to `main`; existing entries need no `ref:` line.

## Builder (`scripts/build_skill_bank_catalog.sh`)

The builder remains the (untested) network adapter; `format_catalog.sh` — the
unit-tested formatting core — is untouched.

1. **Parse `ref`** per source (awk), default `main`.
2. **Per-source ref** flows into three places: the `gh api repos/<owner>/<path>?ref=<ref>`
   list call, the `raw.githubusercontent.com/<owner>/<ref>/<prefix><slug>/SKILL.md`
   fetch, and the catalog header `synced: <owner>@<ref> <date>`.
3. **Multi-path loop:** split `enumerate` on whitespace into an array; record
   `multi = (count > 1)`. For each path `P`:
   - `P == "."` → API `contents`, raw prefix `""`, slug prefix `""`.
   - else → API `contents/P`, raw prefix `"P/"`, slug prefix `multi ? "${P%%/*}/" : ""`.
   - For each dir `D` under `P` that has a `SKILL.md`, emit
     `<key>:<slug-prefix><D><TAB><tmpfile>` into the single per-source input file, so
     all paths feed one `format_catalog.sh` invocation and one `catalog/<key>.md`.

## Output

- `catalog/gstack.md` — ~30 rows, bare slugs.
- `catalog/claude-for-legal.md` — ~110 rows, area-qualified slugs.
- `catalog/awesome-claude-skills.md` — ~25 rows, bare slugs.

## Verification

- `bash scripts/build_skill_bank_catalog.sh` regenerates all catalogs.
- `superpowers.md` and `ecc.md` must be **byte-identical** to their committed
  versions (regression guard for the single-path code path).
- The existing suite (`scripts/tests/test_skill_bank.sh`) lints every committed
  `catalog/*.md`, so the three new files are covered once committed; it must stay green.
- Spot-check: every catalog name is `<key>:<slug>`, no empty descriptions, no
  duplicate names within a file.

## Out of scope

- The 833 `composio-skills/` wrappers.
- `recommended.md` and the search sub-agent (`search-agent.md`) — they already glob
  `catalog/*.md`; new files are picked up with no change.
- Refresh/drift tooling beyond updating the `list:` comments in `sources.yml`.
