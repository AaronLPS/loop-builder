"""Coarse, high-recall blocking key over a condense()-shaped dict.

This is NOT a semantic judgment — it only groups likely-related sessions cheaply
so the (Phase 2b) LLM clustering is batchable. Tuned to OVER-group: surface
variation in command args/order must not change the key. The keep/discard call
belongs to the LLM, never here.
"""
from __future__ import annotations

_BUCKETS = ("discovery", "action", "verify", "vcs")


def _verb(ref: dict) -> str:
    tool = ref.get("tool") or ""
    if tool == "Bash":
        toks = (ref.get("hint") or "").split()
        return toks[0].lower() if toks else "bash"
    return tool.lower()


def signature(condensed: dict) -> str:
    counts = condensed.get("counts", {})
    blocks = tuple(b for b in _BUCKETS if counts.get(b, 0) > 0)
    verbs = set()
    for b in _BUCKETS:
        for ref in condensed.get(b, []):
            v = _verb(ref)
            if v:
                verbs.add(v)
    return f"{','.join(blocks)}|{','.join(sorted(verbs))}"


def group_by_signature(digests: list) -> dict:
    groups: dict = {}
    for d in digests:
        groups.setdefault(d["signature"], []).append(d)
    return groups


def drop_singletons(groups: dict) -> dict:
    # Drop only size-1 families. The candidate threshold N (>=3) is applied later
    # by verify_scan; this bar sits deliberately below N so determinism stays
    # conservative and the LLM/threshold make the real call.
    return {sig_key: members for sig_key, members in groups.items() if len(members) >= 2}
