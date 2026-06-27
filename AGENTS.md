# AGENTS.md

Conventions for anyone — human or agent — working in this repository.

## What this repo is

`loop-builder` is a Claude Code **plugin** bundling peer skills under `skills/`:

- `skills/loop-builder/` — interviews the user and scaffolds a self-running agent
  "loop." Body is `SKILL.md`; deep knowledge in `references/`; bundled verifier and
  skill-bank scripts in `scripts/` (tested under `scripts/tests/`).
- `skills/feedback-to-issue/` — captures feedback and files it as a GitHub issue
  under the user's own account. Body is `SKILL.md`; playbook in `references/`;
  deterministic tooling in `scripts/feedback/` (tested under `scripts/tests/`).

The manifest lives in `.claude-plugin/`; trigger/behavior evals in `evals/evals.json`.

## Branching

- **Develop every new feature on its own branch** — `feature/<name>` cut from `main`.
  Never build a feature directly on `main`; keep `main` clean and releasable.
- Push a feature branch with `-u` to track `origin/feature/<name>` when it's ready
  for review.
- Small doc fixes / chores the maintainer explicitly wants on `main` are exempt.

## Documentation style

- **No emoji** in docs (README, etc.) — it reads as low-quality here.
- Make docs visually appealing through **structure** instead: badges, tables,
  ASCII/box diagrams, Mermaid, centered hero blocks, callouts. Plain typographic
  arrows (→ ↓ ←) and box-drawing are fine; colored emoji are not.

## Skill authoring

- Keep `SKILL.md` under ~500 lines; push depth into `references/` and load only the
  relevant file (progressive disclosure).
- Verifiers are **separate** from the generator and deterministic where possible;
  bundled scripts in `scripts/` are red-green tested under `scripts/tests/`.
- Durable knowledge → a skill; changing state → an external state file. Never put
  mutable progress inside a `SKILL.md`.
- **Skill vs. reference (what graduates):** a capability becomes its own
  `skills/<name>/` skill only if a user would trigger it *without* going through
  another skill ("report a bug" stands alone; "the Ralph pattern" does not).
  Reference knowledge stays nested under the owning skill's `references/`. Every
  graduated skill's `description` is always-on context in every session, so keep
  the bar high — graduate genuine standalone triggers only.
- **Cross-skill references:** when one skill must run another skill's bundled
  script, reference it via `${CLAUDE_PLUGIN_ROOT}/skills/<other>/…`. Within-skill
  references stay relative to the skill dir.

## Commits

- **Commit when the work reaches a coherent, reviewable checkpoint** — a complete
  logical change — rather than waiting to be asked. Use judgement: small atomic
  commits at natural boundaries, each with a clear, professional message that says
  *why*, not just *what*. Don't leave finished work uncommitted.
- Land commits on a `feature/<name>` branch per the branching rule above, never
  directly on `main`.
- **Pushing and opening PRs** happen when a branch is ready for review; don't push
  half-finished work, and confirm before pushing if the change is sensitive or
  outward-facing.
- End commit messages with the trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

## Privacy push gate

A `pre-push` gate (`tools/privacy-scan.sh`) blocks identity/scratch/denylist
leaks before they reach the public repo; CI (`.github/workflows/privacy-scan.yml`)
is the unbypassable backstop. Per clone:

1. `pip install pre-commit && pre-commit install -t pre-push`
2. `cp .privacy-denylist.example .privacy-denylist` and fill in your real
   name / personal email (the file is gitignored — never commit it).
3. Repo admins: set the `PRIVACY_DENYLIST` GitHub Actions secret (newline- or
   comma-separated terms) so CI enforces the denylist too.

Checks: commit author/committer must be a `users.noreply.github.com` address;
no denylisted term in tracked content; no `.superpowers/sdd/` or scratch files
tracked; added external links are inventoried (non-blocking).
