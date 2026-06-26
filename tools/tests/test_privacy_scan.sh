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

# --- Scenario F: GitHub web-flow committer (squash/web-merge) => PASS (check 1) ---
# A squash merge on the default branch is a single-parent commit (so --no-merges
# does not exclude it) whose committer is `GitHub <noreply@github.com>`. That is
# GitHub performing the merge, not a personal-identity leak — must be allowed.
d="$(newrepo)"; ( cd "$d"
  echo y > b.txt; git add b.txt
  GIT_COMMITTER_NAME="GitHub" GIT_COMMITTER_EMAIL="noreply@github.com" \
    git commit -q -m "web-flow squash"
)
out="$( cd "$d" && bash "$SCRIPT" HEAD~1 HEAD 2>&1 )"; code=$?
assert_exit "author: GitHub web-flow committer passes" 0 "$code"
assert_contains "author: PASS line present" "PASS [author]" "$out"

echo "----"; echo "passed: $PASS  failed: $FAILED"
[ "$FAILED" -eq 0 ]
