"""Separate deterministic verifier for surfaced scan candidates.

A candidate is sound only if it recurred enough (>= N distinct sessions), spans
enough of the loop blocks (>= K), and active signatures are unique. This is the
maker/checker split: the scan proposes; this program checks. Run standalone to
exit non-zero on any problem.

K=3 requires the core loop shape (discovery+action+verify) but leaves vcs
optional, because a loop's commit/push step is usually the human gate it must
NOT cross autonomously, so requiring vcs would wrongly filter out triage/draft/
review loops.
"""
from __future__ import annotations

import json
import sys

DEFAULT_N = 3
# K=3: require the 3 core blocks (discovery+action+verify); vcs is optional
# because commit/push is typically the human gate a loop must not cross autonomously.
DEFAULT_K = 3
_ACTIVE = ("new", "surfaced")


def verify(candidates: list, n: int = DEFAULT_N, k: int = DEFAULT_K) -> tuple:
    problems = []
    seen_sigs = set()
    for c in candidates:
        if c.get("status") not in _ACTIVE:
            continue
        label = c.get("label") or c.get("id") or c.get("signature")
        if c.get("count", 0) < n:
            problems.append(f"{label}: only {c.get('count', 0)} recurrence(s), need {n}")
        if len(c.get("blocks", [])) < k:
            problems.append(f"{label}: only {len(c.get('blocks', []))} block(s), need {k}")
        sig_key = c.get("signature")
        if sig_key in seen_sigs:
            problems.append(f"{label}: duplicate active signature {sig_key!r}")
        seen_sigs.add(sig_key)
    return (len(problems) == 0, problems)


def _main() -> int:
    # Reads a JSON array of candidates from stdin; exit 0 == all sound.
    candidates = json.load(sys.stdin)
    ok, problems = verify(candidates)
    for p in problems:
        print(f"FAIL: {p}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())
