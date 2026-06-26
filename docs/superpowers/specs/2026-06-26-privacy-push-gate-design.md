# privacy push gate — design

> Re-rooted on the **post-restructure** `main` (`loop-builder` is now a Claude Code
> *plugin*; the single-skill → multi-skill restructure merged in **#5**). The gate
> itself is repo/push-flow infrastructure and is layout-independent, but this
> revision fixes all paths to the real merged layout and accounts for the new
> plugin-specific surface (the committed `.claude-plugin/` manifest, and the fact
> that the repo is now something *other people install*).

Add an automated privacy/data review that runs **before code reaches the public
repo**, extending the existing secret + home-path scanning with checks the current
gates miss: commit-author identity, a personal-identifier denylist, a stray
scratch-file guard, and an external-link inventory. Enforced in **two** places from
**one shared script**: a local `pre-push` hook (earliest feedback) and a CI job
(unbypassable backstop).

## Problem

The repo is public **and now an installable plugin** — adding the marketplace and
running `/plugin install loop-builder@loop-builder` clones the entire repo onto a
consumer's machine. That raises the privacy bar above "my own skill": anything in
tracked history ships to every installer.

Today two checks are automated — gitleaks (secrets) and a pygrep for machine-local
home paths — but only at the **pre-commit** stage locally, plus a CI mirror
(`secret-scan.yml`). A manual privacy review before the #5 push surfaced categories
none of that covers:

1. A commit could be authored under a **personal email** instead of the GitHub
   `users.noreply.github.com` address, leaking a real identity into public history.
2. A **real name / personal email** could appear in committed *content* — including
   the new committed `.claude-plugin/plugin.json` / `marketplace.json`, which carry
   author/identity fields.
3. **Scratch/working files** (`.superpowers/sdd/` briefs, reports, diffs) could be
   force-added past `.gitignore` (they are ignored today via
   `.superpowers/sdd/.gitignore`, but `git add -f` bypasses that).
4. **External links** added to docs go out unreviewed.

There is also **no `pre-push` hook at all** — the earliest local gate is commit
time, and the CI backstop only fires after the push lands on GitHub.

## Goal

One `git push` (or one PR) cannot carry a personal-identity leak, a denylisted
term, or a stray scratch file to the public repo without an explicit, logged
override — and the maintainer sees an inventory of any new external links. The
denylist (itself PII) never lives in tracked files.

## Decisions (locked during brainstorm)

- **Enforce in both places:** local `pre-push` hook **and** CI job, sharing one
  script so they cannot drift.
- **Four new checks:** (1) commit-author = noreply, (2) personal-identifier
  denylist, (3) stray scratch-file guard, (4) external-link inventory.
- **Link check is non-blocking** — inventory/warn only (live validation is
  network-flaky; a push gate must be deterministic).
- **Denylist storage:** untracked local file (`.privacy-denylist`, gitignored) for
  the local hook; a GitHub Actions secret (`PRIVACY_DENYLIST`) for CI. Nothing
  sensitive is committed. A committed `.privacy-denylist.example` documents the
  format with placeholders only.
- **Keep the existing gitleaks + home-path gates as-is** — this is additive.
- **OPEN (for review):** when `.privacy-denylist` is absent **locally**, does the
  denylist check NOTICE-and-skip (CI still enforces) or hard-fail? Spec currently
  assumes NOTICE-and-skip; confirm before build.

## Plugin-aware placement (the part this revision re-thinks)

After the restructure, every `scripts/` directory is **owned by a skill**
(`skills/loop-builder/scripts/`, `skills/feedback-to-issue/scripts/`) and ships
with that skill. The privacy gate is **repo infrastructure, not a skill component**
— it must NOT live inside `skills/…` (it would then be bundled into the plugin that
installers download, which is wrong). It gets its own top-level home:

```
tools/                          ← repo infrastructure; NOT shipped with any skill
├── privacy-scan.sh             ← the shared gate (4 checks over a commit range + tip)
└── tests/
    └── test_privacy_scan.sh    ← red-green: each check catches a crafted bad case; clean passes
.privacy-denylist.example       ← committed template (placeholders, no real PII)
.gitignore                      ← + .privacy-denylist
.pre-commit-config.yaml         ← + a repo-local hook at `stages: [pre-push]` calling the script
.github/workflows/
└── privacy-scan.yml            ← secret-scan.yml renamed/extended: existing gitleaks+home-path job
                                   PLUS a job calling tools/privacy-scan.sh over the PR range
```

(`tools/` is excluded from any future `*.skill` packaging by construction, since
packaging pulls from `skills/<name>/`, not the repo root.)

### `tools/privacy-scan.sh` contract

- **Invocation:** `privacy-scan.sh [BASE] [HEAD]`. Defaults: `HEAD=HEAD`,
  `BASE=$(git merge-base origin/main HEAD)` (falls back to `main`). For the
  pre-push hook, reads pre-commit's `PRE_COMMIT_FROM_REF`/`PRE_COMMIT_TO_REF` when
  present.
- **Exit:** non-zero if any *blocking* check (1–3) fails; check 4 only prints. A
  one-line summary per check (`PASS`/`FAIL`/`NOTICE`) and, on failure, the
  offending commit SHAs / file:line.
- **Checks:**
  1. **Author = noreply.** `git log --format='%ae%n%ce' BASE..HEAD`; every email
     must match `@users\.noreply\.github\.com$` (configurable via
     `PRIVACY_ALLOWED_AUTHOR_DOMAIN`, default `users.noreply.github.com`). The
     `Co-Authored-By:` trailer is in the commit body, not `%ae/%ce`, so it is not
     evaluated. Fail lists offending commits. (Both `AaronLPS@…` and the
     ID-prefixed `30174455+AaronLPS@users.noreply.github.com` forms pass.)
  2. **Denylist.** Load terms from `.privacy-denylist` (one per line, `#` comments)
     or `$PRIVACY_DENYLIST` (newline/`,`-separated). For each term,
     `git grep -nFi -- <tracked>` at HEAD — this naturally covers the new
     `.claude-plugin/*.json` and every doc. Any hit fails. If **no** denylist is
     configured: print a NOTICE and skip (do not hard-fail) — but CI sets the
     secret, so CI effectively requires it. (See OPEN decision above.)
  3. **Scratch guard.** `git ls-files` must contain no path matching
     `^\.superpowers/sdd/`, `/scratchpad/`, or `claude-[0-9]`. Any match fails
     (catches `git add -f` past the nested `.gitignore`).
  4. **Link inventory (non-blocking).** From `git diff BASE..HEAD -- '*.md'`,
     extract added `https?://` URLs; print them under a NOTICE for the maintainer
     to eyeball. Never fails the gate.

### Wiring

- **Local pre-push:** `.pre-commit-config.yaml` gains a `repo: local` hook,
  `id: privacy-scan`, `stages: [pre-push]`, `language: script`,
  `entry: tools/privacy-scan.sh`, `pass_filenames: false`, `always_run: true`.
  Activated per clone with `pre-commit install -t pre-push` (documented). The two
  existing hooks stay at their default pre-commit stage, unchanged.
- **CI:** `secret-scan.yml` → `privacy-scan.yml`. Keep the current gitleaks +
  home-path job verbatim; add a `privacy-extras` job: checkout with
  `fetch-depth: 0`, compute the PR range, run `tools/privacy-scan.sh` with
  `PRIVACY_DENYLIST` injected from the repo secret. (`tests.yml` is untouched.)

## Testing

`tools/tests/test_privacy_scan.sh` builds throwaway commits/fixtures in a temp git
repo and asserts the script:
- FAILS when a commit author is a non-noreply email (check 1).
- FAILS when a denylisted term appears in a tracked file (check 2).
- FAILS when a `.superpowers/sdd/` path is force-tracked (check 3).
- PASSES a clean range, and PRINTS a NOTICE listing an added URL (check 4) without
  failing.
Red-green: each assertion is written to fail first against a stub, then pass.

## Setup (documented in AGENTS.md / README)

1. `pip install pre-commit && pre-commit install -t pre-push` (per clone).
2. Create `.privacy-denylist` (gitignored) from `.privacy-denylist.example`.
3. Repo admin sets the `PRIVACY_DENYLIST` GitHub Actions secret.

## Out of scope

- Live (network) link validation — inventory only.
- Rewriting existing history; this gates future pushes/PRs.
- Replacing the gitleaks / home-path checks — they stay.
- Scanning plugin *consumers'* installs — this gate is about what the maintainer
  pushes, not what installers run.

## Risks

- **Denylist accidentally committed.** Mitigated: `.privacy-denylist` is gitignored
  and the scratch/identifier checks would themselves flag it; only the `.example`
  (placeholders) is tracked.
- **Author-domain false positive.** Some orgs use a custom noreply domain;
  `PRIVACY_ALLOWED_AUTHOR_DOMAIN` is configurable.
- **Pre-push bypass (`--no-verify`).** Accepted — CI is the unbypassable backstop,
  same posture as the existing secret gate.
