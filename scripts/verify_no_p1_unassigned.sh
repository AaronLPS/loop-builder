#!/usr/bin/env bash
# Worked-example verifier from the loop-engineering reference: the morning-triage
# loop's "done" check. Predicate: every P1 issue has an assignee.
#
# It reads issues as JSON (an array of objects) — the shape `gh issue list --json
# number,title,labels,assignees` produces, or a saved fixture for offline testing.
# Keeping the check deterministic and separate from the agent that did the triage
# is the whole point: the maker does not get to grade its own homework.
#
# Usage:
#   verify_no_p1_unassigned.sh <issues.json>     # read from a file
#   gh issue list --json number,title,labels,assignees | verify_no_p1_unassigned.sh
#
# A P1 issue is one whose labels include "P1". It counts as assigned if it has a
# non-empty `assignee` (string) OR a non-empty `assignees` array — so it works
# with both simplified fixtures and real `gh` output.
#
# Exit codes: 0 = no P1 issue is unassigned (PASS); 1 = at least one is (FAIL);
# 2 = misuse / bad input.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required but not found on PATH" >&2
  exit 2
fi

if [ "$#" -ge 1 ]; then
  input="$1"
  [ -f "$input" ] || { echo "error: no such file: $input" >&2; exit 2; }
  src() { cat "$input"; }
else
  src() { cat; }   # read from stdin
fi

# Labels may be ["P1"] (fixture) or [{"name":"P1"}] (gh). Assignment may be a
# scalar `assignee` or an `assignees` array. Normalize both, then select P1
# issues that have neither form of assignment.
unassigned="$(src | jq -r '
  def labelnames: (.labels // []) | map(if type=="object" then .name else . end);
  def assigned:
    ((.assignee // "") | tostring | length > 0)
    or ((.assignees // []) | length > 0);
  [ .[] | select((labelnames | index("P1")) != null) | select(assigned | not) | .number ]
  | .[]
')"

if [ -z "$unassigned" ]; then
  echo "PASS: no P1 issue is unassigned"
  exit 0
else
  echo "FAIL: P1 issue(s) without an assignee:" >&2
  echo "$unassigned" | while read -r n; do echo "  - #$n" >&2; done
  exit 1
fi
