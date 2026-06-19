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

bash "$SCRIPTS/lint_skill_bank_index.sh" --file /nonexistent/path.md >/dev/null 2>&1
check "lint: missing file -> exit 2" 2 $?

# --- refresh_skill_bank.sh -------------------------------------------------
bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_insync.txt" >/dev/null 2>&1
check "refresh: index matches upstream -> in sync" 0 $?

bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_drift.txt" >/dev/null 2>&1
check "refresh: added/removed drift -> non-zero" 1 $?

bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_stale.txt" >/dev/null 2>&1
check "refresh: stale ref -> non-zero" 1 $?

bash "$SCRIPTS/refresh_skill_bank.sh" --index "$FIX/index_good.md" --upstream "$FIX/upstream_empty.txt" >/dev/null 2>&1
check "refresh: empty upstream -> all removed (non-zero)" 1 $?

timeout 5 bash "$SCRIPTS/refresh_skill_bank.sh" --upstream >/dev/null 2>&1
check "refresh: --upstream with no value -> exit 2 (no hang)" 2 $?

echo "----"
if [ "$fails" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$fails TEST(S) FAILED"
  exit 1
fi
