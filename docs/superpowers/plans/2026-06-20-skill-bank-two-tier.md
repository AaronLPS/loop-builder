# skill-bank Two-Tier Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a comprehensive Tier-2 catalog (full per-source skill listings, read on demand) beneath the curated Tier-1 INDEX, so the skill-bank has high recall without inflating per-build token cost.

**Architecture:** Tier 1 is the existing curated `INDEX.md` (loaded every build). Tier 2 is one auto-generated `catalog/<key>.md` per enumerable source (name + one-line description), read only when a needed block isn't covered by Tier-1 standouts. A pure formatter turns SKILL.md frontmatter into catalog rows (unit-tested); a network adapter drives it from `gh` (documented, not unit-tested). Phase 1.5 gains a conditional Tier-2 widening step.

**Tech Stack:** Bash (`#!/usr/bin/env bash`), awk, markdown, `gh` CLI + `curl` (network adapter only), JSON (evals).

**Spec:** `docs/superpowers/specs/2026-06-20-skill-bank-two-tier-design.md`
**Builds on:** the existing skill-bank (`references/skill-bank/`, `scripts/*skill_bank*`).
**Branch:** `feature/skill-bank` (already checked out).

---

## File Structure

| Path | Responsibility | Action |
|------|----------------|--------|
| `references/skill-bank/sources.yml` | gains an `enumerate:` field per source | Modify |
| `scripts/format_catalog.sh` | pure formatter: `name<TAB>path` lines in → catalog table out | Create |
| `scripts/build_skill_bank_catalog.sh` | network adapter: enumerate sources, write `catalog/<key>.md` | Create |
| `scripts/lint_skill_bank_catalog.sh` | schema check for catalog files | Create |
| `references/skill-bank/catalog/<key>.md` | Tier-2 per-source listings (generated seed) | Create |
| `scripts/tests/test_skill_bank.sh` | add formatter + catalog-lint + seed-catalog cases | Modify |
| `scripts/tests/fixtures/skill_bank/catalog_src/` | fixture SKILL.md files for the formatter test | Create |
| `scripts/tests/fixtures/skill_bank/catalog_expected.md` | golden formatter output | Create |
| `scripts/tests/fixtures/skill_bank/catalog_good.md` / `catalog_bad.md` | lint fixtures | Create |
| `SKILL.md` | Phase 1.5 `1.5b` two-tier step + checklist gate | Modify |
| `references/skill-bank/INDEX.md` | header note pointing at `catalog/` | Modify |
| `evals/evals.json` | Tier-2 escalation eval (id 7) | Modify |
| `README.md` | layout update | Modify |

Naming conventions (unchanged): entry `name` is `<source-key>:<slug>`.

---

## Task 1: Add `enumerate:` to `sources.yml`

**Files:**
- Modify: `references/skill-bank/sources.yml`

- [ ] **Step 1: Determine each source's enumerate path**

For each source, check the repo layout (via `gh api repos/<owner>/<repo>/contents` or WebFetch of the repo) and decide the single directory whose immediate subdirectories are skills. Set `enumerate:` to that path, or to `-` if the source has no single machine-listable skills directory (aggregator/README-only, or skills scattered across many dirs).

Starting points to VERIFY (do not assume — confirm against the live repo):
- `superpowers` → likely `skills`
- `ecc` → likely `skills`
- `gstack` → check whether skills live at repo root or under a dir; set accordingly or `-`
- `claude-for-legal` → skills are under sub-areas; if there's no single root, set `-`
- `awesome-claude-skills` → `-` (it is an aggregator list)

- [ ] **Step 2: Edit `sources.yml`**

Add an `enumerate:` line to each source block, immediately after its `repo:` line. For example, the `superpowers` block becomes:

```yaml
- key: superpowers
  repo: https://github.com/obra/superpowers
  enumerate: skills
  list: "gh api repos/obra/superpowers/contents/skills --jq '.[].name' | sed 's#^#superpowers:#'"
```

Apply the same pattern to every block, using the verified value from Step 1 (`enumerate: -` for non-enumerable sources). Leave all existing comment lines intact.

- [ ] **Step 3: Verify it still reads as before + commit**

Run: `grep -c 'enumerate:' references/skill-bank/sources.yml`
Expected: `5` (one per source).

```bash
git add references/skill-bank/sources.yml
git commit -m "feat(skill-bank): add enumerate field to sources.yml for Tier-2"
```

---

## Task 2: The pure formatter `format_catalog.sh` (TDD)

**Files:**
- Create: `scripts/tests/fixtures/skill_bank/catalog_src/{alpha,beta,gamma,delta}/SKILL.md`
- Create: `scripts/tests/fixtures/skill_bank/catalog_expected.md`
- Modify: `scripts/tests/test_skill_bank.sh`
- Create: `scripts/format_catalog.sh`

- [ ] **Step 1: Create the fixture SKILL.md files**

Create `scripts/tests/fixtures/skill_bank/catalog_src/alpha/SKILL.md`:

```markdown
---
name: alpha
description: Use when doing alpha things on a schedule.
---
# Alpha
body
```

Create `scripts/tests/fixtures/skill_bank/catalog_src/beta/SKILL.md` (folded multi-line description):

```markdown
---
name: beta
description: >-
  Use when doing beta work across
  multiple lines that fold together.
---
# Beta
```

Create `scripts/tests/fixtures/skill_bank/catalog_src/gamma/SKILL.md` (no description field):

```markdown
---
name: gamma
---
# Gamma
```

Create `scripts/tests/fixtures/skill_bank/catalog_src/delta/SKILL.md` (quoted description containing pipes):

```markdown
---
name: delta
description: "Use for X | Y | Z choices."
---
# Delta
```

- [ ] **Step 2: Create the golden expected output**

Create `scripts/tests/fixtures/skill_bank/catalog_expected.md` (exactly this — note: folded collapses to one line, missing becomes `(no description)`, `|` becomes `/`):

```markdown
| name | description |
|------|-------------|
| src:alpha | Use when doing alpha things on a schedule. |
| src:beta | Use when doing beta work across multiple lines that fold together. |
| src:gamma | (no description) |
| src:delta | Use for X / Y / Z choices. |
```

- [ ] **Step 3: Write the failing test (append to `test_skill_bank.sh`)**

In `scripts/tests/test_skill_bank.sh`, find the closing block:

```bash
echo "----"
if [ "$fails" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$fails TEST(S) FAILED"
  exit 1
fi
```

Insert BEFORE it:

```bash
# --- format_catalog.sh -----------------------------------------------------
fmt_in="$(mktemp)"
for n in alpha beta gamma delta; do
  printf 'src:%s\t%s\n' "$n" "$FIX/catalog_src/$n/SKILL.md" >> "$fmt_in"
done
bash "$SCRIPTS/format_catalog.sh" < "$fmt_in" | diff -u - "$FIX/catalog_expected.md" >/dev/null 2>&1
check "format_catalog: fixtures -> expected table" 0 $?
rm -f "$fmt_in"

```

- [ ] **Step 4: Run the test to verify it fails**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: the `format_catalog` case FAILS (script missing); earlier cases still PASS.

- [ ] **Step 5: Write `format_catalog.sh`**

Create `scripts/format_catalog.sh`:

```bash
#!/usr/bin/env bash
# Pure formatter for Tier-2 catalogs. Reads "name<TAB>path-to-SKILL.md" lines on
# stdin and writes a markdown table to stdout: a header row, a separator, then one
# row per entry "| name | one-line description |". The description is read from the
# SKILL.md YAML frontmatter `description:` field, collapsed to a single line; any '|'
# is replaced with '/'; a missing/empty description becomes "(no description)".
# No network, no file writes — this is the unit-tested core of the catalog builder.
set -u

extract_desc() {  # $1 = path to a SKILL.md ; echoes the raw description (may be empty)
  awk '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/  { exit }
    infm {
      if (indesc) {
        if ($0 ~ /^[[:space:]]+/) { line=$0; sub(/^[[:space:]]+/,"",line); desc=desc " " line; next }
        else { indesc=0 }
      }
      if ($0 ~ /^description:[[:space:]]*/) {
        val=$0; sub(/^description:[[:space:]]*/,"",val)
        if (val ~ /^[|>][+-]?[[:space:]]*$/) { indesc=1; next }
        desc=val; next
      }
    }
    END { gsub(/^[\047"]+|[\047"]+$/,"",desc); print desc }
  ' "$1"
}

printf '| name | description |\n'
printf '|------|-------------|\n'
while IFS=$'\t' read -r name path; do
  [ -z "$name" ] && continue
  d="$(extract_desc "$path")"
  # collapse newlines/spaces, replace pipes
  d="$(printf '%s' "$d" | tr '\n|' ' /' | tr -s ' ')"
  # trim
  d="${d#"${d%%[![:space:]]*}"}"; d="${d%"${d##*[![:space:]]}"}"
  [ -z "$d" ] && d="(no description)"
  printf '| %s | %s |\n' "$name" "$d"
done
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: `ALL TESTS PASSED` (the format_catalog case now passes).

- [ ] **Step 7: Commit**

```bash
git add scripts/format_catalog.sh scripts/tests/test_skill_bank.sh scripts/tests/fixtures/skill_bank/catalog_src scripts/tests/fixtures/skill_bank/catalog_expected.md
git commit -m "feat(skill-bank): add Tier-2 catalog formatter with golden test"
```

---

## Task 3: The catalog linter `lint_skill_bank_catalog.sh` (TDD)

**Files:**
- Create: `scripts/tests/fixtures/skill_bank/catalog_good.md`
- Create: `scripts/tests/fixtures/skill_bank/catalog_bad.md`
- Modify: `scripts/tests/test_skill_bank.sh`
- Create: `scripts/lint_skill_bank_catalog.sh`

- [ ] **Step 1: Create the lint fixtures**

Create `scripts/tests/fixtures/skill_bank/catalog_good.md`:

```markdown
# example — full catalog (auto-generated; do not hand-edit)
# source: https://github.com/example/example · synced: example/example@main 2026-06-20

| name | description |
|------|-------------|
| example:alpha | does alpha things |
| example:beta | does beta things |
```

Create `scripts/tests/fixtures/skill_bank/catalog_bad.md` (two faults: a name with no `:` colon, and a row with only one column):

```markdown
# example — full catalog (auto-generated; do not hand-edit)
# source: https://github.com/example/example · synced: example/example@main 2026-06-20

| name | description |
|------|-------------|
| nocolon | missing the key prefix |
| example:short |
```

- [ ] **Step 2: Write the failing test (append to `test_skill_bank.sh`)**

In `scripts/tests/test_skill_bank.sh`, find the `format_catalog` block you added in Task 2 (ending with `rm -f "$fmt_in"`). Insert AFTER it (before the `echo "----"` closing block):

```bash
# --- lint_skill_bank_catalog.sh --------------------------------------------
bash "$SCRIPTS/lint_skill_bank_catalog.sh" --file "$FIX/catalog_good.md" >/dev/null 2>&1
check "catalog lint: well-formed -> pass" 0 $?

bash "$SCRIPTS/lint_skill_bank_catalog.sh" --file "$FIX/catalog_bad.md" >/dev/null 2>&1
check "catalog lint: malformed -> fail" 1 $?

bash "$SCRIPTS/lint_skill_bank_catalog.sh" --file /nonexistent/catalog.md >/dev/null 2>&1
check "catalog lint: missing file -> exit 2" 2 $?

```

- [ ] **Step 3: Run the test to verify it fails**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: the three catalog-lint cases FAIL (script missing); earlier cases PASS.

- [ ] **Step 4: Write `lint_skill_bank_catalog.sh`**

Create `scripts/lint_skill_bank_catalog.sh`:

```bash
#!/usr/bin/env bash
# Lint a Tier-2 catalog file: every data row must have exactly 2 columns, a name in
# <key>:<slug> form (contains a colon), and a non-empty description. Exit 0 clean,
# 1 violations, 2 usage error. Run:
#   bash scripts/lint_skill_bank_catalog.sh --file references/skill-bank/catalog/<key>.md
set -u

FILE=""
if [ "${1:-}" = "--file" ]; then FILE="${2:-}"; fi
if [ -z "$FILE" ]; then echo "usage: lint_skill_bank_catalog.sh --file FILE" >&2; exit 2; fi
if [ ! -f "$FILE" ]; then echo "catalog-lint: file not found: $FILE" >&2; exit 2; fi

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

violations=0
row=0
while IFS= read -r line; do
  case "$line" in \|*) : ;; *) continue ;; esac
  if printf '%s' "$line" | grep -qE '^\|[[:space:]]*:?-{3,}:?[[:space:]]*\|'; then continue; fi
  body="${line#|}"; body="${body%|}"
  IFS='|' read -ra raw <<< "$body"
  cells=()
  for c in "${raw[@]}"; do cells+=("$(trim "$c")"); done
  if [ "${cells[0]}" = "name" ]; then continue; fi
  row=$((row + 1))
  rid="row $row (${cells[0]:-<empty>})"
  if [ "${#cells[@]}" -ne 2 ]; then
    echo "FAIL: $rid has ${#cells[@]} columns, expected 2"; violations=$((violations + 1)); continue
  fi
  name="${cells[0]}"; desc="${cells[1]}"
  case "$name" in
    *:*) : ;;
    *) echo "FAIL: $rid name '$name' is not <key>:<slug>"; violations=$((violations + 1)) ;;
  esac
  if [ -z "$desc" ]; then echo "FAIL: $rid empty description"; violations=$((violations + 1)); fi
done < "$FILE"

if [ "$violations" -eq 0 ]; then
  echo "OK: catalog clean ($row entries)"; exit 0
else
  echo "$violations violation(s)"; exit 1
fi
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: `ALL TESTS PASSED`.

- [ ] **Step 6: Commit**

```bash
git add scripts/lint_skill_bank_catalog.sh scripts/tests/test_skill_bank.sh scripts/tests/fixtures/skill_bank/catalog_good.md scripts/tests/fixtures/skill_bank/catalog_bad.md
git commit -m "feat(skill-bank): add Tier-2 catalog linter with tests"
```

---

## Task 4: The builder + generated seed catalogs

**Files:**
- Create: `scripts/build_skill_bank_catalog.sh`
- Create: `references/skill-bank/catalog/<key>.md` (generated, for enumerable sources)
- Modify: `scripts/tests/test_skill_bank.sh` (guard committed catalogs)

- [ ] **Step 1: Write `build_skill_bank_catalog.sh`**

Create `scripts/build_skill_bank_catalog.sh`:

```bash
#!/usr/bin/env bash
# Generate Tier-2 catalogs from upstream. For each sources.yml entry whose
# `enumerate:` is not '-', list its skill subdirectories, fetch each SKILL.md, and
# write references/skill-bank/catalog/<key>.md (header + table). The table body is
# produced by scripts/format_catalog.sh (unit-tested); this script is the network
# adapter (uses gh + curl) and is not unit-tested. Run:
#   bash scripts/build_skill_bank_catalog.sh
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SOURCES="$ROOT/references/skill-bank/sources.yml"
OUTDIR="$ROOT/references/skill-bank/catalog"
FORMAT="$HERE/format_catalog.sh"
TODAY="$(date +%F)"

command -v gh >/dev/null 2>&1 || { echo "build: gh CLI required" >&2; exit 2; }
mkdir -p "$OUTDIR"

# Parse sources.yml blocks into "key|repo|enumerate" lines.
awk '
  /^- key:/                 { if (key!="") print key"|"repo"|"enum; key=$3; repo=""; enum="-" }
  /^[[:space:]]+repo:/      { repo=$2 }
  /^[[:space:]]+enumerate:/ { enum=$2 }
  END { if (key!="") print key"|"repo"|"enum }
' "$SOURCES" | while IFS='|' read -r key repo enum; do
  [ "$enum" = "-" ] && { echo "skip $key (enumerate: -)"; continue; }
  ownerrepo="${repo#https://github.com/}"; ownerrepo="${ownerrepo%/}"
  echo "building $key from $ownerrepo/$enum ..."
  tmplist="$(mktemp)"
  if ! gh api "repos/$ownerrepo/contents/$enum?ref=main" \
        --jq '.[] | select(.type=="dir") | .name' > "$tmplist" 2>/dev/null; then
    echo "  WARN: could not list $ownerrepo/$enum — skipping $key" >&2
    rm -f "$tmplist"; continue
  fi
  infile="$(mktemp)"
  while IFS= read -r slug; do
    [ -z "$slug" ] && continue
    sk="$(mktemp)"
    if curl -fsSL "https://raw.githubusercontent.com/$ownerrepo/main/$enum/$slug/SKILL.md" -o "$sk" 2>/dev/null; then
      printf '%s:%s\t%s\n' "$key" "$slug" "$sk" >> "$infile"
    else
      rm -f "$sk"
    fi
  done < "$tmplist"
  {
    echo "# $key — full catalog (auto-generated by scripts/build_skill_bank_catalog.sh; do not hand-edit)"
    echo "# source: $repo · synced: $ownerrepo@main $TODAY"
    echo
    bash "$FORMAT" < "$infile"
  } > "$OUTDIR/$key.md"
  echo "  wrote catalog/$key.md ($(grep -c '^| ' "$OUTDIR/$key.md") header+rows)"
  cut -f2 "$infile" | xargs -r rm -f
  rm -f "$infile" "$tmplist"
done
echo "done."
```

- [ ] **Step 2: Generate the seed catalogs from real data**

Run: `bash scripts/build_skill_bank_catalog.sh`

This writes `references/skill-bank/catalog/<key>.md` for each enumerable source. Requirements:
- At least `superpowers.md` MUST be generated with real entries (superpowers has a clean `skills/` dir).
- If `gh` is unavailable or a source fails to fetch, the script skips it with a WARN. Ensure at least two catalogs are produced from real upstream data. If a source you set as enumerable in Task 1 fails to enumerate, change its `enumerate:` back to `-` in `sources.yml` (and `git add` that change with this task) rather than committing an empty/broken catalog.
- Open one generated file and sanity-check it: header lines present, a `| name | description |` table, real skill slugs.

- [ ] **Step 3: Verify the generated catalogs lint clean**

For each generated file, run:
`bash scripts/lint_skill_bank_catalog.sh --file references/skill-bank/catalog/<key>.md`
Expected: `OK: catalog clean (N entries)` and exit 0 for each. Fix any row the linter rejects (a stray `|` in a description should already be handled by the formatter; if not, regenerate).

- [ ] **Step 4: Add a regression test guarding the committed catalogs**

In `scripts/tests/test_skill_bank.sh`, find the catalog-lint block from Task 3 (ending with the `catalog lint: missing file -> exit 2` case). Insert AFTER it (before `echo "----"`):

```bash
# every committed Tier-2 catalog must lint clean
for cat in "$ROOT"/references/skill-bank/catalog/*.md; do
  [ -e "$cat" ] || continue
  bash "$SCRIPTS/lint_skill_bank_catalog.sh" --file "$cat" >/dev/null 2>&1
  check "catalog lint: $(basename "$cat") is clean" 0 $?
done

```

- [ ] **Step 5: Run the full suite**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: `ALL TESTS PASSED` (including one "catalog lint: <key>.md is clean" line per committed catalog).

- [ ] **Step 6: Commit**

```bash
git add scripts/build_skill_bank_catalog.sh references/skill-bank/catalog scripts/tests/test_skill_bank.sh references/skill-bank/sources.yml
git commit -m "feat(skill-bank): add catalog builder and generated Tier-2 seed catalogs"
```

---

## Task 5: Wire the two tiers into Phase 1.5 + INDEX header (`SKILL.md`, `INDEX.md`)

**Files:**
- Modify: `SKILL.md` (Phase 1.5 `1.5b` and the output checklist)
- Modify: `references/skill-bank/INDEX.md` (intro note)

- [ ] **Step 1: Replace the `1.5b` paragraph in `SKILL.md`**

Find this exact passage:

```
**1.5b — skill-bank — do not skip, even if 1.5a already seems to cover a block.**
**Read `references/skill-bank/INDEX.md`** (a curated catalog of proven external
skills/plugins/workflows, each tagged by the block it serves) and scan it for the
blocks this loop needs. The whole point is to surface proven prior art *before you
settle*, so you compose instead of rebuild — an installed capability covering a block
is exactly when people skip this and miss a better-fitting borrow. Recommend-and-record
only: surface the source + install pointer + a named fallback; never inline external
code. Bank entries are externally evolving — keep the "verify unverified mechanics"
flag on them. If nothing in the bank fits, record that explicitly ("skill-bank: none
applicable — <reason>") rather than silently skipping the read.
```

Replace it with:

```
**1.5b — skill-bank — do not skip, even if 1.5a already seems to cover a block.** The
bank has two tiers; use them in order:

*Tier 1 (always).* **Read `references/skill-bank/INDEX.md`** — a curated, block-tagged
catalog of standout external skills/plugins/workflows — and scan it for the blocks
this loop needs.

*Tier 2 (when Tier 1 falls short).* For any block the loop needs that the Tier-1
standouts don't cover well, **read the relevant `references/skill-bank/catalog/<source>.md`**
— the full per-source listing (name + one-line description) — and judge candidates by
their description. Widen only the *uncovered* block(s), and only the source(s)
plausibly holding them — not every catalog. Record "skill-bank: none applicable —
<reason>" only *after* this widening, never before.

Borrow semantics are unchanged: recommend-and-record only (surface source + install
pointer + a named fallback; never inline external code), and confirm license and
mechanics against source at borrow time. The point is to surface proven prior art
before you settle, so you compose instead of rebuild — an installed capability
covering a block is exactly when people skip this and miss a better-fitting borrow.
```

- [ ] **Step 2: Update the checklist gate in `SKILL.md`**

Find:

```
- [ ] **skill-bank INDEX consulted** (1.5b — `references/skill-bank/INDEX.md`): relevant entries shortlisted, or "none applicable — <reason>" recorded. Not skippable.
```

Replace with:

```
- [ ] **skill-bank consulted** (1.5b): Tier-1 `INDEX.md` scanned; for any block its standouts don't cover, the relevant Tier-2 `catalog/<source>.md` was read. "none applicable — <reason>" recorded only after that widening. Not skippable.
```

- [ ] **Step 3: Add a tier note to `INDEX.md`**

In `references/skill-bank/INDEX.md`, find the sentence:

```
the refresh procedure live in `sources.yml`.
```

Replace it with:

```
the refresh procedure live in `sources.yml`. This file is **Tier 1** — the curated
standouts, loaded on every loop build. For comprehensive coverage, `catalog/<source>.md`
holds the full per-source listing (auto-generated), read on demand when these standouts
don't cover a block the loop needs.
```

- [ ] **Step 4: Verify and commit**

Run: `grep -n "catalog/<source>.md" SKILL.md && grep -n "Tier 1" references/skill-bank/INDEX.md && wc -l SKILL.md`
Expected: the grep lines print; `SKILL.md` is under 500 lines.

```bash
git add SKILL.md references/skill-bank/INDEX.md
git commit -m "feat(skill-bank): wire two-tier (Tier-1 + on-demand Tier-2) into Phase 1.5"
```

---

## Task 6: Tier-2 escalation eval (`evals/evals.json`)

**Files:**
- Modify: `evals/evals.json`

- [ ] **Step 1: Add eval id 7**

In `evals/evals.json`, add a comma after the `"id": 6` object's closing brace and insert this object before the array's closing `]`:

```json
    {
      "id": 7,
      "prompt": "I need a weekly agent that proofreads our changelog entries for tone and house style before release — and I'd like to reuse a proven writing/editing skill rather than invent a style checker, even a fairly niche one",
      "expected_output": "Triggers loop-builder; in Phase 1.5 it scans Tier-1 INDEX, finds no standout covering the 'style/editing verifier' block, and ESCALATES to read a relevant Tier-2 references/skill-bank/catalog/<source>.md, surfacing a candidate by its description (or recording 'none applicable' only after that widening). Recommends, never inlines.",
      "files": [],
      "expectations": [
        "The loop-builder skill is invoked",
        "Phase 1.5 first scans the Tier-1 INDEX (references/skill-bank/INDEX.md)",
        "Because the Tier-1 standouts do not cover the needed block, it reads a Tier-2 catalog file (references/skill-bank/catalog/<source>.md)",
        "It widens only the uncovered block and only plausibly-relevant source(s), not every catalog",
        "A candidate is surfaced from the Tier-2 listing by its description, OR 'skill-bank: none applicable — <reason>' is recorded only after the Tier-2 read",
        "Borrow stays recommend-and-record with a named fallback; external code is never inlined"
      ]
    }
```

- [ ] **Step 2: Verify JSON parses**

Run: `python3 -c "import json; d=json.load(open('evals/evals.json')); print('valid ·', len(d['evals']), 'evals')"`
Expected: `valid · 7 evals`

- [ ] **Step 3: Commit**

```bash
git add evals/evals.json
git commit -m "test(skill-bank): add Tier-2 escalation behavior eval"
```

---

## Task 7: Documentation (`README.md`)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the repo-layout block**

In `README.md`, read the repository-layout code fence. Find the skill-bank subtree and the scripts list, currently:

```
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

Replace it with:

```
│   └── skill-bank/                         catalog of borrowable external skills/plugins
│       ├── INDEX.md                        Tier 1: curated block-tagged standouts (loaded every build)
│       ├── catalog/                        Tier 2: full per-source listings (read on demand)
│       └── sources.yml                     upstream sources + refresh/build procedure
├── scripts/
│   ├── verifier_template.sh               generic predicate runner (exits non-zero on fail)
│   ├── verify_no_p1_unassigned.sh         worked example (operates on gh-style JSON)
│   ├── lint_skill_bank_index.sh           validates the Tier-1 INDEX schema
│   ├── refresh_skill_bank.sh              reports Tier-1 drift vs upstream
│   ├── format_catalog.sh                  Tier-2: SKILL.md frontmatter -> catalog rows
│   ├── build_skill_bank_catalog.sh        Tier-2: generate per-source catalogs from upstream
│   ├── lint_skill_bank_catalog.sh         validates Tier-2 catalog schema
│   └── tests/                             red-green tests + fixtures
```

If the actual README text differs slightly, adapt to it while preserving the intent (add `catalog/` under skill-bank; add the three new scripts; relabel INDEX/refresh as Tier 1).

- [ ] **Step 2: Verify both suites still pass + commit**

Run: `bash scripts/tests/test_verifiers.sh && bash scripts/tests/test_skill_bank.sh`
Expected: both print `ALL TESTS PASSED`.

```bash
git add README.md
git commit -m "docs(skill-bank): document the two-tier catalog layout"
```

---

## Final verification

- [ ] **Run all suites + lints**

Run:
```bash
bash scripts/tests/test_verifiers.sh && bash scripts/tests/test_skill_bank.sh
bash scripts/lint_skill_bank_index.sh
for c in references/skill-bank/catalog/*.md; do bash scripts/lint_skill_bank_catalog.sh --file "$c"; done
python3 -c "import json; json.load(open('evals/evals.json'))" && echo "evals OK"
wc -l SKILL.md
```
Expected: both suites `ALL TESTS PASSED`; index + every catalog `OK ... clean`; evals OK; `SKILL.md` under 500 lines.

---

## Notes for the implementer

- **No emoji in any file** (repo convention, `AGENTS.md`). Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **The formatter is the tested core; the builder is a documented network adapter.** Don't try to unit-test `build_skill_bank_catalog.sh` against the network — its formatting logic lives in `format_catalog.sh`, which IS tested. The builder is exercised once to produce the committed seed catalogs, which are then guarded by the catalog linter.
- **Tier 2 is read from committed files only** — nothing in this feature fetches the network during a loop build.
- **Single `enumerate` path per source** is intentional v1 scope; a source whose skills span multiple directories may be partially listed or set to `-`. Don't add multi-path enumeration.
