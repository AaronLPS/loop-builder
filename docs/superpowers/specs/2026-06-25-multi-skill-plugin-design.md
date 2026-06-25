# multi-skill plugin restructure — design

Restructure the loop-builder repo from a **single skill** (`SKILL.md` at root +
`references/` for progressive-disclosure docs) into a **Claude Code plugin** that
bundles multiple independently-triggerable peer skills under `skills/<name>/`,
following the Superpowers layout. The first split graduates `feedback-to-issue`
out of `references/` into its own peer skill; everything else stays nested.

## Problem

loop-builder is growing past one skill's worth of capability. `feedback-to-issue`
already has a standalone trigger ("report a bug / give feedback") that has nothing
to do with building a loop, yet it lives as a `references/` doc that can only load
*after* loop-builder is already active. As more such capabilities arrive, the flat
single-skill layout forces a choice between burying triggerable skills as
references (undiscoverable on their own) or polluting the loop-builder SKILL.md.

The Superpowers repo solves exactly this: a plugin manifest plus `skills/<name>/`
directories, each a self-contained, independently-discoverable unit cross-referenced
by name (`superpowers:brainstorming`).

## Goal

Convert the repo into a plugin named `loop-builder` whose flagship skill is also
`loop-builder`, with `feedback-to-issue` as a sibling peer skill. The plugin is
self-installable, the green test suite still passes, and the layout makes the
next "should this be a skill?" decision answerable by a single rule.

## The governing rule (locked)

For any capability: **"Would a user ever want this *without* going through
loop-builder?"**

- **Yes** → it is a *skill*: it gets its own `SKILL.md` with a triggering
  `description` the model matches against user intent, and lives at
  `skills/<name>/`.
- **No** → it is a *reference*: pure knowledge loaded on demand by a parent
  skill, nested under that skill's `references/`. No trigger of its own.

This rule is written into `AGENTS.md` as the governing convention so future
growth stays disciplined — every graduated skill's `description` becomes
always-on context in *every* session, so only genuine standalone triggers
graduate; reference knowledge stays nested.

## Decisions (locked during brainstorm)

- **Direction:** become a plugin / collection of peer skills (not one deep skill,
  not a hybrid that hides the structure).
- **What graduates:** `feedback-to-issue` only. `loops-and-loop-engineering.md`,
  the four `pattern-*.md`, `deploy-claude-managed-agents.md`, and the
  `skill-bank/` tree stay nested as `loop-builder`'s references. skill-bank search
  does **not** graduate this round (it is tightly coupled to loop-builder's Phase
  1.5).
- **Plugin identity:** plugin name = `loop-builder`; flagship skill name =
  `loop-builder`. Cross-references read `loop-builder:feedback-to-issue`.
- **Distribution scope:** Claude Code only. Do **not** replicate Superpowers'
  multi-platform tree (`.codex-plugin`, `.cursor-plugin`, `.pi`,
  `gemini-extension.json`, `hooks/`). Minimal manifest now; add platforms later
  only if targeted.
- **README:** becomes a *plugin* README — a light overview of the collection at
  the top, linking out to per-skill docs, keeping the existing loop-builder depth.
- **`marketplace.json`:** included, so the repo is self-installable via
  `/plugin marketplace add <repo>` → `/plugin install`.

## Target layout

```
loop-builder/                          ← repo root becomes a PLUGIN
├── .claude-plugin/
│   ├── plugin.json                    ← NEW: name=loop-builder, version, description
│   └── marketplace.json               ← NEW: self-install entry
├── skills/
│   ├── loop-builder/                  ← flagship skill (moved from root)
│   │   ├── SKILL.md                   ← moved verbatim; reference paths unchanged
│   │   └── references/                ← moved verbatim
│   │       ├── loops-and-loop-engineering.md
│   │       ├── pattern-ralph.md
│   │       ├── pattern-react-deterministic-verifier.md
│   │       ├── pattern-evaluator-optimizer.md
│   │       ├── pattern-orchestrator-workers.md
│   │       ├── deploy-claude-managed-agents.md
│   │       └── skill-bank/
│   └── feedback-to-issue/             ← NEW peer skill
│       ├── SKILL.md                   ← NEW: triggering description + flow
│       ├── references/
│       │   └── feedback-to-issue.md   ← moved from root references/
│       └── scripts/
│           ├── feedback/              ← moved from root scripts/feedback/
│           └── tests/                 ← moved from root scripts/tests/feedback/
├── AGENTS.md                          ← + the governing-rule convention
├── README.md                          ← rewritten as plugin README
├── docs/ · evals/ · .github/          ← stay at root
```

Because `loop-builder/SKILL.md` and its `references/` move **together**, every
`references/...` path inside that SKILL.md keeps resolving relatively — no
rewrite needed there. Only the cross-skill links change (next section).

## The cross-reference rewiring

Today `loop-builder/SKILL.md` points at `references/feedback-to-issue.md` in two
distinct roles. They split cleanly:

1. **Review / file flow** (when the user reports a bug or reviews feedback) →
   replaced by *"invoke the `loop-builder:feedback-to-issue` skill."* This is the
   whole point of graduating it: the trigger now lives on the skill's own
   `description`, discoverable without loop-builder being active.
2. **The inline passive-capture hook snippet** for generated loops → **stays
   inline** in loop-builder. The playbook itself states this one-liner is "the
   only part a generated loop needs inline."

A generated loop never *invokes* the feedback-to-issue skill — it only appends to
the local JSONL log, and review/file happens later when the user triggers the
skill. But the hook does **shell out to that skill's `cli.py`** via the loop's
`LOOP_BUILDER_SCRIPTS` path variable, so there is a runtime *file-path*
dependency. Today that variable resolves to `scripts/feedback/`; after the move it
must resolve to **`skills/feedback-to-issue/scripts/feedback/`**. The implementation
plan must therefore update the path the scaffolder writes into generated loops (and
the playbook's "`LOOP_BUILDER_SCRIPTS` — path to `scripts/feedback/`" note) to the
new location. The path stays parameterized, so a loop's own copy keeps working as
long as its `LOOP_BUILDER_SCRIPTS` points at wherever `cli.py` actually lives.

## feedback-to-issue SKILL.md

The existing `references/feedback-to-issue.md` already opens with a trigger
sentence, a strict step-by-step flow, a quick-reference table, and a
maintainer-setup section — i.e. it already reads like a skill body. The new
`skills/feedback-to-issue/SKILL.md` is therefore a thin frontmatter wrapper
(`name: feedback-to-issue`, a `description` covering "report a bug / give
feedback / review my feedback / file an issue"). To keep a single source of
truth, the detailed step-by-step playbook **stays** as
`skills/feedback-to-issue/references/feedback-to-issue.md` (loaded by the thin
SKILL.md), with script paths updated to the skill-local `scripts/` location. The
SKILL.md carries only the trigger, the guarantees, and the pointer into that
reference — matching how loop-builder already treats its own references.

## Migration mechanics

- Use `git mv` for every move to preserve file history.
- **Python import depth:** the feedback tests resolve the module via
  `sys.path` / `parents[N]`; moving `scripts/feedback` and its tests under
  `skills/feedback-to-issue/scripts/` changes the relative depth. Re-point the
  path computation and re-run.
- **CI:** `.github/workflows/tests.yml` references the test locations; update the
  paths to `skills/feedback-to-issue/scripts/...` (and any loop-builder script
  paths that move).
- **Acceptance test for the migration:** the existing 22-test feedback suite
  (`test_feedback.sh`) passes from its new location, and the loop-builder skill
  still loads with all `references/` resolving.

## Out of scope

- Graduating skill-bank search (revisit when it grows a standalone trigger).
- Multi-platform plugin packaging (Codex/Cursor/Gemini/etc.).
- Any behavior change to loop-builder or feedback-to-issue logic — this is a
  structural move plus the cross-reference rewiring, nothing more.

## Risks

- **Silent path breakage:** the move touches Python imports, CI paths, and
  cross-skill links. Mitigated by the migration acceptance test (green suite +
  skill load) being the definition of done.
- **Plugin discovery:** a malformed `plugin.json` / `marketplace.json` makes the
  plugin uninstallable. Mitigated by validating install locally before merge.
- **Description bloat over time:** every future graduated skill adds always-on
  context. Mitigated by the governing rule in `AGENTS.md`.
