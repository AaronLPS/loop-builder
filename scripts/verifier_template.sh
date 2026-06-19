#!/usr/bin/env bash
# Generic deterministic verifier — the spine of a loop's maker/checker split.
#
# A loop is only as trustworthy as its checker, so the check should be a program
# with a binary verdict, not a model's opinion. This template wraps any checkable
# predicate: it runs the command you give it and turns the result into a clear
# PASS/FAIL with the right exit code, so a scheduler or a parent loop can branch
# on $? without parsing prose.
#
# Usage:
#   verifier_template.sh "<human description>" <predicate-command> [args...]
#
# The predicate is any command that exits 0 when the condition HOLDS and non-zero
# when it does NOT. Examples:
#   verifier_template.sh "tests pass"            npm test
#   verifier_template.sh "no type errors"        npx tsc --noEmit
#   verifier_template.sh "schema is valid"       jq -e . config.json
#   verifier_template.sh "no P1 unassigned"      ./verify_no_p1_unassigned.sh issues.json
#
# Exit codes: 0 = predicate holds (loop may stop / mark done); 1 = it does not
# (feed the failure back to the generator and iterate); 2 = misuse.
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: $0 \"<description>\" <predicate-command> [args...]" >&2
  exit 2
fi

description="$1"
shift

if "$@"; then
  echo "PASS: $description"
  exit 0
else
  status=$?
  echo "FAIL: $description (predicate exited $status)" >&2
  exit 1
fi
