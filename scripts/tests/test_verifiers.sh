#!/usr/bin/env bash
# Tests for the bundled verifier scripts. Red-green discipline: these encode the
# contract (exit 0 == predicate holds, non-zero == it does not) so the scripts
# stay trustworthy. Run: bash scripts/tests/test_verifiers.sh
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$(cd "$HERE/.." && pwd)"
FIX="$HERE/fixtures"
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

# --- verify_no_p1_unassigned.sh ---------------------------------------------
bash "$SCRIPTS/verify_no_p1_unassigned.sh" "$FIX/p1_passing.json" >/dev/null 2>&1
check "no_p1_unassigned: all P1 assigned -> pass" 0 $?

bash "$SCRIPTS/verify_no_p1_unassigned.sh" "$FIX/p1_failing.json" >/dev/null 2>&1
check "no_p1_unassigned: a P1 unassigned -> fail" 1 $?

# --- verifier_template.sh (generic predicate runner) ------------------------
bash "$SCRIPTS/verifier_template.sh" "true predicate holds" true >/dev/null 2>&1
check "template: passing predicate -> exit 0" 0 $?

bash "$SCRIPTS/verifier_template.sh" "false predicate fails" false >/dev/null 2>&1
check "template: failing predicate -> exit 1" 1 $?

echo "----"
if [ "$fails" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$fails TEST(S) FAILED"
  exit 1
fi
