# AGENTS.md

Conventions for anyone — human or agent — working in this repository.

## What this repo is

`loop-builder` is a Claude Code **skill** that interviews the user and scaffolds a
self-running agent "loop." The skill body is `SKILL.md`; deep knowledge lives in
`references/`; bundled verifier scripts live in `scripts/`; trigger/behavior evals
live in `evals/evals.json`.

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

## Commits

- End commit messages with the trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Commit or push only when the maintainer asks.
