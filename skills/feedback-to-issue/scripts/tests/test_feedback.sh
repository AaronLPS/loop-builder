#!/usr/bin/env bash
# Runs the feedback module unit tests (python3 stdlib only).
# Red-green contract: exit 0 == all pass.
# Run: bash skills/feedback-to-issue/scripts/tests/test_feedback.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
python3 -m unittest discover -s . -p 'test_*.py' -v
