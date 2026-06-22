#!/usr/bin/env bash
# Runs the feedback module unit tests (python3 stdlib only).
# Red-green contract: exit 0 == all pass. Run: bash scripts/tests/test_feedback.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"
python3 -m unittest discover -s scripts/tests/feedback -p 'test_*.py' -v
