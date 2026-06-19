# skill-bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a curated, index-only "skill-bank" so loop-builder's reuse survey (Phase 1.5) can recommend proven external skills/plugins to serve a loop's building blocks, instead of re-deriving them.

**Architecture:** A small block-tagged markdown index (`references/skill-bank/INDEX.md`) plus a `sources.yml` of upstream repos. Two bash tools — an index linter and a drift checker — guard the catalog, tested red-green in the existing `scripts/tests/` harness. Phase 1.5 of `SKILL.md` gains a second discovery source pointing at the index. Borrowing is recommend-and-record (pointers + fallback), never inlined code.

**Tech Stack:** Bash (POSIX-ish, `#!/usr/bin/env bash`), markdown, YAML-as-docs, JSON (evals). No new runtime deps; online refresh uses `gh` as a documented manual step.

**Spec:** `docs/superpowers/specs/2026-06-19-skill-bank-design.md`

**Branch:** `feature/skill-bank` (already checked out).

---

## File Structure

| Path | Responsibility | Action |
|------|----------------|--------|
| `references/skill-bank/sources.yml` | The upstream source repos + how to enumerate each (refresh input/docs) | Create |
| `references/skill-bank/INDEX.md` | The searchable block-tagged catalog (one row per entry) | Create |
| `scripts/lint_skill_bank_index.sh` | Validate the INDEX table schema; exit 0 clean / 1 violations | Create |
| `scripts/refresh_skill_bank.sh` | Diff INDEX names vs an upstream name list; exit 0 in-sync / 1 drift | Create |
| `scripts/tests/test_skill_bank.sh` | Red-green tests for both scripts + the seeded index | Create |
| `scripts/tests/fixtures/skill_bank/` | Fixture indexes + upstream lists for the tests | Create |
| `SKILL.md` | Phase 1.5 gains a second source (skill-bank) + pointer | Modify |
| `evals/evals.json` | One bank-consult behavior eval | Modify |
| `README.md` | Repo-layout + test-command updates | Modify |

Naming convention used throughout: an INDEX `name` is `<source-key>:<entry-slug>` for enumerable sources (e.g. `superpowers:brainstorming`). This makes drift detection a plain set comparison.

---

## Task 1: Source list (`sources.yml`)

**Files:**
- Create: `references/skill-bank/sources.yml`

- [ ] **Step 1: Create the source list**

Create `references/skill-bank/sources.yml` with exactly this content:

```yaml
# skill-bank sources — the upstream collections this catalog draws from.
#
# Refresh is a manual two-step (see scripts/refresh_skill_bank.sh):
#   1) Produce an upstream name list using each source's `list:` command below.
#      Names use the convention <key>:<entry-slug> so they line up with INDEX.md.
#   2) Run: bash scripts/refresh_skill_bank.sh --upstream <that-file>
#      and curate the reported diff into INDEX.md (we list only standout entries,
#      not a full mirror).

- key: superpowers
  repo: https://github.com/obra/superpowers
  list: "gh api repos/obra/superpowers/contents/skills --jq '.[].name' | sed 's#^#superpowers:#'"

- key: ecc
  repo: https://github.com/affaan-m/ecc
  list: "# README-curated — review the repo and add standout entries by hand"

- key: awesome-claude-skills
  repo: https://github.com/ComposioHQ/awesome-claude-skills
  list: "# README-curated — it is itself a list; pull the standout linked skills"

- key: gstack
  repo: https://github.com/garrytan/gstack
  list: "# README-curated — review the repo and add standout entries by hand"

- key: claude-for-legal
  repo: https://github.com/anthropics/claude-for-legal
  list: "# README-curated — review the repo and add standout entries by hand"
```

- [ ] **Step 2: Commit**

```bash
git add references/skill-bank/sources.yml
git commit -m "feat(skill-bank): add upstream sources.yml"
```

---

## Task 2: INDEX linter (`lint_skill_bank_index.sh`)

**Files:**
- Create: `scripts/tests/fixtures/skill_bank/index_good.md`
- Create: `scripts/tests/fixtures/skill_bank/index_bad.md`
- Create: `scripts/tests/test_skill_bank.sh`
- Create: `scripts/lint_skill_bank_index.sh`

- [ ] **Step 1: Create the fixtures**

Create `scripts/tests/fixtures/skill_bank/index_good.md`:

```markdown
# fixture: a well-formed skill-bank index

| name | type | blocks | purpose | source | install | license | synced |
|------|------|--------|---------|--------|---------|---------|--------|
| example:alpha | skill | 5 | a deterministic verifier helper | https://github.com/example/alpha | clone into ~/.claude/skills/alpha | MIT | example/alpha@abc123 2026-06-19 |
| example:beta | mcp | 4 | a tracker connector | https://github.com/example/beta | add to mcp config | Apache-2.0 | example/beta@def456 2026-06-19 |
```

Create `scripts/tests/fixtures/skill_bank/index_bad.md` (three deliberate faults: an unknown `type`, an out-of-range block `9`, and a row with too few columns):

```markdown
# fixture: a malformed skill-bank index

| name | type | blocks | purpose | source | install | license | synced |
|------|------|--------|---------|--------|---------|---------|--------|
| example:bad | notatype | 9 | bad type and bad block | https://github.com/example/bad | clone it | MIT | example/bad@000 2026-06-19 |
| example:short | skill | 3 | missing columns |
```

- [ ] **Step 2: Write the failing test**

Create `scripts/tests/test_skill_bank.sh`:

```bash
#!/usr/bin/env bash
# Tests for skill-bank tooling: the INDEX linter and the refresh drift checker.
# Same red-green contract as test_verifiers.sh (exit 0 == clean / in-sync).
# Run: bash scripts/tests/test_skill_bank.sh
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$SCRIPTS/.." && pwd)"
FIX="$HERE/fixtures/skill_bank"
fails=0

check() {  # check <description> <expected_exit> <actual_exit>
  local desc="$1" want="$2" got="$3"
  if [ "$want" = "$got" ]; then
    echo "PASS: $desc"
  else
    echo "FAIL: $desc (expected exit $want, got $got)"
    fails=$((fails + 1))
  fi
}

# --- lint_skill_bank_index.sh ----------------------------------------------
bash "$SCRIPTS/lint_skill_bank_index.sh" --file "$FIX/index_good.md" >/dev/null 2>&1
check "lint: well-formed index -> pass" 0 $?

bash "$SCRIPTS/lint_skill_bank_index.sh" --file "$FIX/index_bad.md" >/dev/null 2>&1
check "lint: malformed index -> fail" 1 $?

echo "----"
if [ "$fails" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$fails TEST(S) FAILED"
  exit 1
fi
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: FAIL — both lint cases error because `scripts/lint_skill_bank_index.sh` does not exist yet (the `check` lines will not report PASS; the script will report a non-zero/`127` actual exit and the suite ends with `TEST(S) FAILED`).

- [ ] **Step 4: Write the linter**

Create `scripts/lint_skill_bank_index.sh`:

```bash
#!/usr/bin/env bash
# Lint the skill-bank INDEX table. Every data row must have all 8 columns, a known
# type, block tags in 1..6, a single-token license, an http(s) source, and no empty
# required cells. Exit 0 if clean, 1 if any violation, 2 on usage error. Run:
#   bash scripts/lint_skill_bank_index.sh [--file references/skill-bank/INDEX.md]
set -u

FILE="references/skill-bank/INDEX.md"
if [ "${1:-}" = "--file" ]; then FILE="${2:-}"; fi

if [ ! -f "$FILE" ]; then
  echo "lint: file not found: $FILE" >&2
  exit 2
fi

trim() {  # echo the argument with leading/trailing whitespace removed
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

violations=0
row=0
while IFS= read -r line; do
  # only markdown table rows (start with a pipe)
  case "$line" in
    \|*) : ;;
    *) continue ;;
  esac
  # skip separator rows like |---|---|
  if printf '%s' "$line" | grep -qE '^\|[[:space:]]*-{3,}'; then continue; fi

  body="${line#|}"; body="${body%|}"
  IFS='|' read -ra raw <<< "$body"
  cells=()
  for c in "${raw[@]}"; do cells+=("$(trim "$c")"); done

  # skip the header row
  if [ "${cells[0]}" = "name" ]; then continue; fi

  row=$((row + 1))
  rid="row $row (${cells[0]:-<empty>})"

  if [ "${#cells[@]}" -ne 8 ]; then
    echo "FAIL: $rid has ${#cells[@]} columns, expected 8"
    violations=$((violations + 1))
    continue
  fi

  name="${cells[0]}"; type="${cells[1]}"; blocks="${cells[2]}"; purpose="${cells[3]}"
  source="${cells[4]}"; install="${cells[5]}"; license="${cells[6]}"; synced="${cells[7]}"

  for pair in "name=$name" "purpose=$purpose" "install=$install" "synced=$synced"; do
    k="${pair%%=*}"; v="${pair#*=}"
    if [ -z "$v" ]; then
      echo "FAIL: $rid empty $k"; violations=$((violations + 1))
    fi
  done

  case "$type" in
    skill|plugin|mcp|sub-agent|workflow) : ;;
    *) echo "FAIL: $rid bad type '$type'"; violations=$((violations + 1)) ;;
  esac

  IFS=',' read -ra btoks <<< "$blocks"
  for b in "${btoks[@]}"; do
    b="$(trim "$b")"
    case "$b" in
      1|2|3|4|5|6) : ;;
      *) echo "FAIL: $rid bad block '$b'"; violations=$((violations + 1)) ;;
    esac
  done

  if [ -z "$license" ] || printf '%s' "$license" | grep -q ' '; then
    echo "FAIL: $rid bad license '$license'"; violations=$((violations + 1))
  fi

  case "$source" in
    http://*|https://*) : ;;
    *) echo "FAIL: $rid source not a URL '$source'"; violations=$((violations + 1)) ;;
  esac
done < "$FILE"

if [ "$violations" -eq 0 ]; then
  echo "OK: skill-bank index clean ($row entries)"
  exit 0
else
  echo "$violations violation(s)"
  exit 1
fi
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: PASS for both lint cases; suite prints `ALL TESTS PASSED`.

- [ ] **Step 6: Commit**

```bash
git add scripts/lint_skill_bank_index.sh scripts/tests/test_skill_bank.sh scripts/tests/fixtures/skill_bank/index_good.md scripts/tests/fixtures/skill_bank/index_bad.md
git commit -m "feat(skill-bank): add INDEX linter with red-green tests"
```

---

## Task 3: Refresh drift checker (`refresh_skill_bank.sh`)

**Files:**
- Create: `scripts/tests/fixtures/skill_bank/upstream_insync.txt`
- Create: `scripts/tests/fixtures/skill_bank/upstream_drift.txt`
- Modify: `scripts/tests/test_skill_bank.sh` (append refresh cases)
- Create: `scripts/refresh_skill_bank.sh`

Recall `index_good.md`'s two rows carry `synced` refs `example/alpha@abc123` and
`example/beta@def456`. The upstream fixtures below exercise all three drift classes
(added, removed, stale). An upstream line is `name` or `name<space>ref`; a bare name
means "ref unknown, do not stale-check it".

- [ ] **Step 1: Create the upstream fixtures**

Create `scripts/tests/fixtures/skill_bank/upstream_insync.txt` (same two names, no refs → no added/removed/stale):

```text
example:alpha
example:beta
```

Create `scripts/tests/fixtures/skill_bank/upstream_drift.txt` (drops `example:beta`, adds `example:gamma`):

```text
example:alpha
example:gamma
```

Create `scripts/tests/fixtures/skill_bank/upstream_stale.txt` (same two names, but `example:beta`'s ref differs from the index's `def456` → stale):

```text
example:alpha abc123
example:beta zzz999
```

- [ ] **Step 2: Write the failing test (append refresh cases)**

In `scripts/tests/test_skill_bank.sh`, replace the closing block:

```bash
echo "----"
if [ "$fails" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$fails TEST(S) FAILED"
  exit 1
fi
```

with:

```bash
# --- refresh_skill_bank.sh -------------------------------------------------
bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_insync.txt" >/dev/null 2>&1
check "refresh: index matches upstream -> in sync" 0 $?

bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_drift.txt" >/dev/null 2>&1
check "refresh: added/removed drift -> non-zero" 1 $?

bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_stale.txt" >/dev/null 2>&1
check "refresh: stale ref -> non-zero" 1 $?

echo "----"
if [ "$fails" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$fails TEST(S) FAILED"
  exit 1
fi
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: the two new refresh cases FAIL (script missing → non-zero actual), suite ends `TEST(S) FAILED`. The two lint cases still PASS.

- [ ] **Step 4: Write the refresh checker**

Create `scripts/refresh_skill_bank.sh`:

```bash
#!/usr/bin/env bash
# Compare the skill-bank INDEX against a list of upstream entries and report drift in
# three classes: added (upstream-only), removed (index-only), stale (same name, but
# the upstream ref differs from the index's recorded synced ref). Exit 0 if in sync,
# 1 if any drift, 2 on usage error.
#
#   bash scripts/refresh_skill_bank.sh --upstream <file> [--index <file>]
#
# --upstream FILE : one entry per line, `name` or `name <ref>` (blank lines and
#   #comments ignored), in the same <key>:<slug> convention as INDEX.md. A bare name
#   skips the stale check for that entry. This is the deterministic, tested path:
#   produce FILE with the `list:` commands in references/skill-bank/sources.yml, then
#   curate the reported diff by hand.
set -u

INDEX="references/skill-bank/INDEX.md"
UPSTREAM=""

while [ $# -gt 0 ]; do
  case "$1" in
    --upstream) UPSTREAM="${2:-}"; shift 2 ;;
    --index)    INDEX="${2:-}"; shift 2 ;;
    *) echo "usage: refresh_skill_bank.sh --upstream FILE [--index FILE]" >&2; exit 2 ;;
  esac
done

if [ ! -f "$INDEX" ]; then echo "refresh: index not found: $INDEX" >&2; exit 2; fi
if [ -z "$UPSTREAM" ]; then
  echo "refresh: --upstream FILE is required (see references/skill-bank/sources.yml)" >&2
  exit 2
fi
if [ ! -f "$UPSTREAM" ]; then echo "refresh: upstream file not found: $UPSTREAM" >&2; exit 2; fi

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

idx_tmp="$(mktemp)"; up_tmp="$(mktemp)"
trap 'rm -f "$idx_tmp" "$up_tmp"' EXIT

# INDEX data rows -> "name ref" (ref from the synced column's <owner/repo>@<ref>; '-'
# if absent).
while IFS= read -r line; do
  case "$line" in \|*) : ;; *) continue ;; esac
  if printf '%s' "$line" | grep -qE '^\|[[:space:]]*-{3,}'; then continue; fi
  body="${line#|}"; body="${body%|}"
  IFS='|' read -ra raw <<< "$body"
  [ "${#raw[@]}" -lt 8 ] && continue
  name="$(trim "${raw[0]}")"
  [ "$name" = "name" ] && continue
  [ -z "$name" ] && continue
  synced="$(trim "${raw[7]}")"
  if printf '%s' "$synced" | grep -q '@'; then
    ref="${synced#*@}"; ref="${ref%% *}"
  else
    ref="-"
  fi
  printf '%s %s\n' "$name" "$ref" >> "$idx_tmp"
done < "$INDEX"

# upstream lines -> "name ref" ('-' if no ref given)
grep -vE '^[[:space:]]*(#|$)' "$UPSTREAM" | while IFS= read -r l; do
  l="$(trim "$l")"; [ -z "$l" ] && continue
  n="${l%%[[:space:]]*}"
  r="$(trim "${l#"$n"}")"; [ -z "$r" ] && r="-"
  printf '%s %s\n' "$n" "$r"
done >> "$up_tmp"

idx_names="$(awk '{print $1}' "$idx_tmp" | sort -u)"
up_names="$(awk '{print $1}' "$up_tmp" | sort -u)"

added="$(comm -13 <(printf '%s\n' "$idx_names") <(printf '%s\n' "$up_names"))"
removed="$(comm -23 <(printf '%s\n' "$idx_names") <(printf '%s\n' "$up_names"))"
stale="$(awk '
  NR==FNR { if ($2 != "-") iref[$1]=$2; next }
  { if ($2 != "-" && ($1 in iref) && iref[$1] != $2) print $1" (index "iref[$1]" vs upstream "$2")" }
' "$idx_tmp" "$up_tmp")"

drift=0
if [ -n "$added" ]; then
  echo "UPSTREAM-ADDED (in upstream, not in index):"
  printf '%s\n' "$added" | sed 's/^/  + /'
  drift=1
fi
if [ -n "$removed" ]; then
  echo "INDEX-ONLY (in index, not upstream — removed/renamed?):"
  printf '%s\n' "$removed" | sed 's/^/  - /'
  drift=1
fi
if [ -n "$stale" ]; then
  echo "STALE (ref moved upstream):"
  printf '%s\n' "$stale" | sed 's/^/  ~ /'
  drift=1
fi

if [ "$drift" -eq 0 ]; then
  echo "OK: index in sync with upstream"
  exit 0
fi
exit 1
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: all four cases PASS; suite prints `ALL TESTS PASSED`.

- [ ] **Step 6: Commit**

```bash
git add scripts/refresh_skill_bank.sh scripts/tests/test_skill_bank.sh scripts/tests/fixtures/skill_bank/upstream_insync.txt scripts/tests/fixtures/skill_bank/upstream_drift.txt scripts/tests/fixtures/skill_bank/upstream_stale.txt
git commit -m "feat(skill-bank): add refresh drift checker (added/removed/stale) with tests"
```

---

## Task 4: Seed the real `INDEX.md`

**Files:**
- Create: `references/skill-bank/INDEX.md`
- Modify: `scripts/tests/test_skill_bank.sh` (assert the seeded index lints clean)

- [ ] **Step 1: Author the seed index from real upstream data**

Create `references/skill-bank/INDEX.md` starting with this exact skeleton (header + separator unchanged — the linter and refresh parser depend on the 8-column shape):

```markdown
# skill-bank index

A curated catalog of proven external skills/plugins/workflows worth borrowing when
building a loop. Pointers only — nothing here is vendored. Each entry is tagged by the
loop block it can serve: (1) scheduling, (2) isolation, (3) skill/conventions,
(4) connectors, (5) verifier, (6) state. Borrow by recommend-and-record: cite the
source + install pointer + a named fallback; never inline external code. Sources and
the refresh procedure live in `sources.yml`.

| name | type | blocks | purpose | source | install | license | synced |
|------|------|--------|---------|--------|---------|---------|--------|
| superpowers:test-driven-development | skill | 5 | red-green TDD discipline usable as a loop's verifier rubric | https://github.com/obra/superpowers | clone into ~/.claude/skills/ | MIT | obra/superpowers@main 2026-06-19 |
| superpowers:brainstorming | workflow | 3 | structured design dialogue for shaping a loop's conventions | https://github.com/obra/superpowers | clone into ~/.claude/skills/ | MIT | obra/superpowers@main 2026-06-19 |
```

Then populate it for real. For each source in `sources.yml`, fetch the repo
(WebFetch the README and, for `superpowers`, the `skills/` listing) and add the
standout entries — aim for **2–4 per source**, not an exhaustive dump. For every row:

- Set `name` to `<source-key>:<entry-slug>` (e.g. `gstack:ship`).
- Set `blocks` to the loop block(s) it genuinely serves (a verifier-like skill → 5; a
  connector/MCP → 4; a conventions/process skill → 3; a scheduler → 1; isolation → 2;
  a state/memory tool → 6).
- Set `type` to one of: `skill`, `plugin`, `mcp`, `sub-agent`, `workflow`.
- Read the actual `license` from each repo's LICENSE file (do not guess — confirm via
  WebFetch; use the SPDX id, single token, e.g. `MIT`, `Apache-2.0`).
- Set `source` to the repo URL (add the in-repo path in `install` if relevant).
- Stamp `synced` as `<owner>/<repo>@<ref> 2026-06-19`.

The two seed rows above are real and verifiable; keep them and confirm their license
against the repo while you add the rest.

- [ ] **Step 2: Verify the seed lints clean**

Run: `bash scripts/lint_skill_bank_index.sh --file references/skill-bank/INDEX.md`
Expected: `OK: skill-bank index clean (N entries)` and exit 0. If it reports
violations, fix the offending rows (column count, type, blocks, license token, URL).

- [ ] **Step 3: Add a regression test that the seeded index stays clean**

In `scripts/tests/test_skill_bank.sh`, immediately after the second lint case (the
`index_bad.md` line) and before the `# --- refresh` comment, insert:

```bash
# the real seeded index must always lint clean
bash "$SCRIPTS/lint_skill_bank_index.sh" --file "$ROOT/references/skill-bank/INDEX.md" >/dev/null 2>&1
check "lint: seeded INDEX.md is clean" 0 $?
```

- [ ] **Step 4: Run the full suite**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: all five cases PASS; suite prints `ALL TESTS PASSED`.

- [ ] **Step 5: Commit**

```bash
git add references/skill-bank/INDEX.md scripts/tests/test_skill_bank.sh
git commit -m "feat(skill-bank): seed curated INDEX.md and guard it in tests"
```

---

## Task 5: Wire skill-bank into Phase 1.5 of `SKILL.md`

**Files:**
- Modify: `SKILL.md` (the Phase 1.5 opening paragraph)

- [ ] **Step 1: Edit the discovery sentence**

In `SKILL.md`, find this exact sentence at the end of the Phase 1.5 opening paragraph:

```
sub-agent. Use `find-skills` (or scan the available skills / MCP list) to discover
options.
```

Replace it with:

```
sub-agent. Search **two** sources and map both to the loop's blocks:

- **Installed** — use `find-skills` (or scan the available skills / MCP list) for
  capabilities already on the machine (ready to use immediately).
- **skill-bank** — search `references/skill-bank/INDEX.md`, a curated catalog of
  proven external skills/plugins/workflows tagged by the block each can serve, for
  capabilities worth *borrowing* (these would need installing). Recommend-and-record
  only: surface the source + install pointer + a named fallback; never inline
  external code. Bank entries are externally evolving — keep the "verify unverified
  mechanics" flag on them.
```

- [ ] **Step 2: Verify the pointer landed and the body is still within budget**

Run: `grep -n "skill-bank/INDEX.md" SKILL.md && wc -l SKILL.md`
Expected: the grep prints the new line; `wc -l` is comfortably under 500.

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "feat(skill-bank): add skill-bank as a second Phase 1.5 reuse source"
```

---

## Task 6: Add a bank-consult behavior eval

**Files:**
- Modify: `evals/evals.json`

- [ ] **Step 1: Add the eval entry**

In `evals/evals.json`, the `evals` array currently ends with the object whose `"id": 5`. Add a comma after that object's closing brace and insert this new object before the array's closing `]`:

```json
    {
      "id": 6,
      "prompt": "I want to set up an overnight agent that keeps our docs site's broken links fixed, and I'd rather reuse good existing tooling than build link-checking from scratch",
      "expected_output": "Triggers loop-builder; during Phase 1.5 it searches the skill-bank (references/skill-bank/INDEX.md) in addition to installed skills, surfaces a relevant borrowable entry mapped to a loop block (e.g. a verifier or connector), and records it with source + install pointer + a named fallback. Recommends, never inlines external code.",
      "files": [],
      "expectations": [
        "The loop-builder skill is invoked",
        "Phase 1.5 consults the skill-bank index (references/skill-bank/INDEX.md), not only installed skills",
        "At least one borrowable bank entry is mapped to a specific loop block (e.g. verifier or connector)",
        "Each recommended bank entry is recorded with its source and install pointer plus a NAMED fallback",
        "External code is recommended/referenced, never inlined into the scaffolded loop",
        "The recommendation carries the 'verify unverified mechanics against source' caution"
      ]
    }
```

- [ ] **Step 2: Verify the JSON still parses**

Run: `python3 -c "import json; d=json.load(open('evals/evals.json')); print('valid ·', len(d['evals']), 'evals')"`
Expected: `valid · 6 evals`

- [ ] **Step 3: Commit**

```bash
git add evals/evals.json
git commit -m "test(skill-bank): add bank-consult behavior eval"
```

---

## Task 7: Documentation (`README.md`)

**Files:**
- Modify: `README.md` (repo-layout block and the test-command section)

- [ ] **Step 1: Add skill-bank to the repo-layout block**

In `README.md`, find:

```
│   └── deploy-claude-managed-agents.md     optional deploy target (beta; behind uncertainty flag)
├── scripts/
│   ├── verifier_template.sh               generic predicate runner (exits non-zero on fail)
│   ├── verify_no_p1_unassigned.sh         worked example (operates on gh-style JSON)
│   └── tests/                             red-green tests + fixtures
```

Replace it with:

```
│   ├── deploy-claude-managed-agents.md     optional deploy target (beta; behind uncertainty flag)
│   └── skill-bank/                         curated catalog of borrowable external skills/plugins
│       ├── INDEX.md                        block-tagged entries (pointers only, never vendored)
│       └── sources.yml                     upstream sources + refresh procedure
├── scripts/
│   ├── verifier_template.sh               generic predicate runner (exits non-zero on fail)
│   ├── verify_no_p1_unassigned.sh         worked example (operates on gh-style JSON)
│   ├── lint_skill_bank_index.sh           validates the skill-bank INDEX schema
│   ├── refresh_skill_bank.sh              reports skill-bank drift vs upstream
│   └── tests/                             red-green tests + fixtures
```

- [ ] **Step 2: Update the test-command section**

In `README.md`, find:

```
## Test the bundled verifiers

```bash
bash scripts/tests/test_verifiers.sh
```
```

Replace it with:

```
## Test the bundled scripts

```bash
bash scripts/tests/test_verifiers.sh
bash scripts/tests/test_skill_bank.sh
```
```

- [ ] **Step 3: Verify both test suites pass together**

Run: `bash scripts/tests/test_verifiers.sh && bash scripts/tests/test_skill_bank.sh`
Expected: both suites print `ALL TESTS PASSED`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(skill-bank): document catalog layout and test commands"
```

---

## Final verification

- [ ] **Run every test suite**

Run: `bash scripts/tests/test_verifiers.sh && bash scripts/tests/test_skill_bank.sh`
Expected: both print `ALL TESTS PASSED`.

- [ ] **Lint the real index**

Run: `bash scripts/lint_skill_bank_index.sh`
Expected: `OK: skill-bank index clean (N entries)`, exit 0.

- [ ] **Confirm evals parse and SKILL.md is in budget**

Run: `python3 -c "import json; json.load(open('evals/evals.json'))" && wc -l SKILL.md`
Expected: no JSON error; `SKILL.md` under 500 lines.

---

## Notes for the implementer

- **No emoji in any file** — repo convention (`AGENTS.md`). Use structure/tables instead.
- **Online refresh is intentionally a manual two-step**, not baked into the script: produce an upstream name file with the `list:` commands in `sources.yml`, then run `refresh_skill_bank.sh --upstream <file>`. The script's tested job is the deterministic diff, not network enumeration.
- **Borrow semantics are recommend-and-record only.** Nothing in this feature copies external skill source into the repo; that keeps it license-clean.
- The `references/skill-bank/entries/<slug>.md` detail files from the spec are **out of v1 scope** — add them later, only when a specific entry needs caveats.
```
