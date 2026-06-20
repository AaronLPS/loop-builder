# Catalog Multi-Path + Per-Source Ref Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate full skill-bank catalogs for `gstack`, `claude-for-legal`, and `awesome-claude-skills` by extending the catalog builder with whitespace-separated multi-path enumeration and an optional per-source `ref` (default `main`).

**Architecture:** Two backward-compatible changes to `scripts/build_skill_bank_catalog.sh` (the untested network adapter) plus matching `references/skill-bank/sources.yml` entries. The pure, unit-tested formatter `scripts/format_catalog.sh` is untouched. The builder learns to (a) read a per-source `ref` and thread it through the `gh api` list call, the raw SKILL.md fetch, and the catalog header; (b) split `enumerate` into multiple paths and, when a source has more than one path, prefix each slug with the path's first component to avoid cross-area collisions. Verification is integration-style: regenerate everything, prove the single-path catalogs (`superpowers.md`, `ecc.md`) are byte-identical (regression guard), and prove the three new catalogs lint clean through the existing test suite.

**Tech Stack:** Bash, `awk`, `gh` CLI, `curl`. Spec: `docs/superpowers/specs/2026-06-20-catalog-multipath-ref-design.md`.

---

## File Structure

- `scripts/build_skill_bank_catalog.sh` — **modify.** Network adapter: add `ref` parsing/threading and the multi-path enumeration loop with slug-prefix derivation. Single responsibility unchanged (generate `catalog/<key>.md` per source).
- `references/skill-bank/sources.yml` — **modify.** Set real `enumerate:`/`ref:` values for the three previously curated-only sources; refresh their inline comments.
- `references/skill-bank/catalog/gstack.md` — **create** (generated).
- `references/skill-bank/catalog/claude-for-legal.md` — **create** (generated).
- `references/skill-bank/catalog/awesome-claude-skills.md` — **create** (generated).
- `scripts/tests/test_skill_bank.sh` — **no change.** Already lints every committed `catalog/*.md`; new files are covered automatically.
- `scripts/format_catalog.sh` — **no change.** Pure tested core.

Network access (`gh` authenticated + `curl`) is required to regenerate catalogs.

---

## Task 1: Extend the builder with `ref` and multi-path enumeration

**Files:**
- Modify: `scripts/build_skill_bank_catalog.sh` (the `awk` source parser, lines ~22-27; the per-source loop body, lines ~28-62)

- [ ] **Step 1: Replace the `awk` source parser to capture full `enumerate` value + `ref`**

The current parser grabs only `$2` for `enumerate` (loses multi-token values) and has no `ref`. Replace the `awk '...' "$SOURCES" | while ...` parser block (lines ~22-27) with this parser, keeping the `| while IFS='|' read ...` pipe that follows:

```bash
awk '
  /^- key:/ {
    if (key!="") print key"|"repo"|"enum"|"ref
    key=$3; repo=""; enum="-"; ref="main"
  }
  /^[[:space:]]+repo:/      { repo=$2 }
  /^[[:space:]]+enumerate:/ { line=$0; sub(/^[[:space:]]*enumerate:[[:space:]]*/,"",line); sub(/[[:space:]]+$/,"",line); enum=line }
  /^[[:space:]]+ref:/       { ref=$2 }
  END { if (key!="") print key"|"repo"|"enum"|"ref }
' "$SOURCES" | while IFS='|' read -r key repo enum ref; do
```

- [ ] **Step 2: Replace the loop body to thread `ref` and iterate paths**

Replace the entire body of the `while` loop (from `key="$(unquote "$key")"...` through the closing `done` at line ~62) with the following. It keeps `unquote`, the `enumerate: "-"` skip, the `format_catalog.sh` call, and tmpfile cleanup; it adds `ref` defaulting, path splitting, the `multi` flag, the slug prefix, and a per-path inner loop feeding one shared `$infile`:

```bash
  key="$(unquote "$key")"; repo="$(unquote "$repo")"; enum="$(unquote "$enum")"; ref="$(unquote "$ref")"
  [ -z "$ref" ] && ref="main"
  [ "$enum" = "-" ] && { echo "skip $key (enumerate: -)"; continue; }
  ownerrepo="${repo#https://github.com/}"; ownerrepo="${ownerrepo%/}"
  set -f; paths=( $enum ); set +f
  multi=0; [ "${#paths[@]}" -gt 1 ] && multi=1
  echo "building $key from $ownerrepo (enumerate: $enum, ref: $ref) ..."
  infile="$(mktemp)"
  for p in "${paths[@]}"; do
    if [ "$p" = "." ]; then
      apipath="contents"; rawprefix=""; slugprefix=""
    else
      apipath="contents/$p"; rawprefix="$p/"
      if [ "$multi" -eq 1 ]; then slugprefix="${p%%/*}/"; else slugprefix=""; fi
    fi
    tmplist="$(mktemp)"
    if ! gh api "repos/$ownerrepo/$apipath?ref=$ref" \
          --jq '.[] | select(.type=="dir") | .name' > "$tmplist" 2>/dev/null; then
      echo "  WARN: could not list $ownerrepo/$p (ref $ref) — skipping path" >&2
      rm -f "$tmplist"; continue
    fi
    while IFS= read -r slug; do
      [ -z "$slug" ] && continue
      sk="$(mktemp)"
      if curl -fsSL "https://raw.githubusercontent.com/$ownerrepo/$ref/${rawprefix}${slug}/SKILL.md" -o "$sk" 2>/dev/null; then
        printf '%s:%s\t%s\n' "$key" "${slugprefix}${slug}" "$sk" >> "$infile"
      else
        rm -f "$sk"
      fi
    done < "$tmplist"
    rm -f "$tmplist"
  done
  if [ ! -s "$infile" ]; then
    echo "  WARN: no SKILL.md found for $key (ref $ref) — skipping $key" >&2
    rm -f "$infile"; continue
  fi
  {
    echo "# $key — full catalog (auto-generated by scripts/build_skill_bank_catalog.sh; do not hand-edit)"
    echo "# source: $repo · synced: $ownerrepo@$ref $TODAY"
    echo
    bash "$FORMAT" < "$infile"
  } > "$OUTDIR/$key.md"
  echo "  wrote catalog/$key.md"
  cut -f2 "$infile" | xargs -r rm -f
  rm -f "$infile"
done
```

- [ ] **Step 3: Syntax-check the script (no network)**

Run: `bash -n scripts/build_skill_bank_catalog.sh && echo OK`
Expected: `OK` (no syntax errors).

- [ ] **Step 4: Commit**

```bash
git add scripts/build_skill_bank_catalog.sh
git commit -m "feat(skill-bank): builder supports per-source ref + multi-path enumerate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Point the three sources at real enumerate paths

**Files:**
- Modify: `references/skill-bank/sources.yml` (the `awesome-claude-skills`, `gstack`, `claude-for-legal` entries)

- [ ] **Step 1: Update the `gstack` entry**

Replace the `gstack` entry's `enumerate: "-"` line and add a `ref:`:

```yaml
- key: gstack
  repo: https://github.com/garrytan/gstack
  enumerate: "."
  ref: main
  list: "# README-curated — review the repo and add standout entries by hand"
```

- [ ] **Step 2: Update the `claude-for-legal` entry**

```yaml
- key: claude-for-legal
  repo: https://github.com/anthropics/claude-for-legal
  enumerate: "ai-governance-legal/skills commercial-legal/skills corporate-legal/skills employment-legal/skills ip-legal/skills litigation-legal/skills privacy-legal/skills product-legal/skills regulatory-legal/skills"
  ref: main
  list: "# README-curated — review the repo and add standout entries by hand"
```

- [ ] **Step 3: Update the `awesome-claude-skills` entry**

Replace its `enumerate: "-"` and trailing catalog note. Keep the aggregator note about drift watching the list; replace only the final "not cleanly enumerable / curated-only" lines:

```yaml
- key: awesome-claude-skills
  repo: https://github.com/ComposioHQ/awesome-claude-skills
  enumerate: "."
  ref: master
  list: "# README-curated — it is itself a list; pull the standout linked skills"
  # Note: this is an aggregator list. An entry's recommended-list `source` may point at the
  # linked skill's own repo (and carry that repo's license), while `synced` tracks
  # this list repo. Drift detection therefore watches the list, not each linked repo.
  # Catalog: enumerates the repo root on master (~25 distinct skills). The 833
  # auto-generated composio-skills/*-automation wrappers are intentionally excluded.
```

- [ ] **Step 4: Verify the parser reads all five entries with correct ref/enum (no catalog write)**

Run this to print what the builder's parser extracts (reuses the same `awk`):

```bash
awk '
  /^- key:/ { if (key!="") print key" | enum=["enum"] ref="ref; key=$3; repo=""; enum="-"; ref="main" }
  /^[[:space:]]+repo:/      { repo=$2 }
  /^[[:space:]]+enumerate:/ { line=$0; sub(/^[[:space:]]*enumerate:[[:space:]]*/,"",line); sub(/[[:space:]]+$/,"",line); enum=line }
  /^[[:space:]]+ref:/       { ref=$2 }
  END { if (key!="") print key" | enum=["enum"] ref="ref }
' references/skill-bank/sources.yml
```

Expected (quotes preserved from the YAML values):
```
superpowers | enum=[skills] ref=main
ecc | enum=[skills] ref=main
awesome-claude-skills | enum=["."] ref=master
gstack | enum=["."] ref=main
claude-for-legal | enum=["ai-governance-legal/skills commercial-legal/skills corporate-legal/skills employment-legal/skills ip-legal/skills litigation-legal/skills privacy-legal/skills product-legal/skills regulatory-legal/skills"] ref=main
```

- [ ] **Step 5: Commit**

```bash
git add references/skill-bank/sources.yml
git commit -m "feat(skill-bank): enumerate gstack, claude-for-legal, awesome-claude-skills

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Regenerate catalogs and verify regression + new output

**Files:**
- Create: `references/skill-bank/catalog/gstack.md`, `references/skill-bank/catalog/claude-for-legal.md`, `references/skill-bank/catalog/awesome-claude-skills.md`
- Touch (must stay identical): `references/skill-bank/catalog/superpowers.md`, `references/skill-bank/catalog/ecc.md`

- [ ] **Step 1: Snapshot the two single-path catalogs for the regression guard**

```bash
cp references/skill-bank/catalog/superpowers.md /tmp/superpowers.before.md
cp references/skill-bank/catalog/ecc.md /tmp/ecc.before.md
```

- [ ] **Step 2: Regenerate all catalogs**

Run: `bash scripts/build_skill_bank_catalog.sh`
Expected: `building …` lines for superpowers, ecc, awesome-claude-skills, gstack, claude-for-legal, each ending `wrote catalog/<key>.md`, then `done.`. No `skip` lines (no source is `enumerate: "-"` anymore).

- [ ] **Step 3: Regression guard — single-path catalogs unchanged except the sync date**

Single-path output must not change structurally. The only allowed diff is the `synced: …@main <date>` date on line 2 if upstream is unchanged; if rows differ, that is upstream drift to inspect, not this feature.

Run:
```bash
diff <(sed '2d' /tmp/superpowers.before.md) <(sed '2d' references/skill-bank/catalog/superpowers.md) && echo "superpowers OK"
diff <(sed '2d' /tmp/ecc.before.md) <(sed '2d' references/skill-bank/catalog/ecc.md) && echo "ecc OK"
```
Expected: `superpowers OK` and `ecc OK` (no row differences). If rows differ, stop and confirm whether upstream genuinely changed before continuing.

- [ ] **Step 4: Verify the three new catalogs exist with sane shape**

Run:
```bash
for k in gstack claude-for-legal awesome-claude-skills; do
  f="references/skill-bank/catalog/$k.md"
  printf '%s: rows=%s header=' "$k" "$(grep -c '^| ' "$f")"
  sed -n '2p' "$f"
done
```
Expected: `gstack` ~31 rows (30 + header), `claude-for-legal` ~110+ rows, `awesome-claude-skills` ~26 rows; each header line shows `synced: <owner>/<repo>@<ref>` with `awesome-claude-skills` showing `@master`. (Row count includes the `| name | description |` header row.)

- [ ] **Step 5: Verify slug shapes — area-qualified for legal, bare for the others**

Run:
```bash
echo "--- claude-for-legal sample (expect area/slug) ---"; grep -E '^\| claude-for-legal:' references/skill-bank/catalog/claude-for-legal.md | head -3
echo "--- no bare collisions: every legal name has a slash after the colon ---"
grep -E '^\| claude-for-legal:' references/skill-bank/catalog/claude-for-legal.md | grep -vE '^\| claude-for-legal:[^ ]+/' && echo "FOUND UNQUALIFIED (bad)" || echo "all qualified OK"
echo "--- gstack sample (expect bare slug, no slash) ---"; grep -E '^\| gstack:' references/skill-bank/catalog/gstack.md | head -3
```
Expected: legal names look like `| claude-for-legal:ip-legal/cease-desist | … |`; the unqualified check prints `all qualified OK`; gstack names look like `| gstack:browse | … |`.

- [ ] **Step 6: Run the skill-bank test suite (lints all committed + regenerated catalogs)**

Run: `bash scripts/tests/test_skill_bank.sh`
Expected: ends with `ALL TESTS PASSED`; the per-file lines include `catalog lint: gstack.md is clean`, `catalog lint: claude-for-legal.md is clean`, `catalog lint: awesome-claude-skills.md is clean`.

- [ ] **Step 7: Run the full verifier suite as a final guard**

Run: `bash scripts/tests/test_verifiers.sh`
Expected: `ALL TESTS PASSED` (no regression in sibling tooling).

- [ ] **Step 8: Commit the generated catalogs**

```bash
git add references/skill-bank/catalog/
git commit -m "feat(skill-bank): add gstack, claude-for-legal, awesome-claude-skills catalogs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Multi-path schema (whitespace-separated `enumerate`) → Task 1 Step 1-2, Task 2.
- Optional `ref:` default `main` → Task 1 (awk `ref="main"`, loop `[ -z "$ref" ] && ref="main"`), threaded into list call, raw fetch, header.
- gstack `enumerate: "."` → Task 2 Step 1; verified bare slugs Task 3 Step 5.
- claude-for-legal nine `*/skills` paths + area-qualified slugs → Task 2 Step 2; verified Task 3 Step 5.
- awesome-claude-skills root-only on `master`, composio-skills excluded → Task 2 Step 3 (`enumerate: "."`, no composio path); verified `@master` Task 3 Step 4.
- Regression: superpowers/ecc byte-identical (sans date) → Task 3 Step 3.
- New catalogs lint clean via existing suite → Task 3 Step 6.
- `format_catalog.sh`, `recommended.md`, search agent untouched → not modified in any task.

**Placeholder scan:** No TBD/TODO; every code step shows complete `awk`/bash; every run step has an exact command and expected output.

**Type/name consistency:** Variable names consistent across steps — `enum`, `ref`, `paths`, `multi`, `slugprefix`, `rawprefix`, `apipath`, `infile`. The pipe-delimited parser emits `key|repo|enum|ref` and the loop reads `key repo enum ref` in the same order. The `awk` snippet in Task 2 Step 4 matches the parser added in Task 1 Step 1.
