# Privacy Push Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared `tools/privacy-scan.sh` gate — author-identity, personal-identifier denylist, scratch-file, and external-link checks — enforced both at local `pre-push` (via pre-commit) and in CI, on top of the existing gitleaks + home-path scanning.

**Architecture:** One bash script runs four checks over a commit range (`BASE..HEAD`) and the tip tree; blocking checks 1–3 set a non-zero exit, the link check only prints. The pre-commit framework calls it at the `pre-push` stage; a CI job calls the same script over the PR range with the denylist injected from a secret. No existing check is replaced.

**Tech Stack:** `bash` + `git` (stdlib only — no Python/Node), `pre-commit` framework, GitHub Actions.

## Global Constraints

- **Repo is a Claude Code plugin.** Repo-infrastructure tooling lives in a top-level `tools/`, NEVER under `skills/…` (skill dirs are bundled into the installable plugin; `tools/` is not).
- **Additive only** — keep the existing `gitleaks` + `no-local-home-paths` pre-commit hooks and their CI mirror exactly as they are.
- **Denylist never committed** — `.privacy-denylist` is gitignored (local); CI uses the `PRIVACY_DENYLIST` Actions secret; only `.privacy-denylist.example` (placeholders) is tracked.
- **Denylist absent locally → NOTICE-and-skip** (not a hard fail); CI is the enforced backstop.
- **Link check is non-blocking** (inventory/NOTICE only).
- **Allowed author domain** default `users.noreply.github.com`, overridable via `PRIVACY_ALLOWED_AUTHOR_DOMAIN`.
- **Stdlib bash/git only.** Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Branch `feature/privacy-push-gate` (already created off `main`); never push to `main` directly. Pre-commit hooks run on every commit (gitleaks + home-path) — no `/home/...` literals in committed files.

## File Structure

```
tools/
├── privacy-scan.sh              ← Create: the shared gate (4 checks; exit non-zero on blocking failure)
└── tests/
    └── test_privacy_scan.sh     ← Create: temp-repo harness asserting each check + clean/skip cases
.privacy-denylist.example        ← Create: committed template, placeholders only
.gitignore                       ← Modify: + .privacy-denylist
.pre-commit-config.yaml          ← Modify: + pre-push privacy-scan hook; repoint secret-scan.yml refs
.github/workflows/
└── privacy-scan.yml             ← Rename from secret-scan.yml + add privacy-extras job
AGENTS.md                        ← Modify: setup steps (pre-push install, denylist, CI secret)
README.md                        ← Modify: one-line note in the security/contributing area
```

**Task order:** Task 1 builds and proves the script in isolation (no wiring). Task 2 renames the CI workflow and adds the job (must precede the pre-commit edits, which repoint to the new filename). Task 3 wires the local hook + denylist files + the renamed references. Task 4 documents setup.

---

### Task 1: The shared scan script + test harness

**Files:**
- Create: `tools/privacy-scan.sh`
- Create: `tools/tests/test_privacy_scan.sh`

**Interfaces:**
- Produces: an executable `tools/privacy-scan.sh [BASE] [HEAD]` that exits `0` when clean and non-zero when a blocking check (author/denylist/scratch) fails. Reads optional env: `PRIVACY_ALLOWED_AUTHOR_DOMAIN`, `PRIVACY_DENYLIST`, `PRE_COMMIT_FROM_REF`, `PRE_COMMIT_TO_REF`. Reads `.privacy-denylist` from the current working directory if present.

- [ ] **Step 1: Write the failing test harness**

Create `tools/tests/test_privacy_scan.sh`:

```bash
#!/usr/bin/env bash
# Red-green harness for tools/privacy-scan.sh. Builds throwaway git repos and
# asserts the gate's exit code + output per check. Stdlib bash + git only.
set -uo pipefail
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/privacy-scan.sh"
PASS=0; FAILED=0
ok()   { echo "ok   - $1"; PASS=$((PASS+1)); }
no()   { echo "FAIL - $1"; FAILED=$((FAILED+1)); }
assert_exit() { # desc want_code got_code
  [ "$2" = "$3" ] && ok "$1" || no "$1 (want exit $2, got $3)"; }
assert_contains() { # desc needle haystack
  case "$3" in *"$2"*) ok "$1";; *) no "$1 (missing: $2)";; esac; }

newrepo() {
  local d; d="$(mktemp -d)"; ( cd "$d"
    git init -q
    git config user.name CI
    git config user.email "bot@users.noreply.github.com"
    git config commit.gpgsign false
    echo "# base" > README.md; git add README.md
    git commit -q -m "base" ) ; echo "$d"
}

# --- Scenario A: non-noreply author => FAIL (check 1) ---
d="$(newrepo)"; ( cd "$d"
  echo x > a.txt; git add a.txt
  GIT_AUTHOR_EMAIL="dev@example.com" GIT_COMMITTER_EMAIL="dev@example.com" \
    git commit -q -m "leak author"
)
out="$( cd "$d" && bash "$SCRIPT" HEAD~1 HEAD 2>&1 )"; code=$?
assert_exit "author: non-noreply email fails" 1 "$code"
assert_contains "author: names the bad email" "dev@example.com" "$out"

# --- Scenario B: denylisted term in tracked file => FAIL (check 2) ---
d="$(newrepo)"; ( cd "$d"
  printf 'Jane Q. Public\n' > .privacy-denylist
  echo "contact Jane Q. Public" > docs.md; git add docs.md
  git commit -q -m "add docs"
)
out="$( cd "$d" && bash "$SCRIPT" HEAD~1 HEAD 2>&1 )"; code=$?
assert_exit "denylist: term in content fails" 1 "$code"
assert_contains "denylist: shows the match file" "docs.md" "$out"

# --- Scenario C: force-tracked scratch file => FAIL (check 3) ---
d="$(newrepo)"; ( cd "$d"
  mkdir -p .superpowers/sdd; echo brief > .superpowers/sdd/task-1-brief.md
  git add -f .superpowers/sdd/task-1-brief.md
  git commit -q -m "oops scratch"
)
out="$( cd "$d" && bash "$SCRIPT" HEAD~1 HEAD 2>&1 )"; code=$?
assert_exit "scratch: tracked scratch fails" 1 "$code"
assert_contains "scratch: names the path" ".superpowers/sdd/task-1-brief.md" "$out"

# --- Scenario D: clean range with an added URL => PASS + link NOTICE (check 4) ---
d="$(newrepo)"; ( cd "$d"
  echo "see https://example.com/x for details" > guide.md; git add guide.md
  git commit -q -m "add guide"
)
out="$( cd "$d" && bash "$SCRIPT" HEAD~1 HEAD 2>&1 )"; code=$?
assert_exit "clean: passes with exit 0" 0 "$code"
assert_contains "links: inventories the URL" "https://example.com/x" "$out"

# --- Scenario E: no denylist configured => NOTICE + skip, still PASS ---
d="$(newrepo)"; ( cd "$d"
  echo "nothing sensitive" > plain.md; git add plain.md
  git commit -q -m "add plain"
)
out="$( cd "$d" && env -u PRIVACY_DENYLIST bash "$SCRIPT" HEAD~1 HEAD 2>&1 )"; code=$?
assert_exit "denylist-absent: skips, exit 0" 0 "$code"
assert_contains "denylist-absent: prints NOTICE" "NOTICE [denylist]" "$out"

echo "----"; echo "passed: $PASS  failed: $FAILED"
[ "$FAILED" -eq 0 ]
```

- [ ] **Step 2: Run the harness to verify it FAILS (script doesn't exist yet)**

Run: `bash tools/tests/test_privacy_scan.sh 2>&1 | tail -5`
Expected: FAIL — the harness errors because `tools/privacy-scan.sh` does not exist (e.g. "No such file or directory"), so assertions don't pass.

- [ ] **Step 3: Implement the script**

Create `tools/privacy-scan.sh`:

```bash
#!/usr/bin/env bash
# Privacy push gate: block personal-identity / scratch / denylist leaks before
# they reach the public repo. Runs at pre-push (via pre-commit) and in CI.
# Blocking checks (1-3) exit non-zero; the link inventory (4) only prints.
# Usage: privacy-scan.sh [BASE] [HEAD]
set -uo pipefail

DOMAIN="${PRIVACY_ALLOWED_AUTHOR_DOMAIN:-users.noreply.github.com}"

# Range precedence: explicit args > pre-commit pre-push env > merge-base w/ main.
BASE="${1:-${PRE_COMMIT_FROM_REF:-}}"
HEAD="${2:-${PRE_COMMIT_TO_REF:-HEAD}}"
[ -z "$BASE" ] && BASE="$(git merge-base origin/main HEAD 2>/dev/null || echo main)"
RANGE="$BASE..$HEAD"

fail=0

# 1. Author/committer identity must be a noreply address.
bad="$(git log --format='%ae%n%ce' "$RANGE" 2>/dev/null | sort -u | grep -v "@${DOMAIN}\$" || true)"
if [ -n "$bad" ]; then
  echo "FAIL [author]: non-noreply author/committer email(s) in $RANGE:"
  printf '%s\n' "$bad" | sed 's/^/  - /'
  fail=1
else
  echo "PASS [author]: all commit identities under @${DOMAIN}"
fi

# 2. Personal-identifier denylist (terms from .privacy-denylist or $PRIVACY_DENYLIST).
terms="$(
  { [ -f .privacy-denylist ] && grep -vE '^[[:space:]]*(#|$)' .privacy-denylist; } 2>/dev/null
  [ -n "${PRIVACY_DENYLIST:-}" ] && printf '%s\n' "${PRIVACY_DENYLIST//,/$'\n'}"
)"
if [ -z "$(printf '%s' "$terms" | tr -d '[:space:]')" ]; then
  echo "NOTICE [denylist]: no .privacy-denylist or \$PRIVACY_DENYLIST configured — skipped"
else
  hit=0
  while IFS= read -r term; do
    [ -z "${term//[[:space:]]/}" ] && continue
    m="$(git grep -nFi -e "$term" "$HEAD" -- . 2>/dev/null || true)"
    if [ -n "$m" ]; then
      echo "FAIL [denylist]: term matched in tracked content:"
      printf '%s\n' "$m" | sed 's/^/  /'
      hit=1
    fi
  done <<< "$terms"
  if [ "$hit" -eq 0 ]; then
    echo "PASS [denylist]: no denylisted terms in tracked content"
  else
    fail=1
  fi
fi

# 3. Stray scratch/working files must not be tracked (catches `git add -f`).
scratch="$(git ls-tree -r --name-only "$HEAD" 2>/dev/null \
  | grep -E '(^\.superpowers/sdd/|/scratchpad/|claude-[0-9])' || true)"
if [ -n "$scratch" ]; then
  echo "FAIL [scratch]: scratch/working files are tracked:"
  printf '%s\n' "$scratch" | sed 's/^/  - /'
  fail=1
else
  echo "PASS [scratch]: no scratch/working files tracked"
fi

# 4. External-link inventory (non-blocking).
links="$(git diff "$RANGE" -- '*.md' 2>/dev/null | grep '^+' \
  | grep -oE 'https?://[^ )"`<>]+' | sort -u || true)"
if [ -n "$links" ]; then
  echo "NOTICE [links]: external URLs added in $RANGE (review):"
  printf '%s\n' "$links" | sed 's/^/  - /'
else
  echo "NOTICE [links]: no external URLs added in $RANGE"
fi

exit "$fail"
```

- [ ] **Step 4: Make both scripts executable**

Run: `chmod +x tools/privacy-scan.sh tools/tests/test_privacy_scan.sh`

- [ ] **Step 5: Run the harness to verify it PASSES**

Run: `bash tools/tests/test_privacy_scan.sh 2>&1 | tail -8`
Expected: every line `ok - …`, final line `passed: 10  failed: 0`, exit 0.

- [ ] **Step 6: Commit**

```bash
git add tools/privacy-scan.sh tools/tests/test_privacy_scan.sh
git commit -m "feat(privacy): add privacy-scan gate + red-green test harness

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Rename the CI workflow and add the privacy-extras job

**Files:**
- Rename: `.github/workflows/secret-scan.yml` → `.github/workflows/privacy-scan.yml`
- Modify: the renamed workflow (add `privacy-extras` job; repoint its internal self-exclude)

**Interfaces:**
- Consumes: `tools/privacy-scan.sh` from Task 1.
- Produces: a CI workflow `privacy-scan.yml` whose existing gitleaks + home-path job is unchanged and which adds a `privacy-extras` job running `tools/privacy-scan.sh` over the PR/push range with `PRIVACY_DENYLIST` from secrets.

- [ ] **Step 1: Rename the workflow with git mv**

Run: `git mv .github/workflows/secret-scan.yml .github/workflows/privacy-scan.yml`

- [ ] **Step 2: Update the workflow name and the home-path job's self-exclude**

In `.github/workflows/privacy-scan.yml`:
- Change the top `name: secret-scan` to `name: privacy-scan`.
- In the "Block machine-local absolute home paths" step's `git grep`, change the self-exclude `':!.github/workflows/secret-scan.yml'` to `':!.github/workflows/privacy-scan.yml'`.

- [ ] **Step 3: Add the `privacy-extras` job**

Append this job under `jobs:` in `.github/workflows/privacy-scan.yml` (sibling of the existing `gitleaks` job):

```yaml
  privacy-extras:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # full history so the range scan sees every commit
      - name: Privacy gate (author / denylist / scratch / links)
        env:
          PRIVACY_DENYLIST: ${{ secrets.PRIVACY_DENYLIST }}
        run: |
          # PR: base..head ; push: before..after (fall back to last commit).
          if [ -n "${{ github.event.pull_request.base.sha }}" ]; then
            BASE="${{ github.event.pull_request.base.sha }}"
          elif [ -n "${{ github.event.before }}" ] && \
               git cat-file -e "${{ github.event.before }}^{commit}" 2>/dev/null; then
            BASE="${{ github.event.before }}"
          else
            BASE="$(git rev-parse HEAD~1 2>/dev/null || git rev-parse HEAD)"
          fi
          echo "scanning ${BASE}..HEAD"
          bash tools/privacy-scan.sh "$BASE" HEAD
```

- [ ] **Step 4: Validate the workflow YAML parses**

Run: `python3 -c "import sys,yaml; yaml.safe_load(open('.github/workflows/privacy-scan.yml')); print('YAML OK')"`
Expected: `YAML OK`. (If PyYAML is unavailable, instead run `python3 -c "import json,subprocess" ` is not applicable — use `pre-commit run check-yaml --files .github/workflows/privacy-scan.yml` if check-yaml is configured, else visually confirm indentation.)

- [ ] **Step 5: Dry-run the script over this branch's own range (proxy for CI)**

Run: `bash tools/privacy-scan.sh "$(git merge-base origin/main HEAD)" HEAD; echo "exit=$?"`
Expected: PASS lines for author/denylist(NOTICE)/scratch, a links NOTICE, `exit=0`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/privacy-scan.yml
git commit -m "ci(privacy): rename secret-scan -> privacy-scan, add privacy-extras job

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Local wiring — pre-push hook, denylist ignore + example

**Files:**
- Modify: `.pre-commit-config.yaml` (add pre-push `privacy-scan` hook; repoint two `secret-scan.yml` references)
- Modify: `.gitignore` (+ `.privacy-denylist`)
- Create: `.privacy-denylist.example`

**Interfaces:**
- Consumes: `tools/privacy-scan.sh` (Task 1), the renamed `privacy-scan.yml` (Task 2).
- Produces: a `pre-push`-stage pre-commit hook and the gitignored denylist contract.

- [ ] **Step 1: Add the pre-push hook and repoint the renamed references**

In `.pre-commit-config.yaml`:
- In the header comment, change `the CI job in .github/workflows/secret-scan.yml is the backstop` to `.github/workflows/privacy-scan.yml`.
- In the `no-local-home-paths` hook's `exclude:` regex, change `\.github/workflows/secret-scan\.yml` to `\.github/workflows/privacy-scan\.yml`.
- Add a new hook under the existing `- repo: local` block's `hooks:` list:

```yaml
      - id: privacy-scan
        name: Privacy push gate (author / denylist / scratch / links)
        language: script
        entry: tools/privacy-scan.sh
        stages: [pre-push]
        pass_filenames: false
        always_run: true
```

- [ ] **Step 2: Add `.privacy-denylist` to .gitignore**

Append to `.gitignore` (under a comment):

```
# Personal-identifier denylist for the privacy push gate — contains PII
# (real name / email), so it is per-clone and never committed. Copy from
# .privacy-denylist.example.
.privacy-denylist
```

- [ ] **Step 2b: Create the committed example template**

Create `.privacy-denylist.example`:

```
# Personal-identifier denylist for tools/privacy-scan.sh (local pre-push).
# Copy to .privacy-denylist (gitignored) and fill in real values — one term
# per line, case-insensitive literal match, '#' comments allowed.
# The pre-push gate fails if any term appears in tracked content.
#
# Examples (replace with your own; do NOT commit real values):
# Your Real Name
# you@personal-email.example
```

- [ ] **Step 3: Verify the pre-commit config is valid and the hook is recognized**

Run: `pre-commit validate-config && echo "config OK"`
Expected: `config OK` (no schema errors).

- [ ] **Step 4: Verify `.privacy-denylist` is now ignored and the example is tracked**

Run:
```bash
printf 'Test Name\n' > .privacy-denylist
git check-ignore .privacy-denylist && echo "denylist ignored"
git status --porcelain .privacy-denylist.example
rm -f .privacy-denylist
```
Expected: `.privacy-denylist` then `denylist ignored`; the example shows as a new tracked file (`?? .privacy-denylist.example` or staged).

- [ ] **Step 5: Exercise the actual pre-push hook end-to-end**

Run:
```bash
pre-commit install -t pre-push
pre-commit run privacy-scan --hook-stage pre-push --all-files; echo "exit=$?"
```
Expected: the `privacy-scan` hook runs and reports PASS/NOTICE lines with `exit=0` (this branch is clean).

- [ ] **Step 6: Commit**

```bash
git add .pre-commit-config.yaml .gitignore .privacy-denylist.example
git commit -m "feat(privacy): wire pre-push hook + gitignored denylist contract

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Document setup

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Add a privacy-gate setup subsection to AGENTS.md**

In `AGENTS.md`, after the existing security/commit guidance, add:

```markdown
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
```

- [ ] **Step 2: Add a one-line pointer in README.md**

In `README.md`, in the security/contributing area (near the existing secret-scan mention if present), add one line:

```markdown
> Contributors: run `pre-commit install -t pre-push` and create `.privacy-denylist` from the example — see [AGENTS.md](AGENTS.md#privacy-push-gate). No emoji in docs.
```

(If a more fitting spot exists in the README's contributing/security section, place it there; keep it one line, no emoji.)

- [ ] **Step 3: Confirm no stale `secret-scan.yml` references remain anywhere**

Run: `grep -rn "secret-scan" . --include='*.md' --include='*.yaml' --include='*.yml' 2>/dev/null | grep -v '.superpowers/'`
Expected: no output (every reference now says `privacy-scan`).

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md README.md
git commit -m "docs(privacy): document pre-push gate setup + CI secret

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Shared `tools/privacy-scan.sh` (4 checks, blocking 1–3, link non-blocking) → Task 1 ✓
- `tools/` placement outside `skills/` → Global Constraints + Task 1 ✓
- Author = noreply, configurable domain → Task 1 check 1 ✓
- Denylist from `.privacy-denylist` / `$PRIVACY_DENYLIST`, NOTICE-and-skip when absent → Task 1 check 2 ✓
- Scratch guard (`.superpowers/sdd/` etc., catches `git add -f`) → Task 1 check 3 ✓
- Link inventory non-blocking → Task 1 check 4 ✓
- CI job over PR range with `PRIVACY_DENYLIST` secret; existing gitleaks/home-path job kept → Task 2 ✓
- Rename `secret-scan.yml` → `privacy-scan.yml` + repoint all references → Task 2 (workflow self-exclude) + Task 3 (pre-commit refs) + Task 4 (stale-ref grep) ✓
- Local pre-push hook via pre-commit `stages: [pre-push]` → Task 3 ✓
- `.privacy-denylist` gitignored + `.example` committed → Task 3 ✓
- Setup docs (pre-push install, denylist, CI secret) → Task 4 ✓

**Placeholder scan:** No TBD/TODO; every code step shows the full script/edit; the RED step (Task 1 Step 2) is an intentional TDD failure.

**Type/path consistency:** `tools/privacy-scan.sh` and `tools/tests/test_privacy_scan.sh` paths, the `privacy-scan` hook id, env names (`PRIVACY_DENYLIST`, `PRIVACY_ALLOWED_AUTHOR_DOMAIN`), and the `privacy-scan.yml` filename are used identically across Tasks 1–4. The harness asserts 10 `ok` lines (2 per scenario × 5 scenarios) → matches Task 1 Step 5's `passed: 10`.

**Note:** CI behavior (the `privacy-extras` job firing on a real PR) can only be fully verified once the branch is pushed — Task 2 Step 5 dry-runs the script locally as the proxy; the live PR run is the final confirmation, same posture as the plugin-restructure plan.
