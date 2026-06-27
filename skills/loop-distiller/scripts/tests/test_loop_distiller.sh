#!/usr/bin/env bash
# Runs the loop-distiller kernel unit tests (python3 stdlib only).
# Red-green contract: exit 0 == all pass.
# Run: bash skills/loop-distiller/scripts/tests/test_loop_distiller.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
python3 -m unittest discover -s . -p 'test_*.py' -v
