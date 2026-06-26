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

# 1. Author/committer identity must be a noreply address. Allowed: the configured
#    user-noreply domain, plus GitHub's web-flow committer `noreply@github.com`
#    (used for squash/web merges on the default branch — GitHub doing the merge,
#    not a personal-identity leak; squash commits are single-parent so --no-merges
#    does not exclude them).
allow="@${DOMAIN//./\\.}\$|^noreply@github\.com\$"
bad="$(git log --no-merges --format='%ae%n%ce' "$RANGE" 2>/dev/null | sort -u | grep -vE "$allow" || true)"
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
  | grep -E '(^\.superpowers/sdd/|/scratchpad/|/claude-[0-9])' || true)"
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
