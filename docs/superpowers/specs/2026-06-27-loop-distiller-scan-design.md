# loop-distiller scanning loop (Trigger C) — design

Phase 2 of `loop-distiller`: a dogfooded, opt-in **scanning loop** that reads the
user's AI-interaction history across all projects, finds workflows that recur,
and surfaces them as loop *candidates* — so a high-quality loop can fall out of
weeks of daily use without the user ever having to notice the pattern themselves.
It only proposes; building a loop is always the user's explicit action via the
Phase 1 on-demand flow (Trigger A).

This builds on the Phase 1 design
(`2026-06-27-loop-distiller-design.md`), which shipped the engine and Trigger A.
Trigger B (per-session hook) was rejected there and stays rejected.

## Problem

Phase 1's Trigger A only fires when the user *asks* ("distill what I just did").
The richest loop candidates are the workflows a user repeats across days and
across repos without noticing they have hardened into a routine. Nothing watches
for that recurrence. Two facts make this hard:

1. **Volume.** Machine-wide history is large and grows daily. Re-reading it every
   scan does not scale, and feeding it wholesale to an LLM is a token bonfire.
2. **Quality at scale.** The signal ("this multi-step workflow recurred") is
   semantic, but the cheap way to find it is structural. Lean too hard on the
   structural side and real recurrences with surface variation are silently
   missed (a false-negative the user never sees).

## Goal

From weeks of normal, multi-project use, the user can run one command
(`/loop-distiller review`) and see a short, ranked list of workflows they
genuinely repeat — each ready to turn into a loop with one more action. Detection
runs locally, incrementally, and never builds anything on its own.

## Decisions (locked during brainstorm)

- **Scope: machine-wide.** Scan every project's transcripts
  (`~/.claude/projects/*/`), because daily work spans repos and cross-repo habits
  are exactly the high-value loop candidates.
- **Ledger is machine-global.** Because the scan spans all projects, the digest
  index and candidate ledger live in `~/.loop-builder/` (alongside
  `feedback-to-issue`'s existing `~/.loop-builder/feedback.jsonl`), not in any one
  project's `loops/` dir.
- **Three-tier memory pipeline** (synthesized from Understand-Anything and
  hermes-agent): digest → cluster → curate. Each transcript is read exactly once;
  scanning is incremental; one-offs never reach the LLM.
- **Determinism is lossless structuring, never the quality gate.** Both reference
  systems keep determinism lossless (Tree-sitter facts; FTS5 index) and let the
  LLM own every semantic judgment. We follow that: the deterministic signature is
  a high-recall *blocking key* used only to make LLM clustering cheap and
  batchable. The LLM makes every keep/discard call.
- **High-recall blocking dial.** The cheap pre-pass drops only size-1 families
  under the *coarse* key, with the drop bar *below* the candidate threshold N — so
  determinism is always conservative; the LLM and the threshold make the real
  call. A recovery pass re-checks cross-batch.
- **Capability-in-plugin, not a generated loop.** The scan is a mode of the
  `loop-distiller` plugin skill (`/loop-distiller` scan + `/loop-distiller
  review`); the *recurring execution* is the user pointing `/schedule` or `/loop`
  at it. `loop-builder` stays the single scaffolding authority.
- **Opt-in, local-only, pull + opt-in nudge.** Nothing runs until the user wires
  the schedule (and optionally a `SessionStart` nudge). All reads/writes stay on
  the machine; the ledger records what was read. Building is always the user's
  action; the blueprint is drafted fresh at review time via Trigger A.

## Architecture — the three-tier memory pipeline

```
RAW transcripts (~/.claude/projects/*/*.jsonl)        read EXACTLY ONCE, ever
        │  Tier 1: DIGEST   (incremental · deterministic · cheap)
        │  list_transcripts machine-wide; fingerprint = path+mtime+size;
        │  for each NEW-since-watermark transcript: kernel parse + condense
        │  → a compact session digest (signature + key commands + project + ts)
        ▼
DIGEST index (~/.loop-builder/digests.jsonl)          the FTS5 analogue (stdlib JSONL)
        │  Tier 2: CLUSTER  (batched · map-reduce · hybrid)
        │  group digests by COARSE high-recall signature (blocking key);
        │  drop only size-1 families (bar < threshold N) — one-offs cost no LLM;
        │  survivors → LLM cluster sub-agents in bounded batches (~20-30, ≤5
        │  concurrent) that semantically merge/name/validate; recovery pass
        │  re-checks cross-batch
        ▼
CANDIDATE ledger (~/.loop-builder/scan-ledger.jsonl)  curated long-term memory
        │  Tier 3: CURATE — upsert candidates; dedup by signature+status vs
        │  surfaced/dismissed/built; update counts; one-offs age out
        ▼
   /loop-distiller review → pick one → Trigger A distiller (fresh) → loop-builder
```

The deterministic tiers reuse the Phase 1 kernel (`parse`, `condense`). The LLM
cluster step is a sub-agent (mirrors the existing skill-bank search-agent
pattern), kept out of the deterministic modules.

### Units (single responsibility, independently testable)

All live under the existing `skills/loop-distiller/`.

| Unit | Responsibility | Form |
| --- | --- | --- |
| `transcript_reader.py` (extend) | `list_transcripts()` across all `~/.claude/projects/*/`; `fingerprint(path)` (path+mtime+size) | deterministic, tested |
| `signature.py` | `signature(condensed) -> str` — coarse high-recall blocking key from `condense()` buckets; family grouping + size-1 drop helpers | deterministic, tested |
| `digest_store.py` | append/read session digests at `~/.loop-builder/digests.jsonl`; watermark = stored fingerprints (skip already-digested) | deterministic, tested (env-overridable) |
| `ledger.py` | upsert/read/mark candidates at `~/.loop-builder/scan-ledger.jsonl`; dedup by signature+status | deterministic, tested (env-overridable) |
| `verify_scan` | separate check: each surfaced candidate clears ≥N recurrences, ≥K blocks, not a dupe of surfaced/dismissed/built | deterministic verifier |
| `references/scanning.md` | tiered pipeline, signature/blocking-key definition, thresholds N/K, batch sizes, cluster sub-agent rubric, recovery pass, consent posture | reference |
| `SKILL.md` (extend) | scan procedure (orchestrate tiers, dispatch batched cluster sub-agents, recovery pass) + `/loop-distiller review` flow + surfacing | skill judgment |
| `SessionStart` nudge hook snippet + install doc | opt-in: read ledger, print one read-only line if candidates wait | opt-in glue |
| evals + tests + CI | scan/review trigger+behaviour evals; unit tests in the runner | tests |

### The loop's seven blocks

```
GOAL (verifiable):  every recurring pattern (≥N occurrences, ≥K blocks) across the digest
                    index is either surfaced as a candidate or dismissed/aged — in the ledger
TRIGGER:            schedule, low-frequency (weekly /schedule or /loop), dynamic interval.
                    OPT-IN. Never per-session.
DISCOVERY:          list_transcripts machine-wide → digest only new-since-watermark (Tier 1)
ACTION:             cluster digests (Tier 2: blocking-key pre-pass → batched LLM cluster
                    sub-agents → recovery pass) → upsert candidates (Tier 3). LOCAL WRITE
                    ONLY, to ~/.loop-builder. Never invokes loop-builder; never writes
                    project files.
VERIFY (separate):  deterministic verify_scan — candidate clears ≥N/≥K and isn't a dupe
STATE:              ~/.loop-builder/digests.jsonl (digest index + watermark) +
                    ~/.loop-builder/scan-ledger.jsonl (candidates). Machine-global.
HUMAN GATES:        BUILDING is the hard gate — C only proposes. Reading history is
                    local-only, never leaves the machine; the ledger records which
                    projects were read.
KNOWLEDGE → skill:  thresholds N/K, signature/blocking-key definition, batch sizes,
                    dedup rules, cluster rubric → references (durable)
BUDGET / stop:      incremental (new transcripts only); singletons dropped pre-LLM; batches
                    bounded (≤5 concurrent, ~20-30/batch); per-scan token cap
```

## Data shapes

**Digest** (one per transcript, append-only in `digests.jsonl`):

```
{ "fingerprint": "<path|mtime|size>", "project": "<encoded project dir>",
  "path": "<transcript path>", "ts": <int>, "signature": "<coarse blocking key>",
  "blocks": ["discovery","action","verify",...], "commands": ["gh issue list", "pytest", ...],
  "schema": 1 }
```

**Candidate** (one per recurring pattern, in `scan-ledger.jsonl`):

```
{ "id": "<hex>", "signature": "<coarse blocking key>", "label": "<LLM short name>",
  "count": <int>, "projects": ["...", ...], "first_seen": <int>, "last_seen": <int>,
  "evidence": ["<fingerprint>", ...], "status": "new|surfaced|dismissed|built",
  "schema": 1 }
```

The candidate stores only pointers (`evidence` fingerprints) — never a stored
blueprint. The blueprint is drafted fresh at review time by re-reading the cited
transcripts through Trigger A's distiller (cheaper and fresher than storing).

Status flow: `new → surfaced → dismissed | built`. Dedup keys on `signature +
status` so dismissed/built patterns never resurface.

## Consent & privacy posture (mirrors feedback-to-issue's "act only on explicit yes")

- **Opt-in install, two switches, both off by default:** (1) the scheduled scan
  trigger (`/schedule` weekly or `/loop` pointed at "run the loop-distiller
  scan"); (2) optionally the `SessionStart` nudge hook.
- **Local-only & auditable:** all reads (`~/.claude/projects/*/`) and writes
  (`~/.loop-builder/`) stay on the machine; the ledger records which projects were
  read; nothing leaves the machine.
- **Surfacing: pull default + opt-in nudge.** `/loop-distiller review` lists
  candidates on demand. The opt-in `SessionStart` hook prints one read-only line
  ("N loop candidates waiting — /loop-distiller review") and can be turned off.
- **Build is always the user's action.** Surfacing ≠ building. The user picks a
  candidate in review; that runs the Trigger A handoff into `loop-builder`.

## Implementation phasing

Mirror Phase 1's "deterministic substrate first" discipline. Two PRs under this
one spec:

- **2a — deterministic memory substrate (heavily unit-tested, no LLM):**
  `list_transcripts` + `fingerprint`, `signature` (the high-recall blocking key),
  `digest_store`, `ledger`, `verify_scan`. Fixtures = synthetic digests with known
  recurrences → assert family grouping, that the size-1 drop bar sits below N,
  ledger dedup by signature+status, and verifier thresholds. A working
  scan-and-ledger with a stubbed/manual cluster step is shippable on its own.
- **2b — judgment + UX layer (eval-tested):** the `SKILL.md` scan procedure
  (orchestrate the tiers, dispatch batched cluster sub-agents, recovery pass),
  `references/scanning.md` (cluster rubric, thresholds, batch sizes, consent), the
  `/loop-distiller review` flow, the opt-in `SessionStart` nudge hook + install
  doc, and scan/review evals.

## Testing

- **Deterministic modules:** red-green unit tests under
  `skills/loop-distiller/scripts/tests/`, wired into the existing
  `test_loop_distiller.sh` runner and CI. Env-overridable paths
  (`LOOP_DISTILLER_*`) so tests never touch the real `~/.loop-builder` or
  `~/.claude`. Fixtures: synthetic transcripts/digests encoding known recurrences
  and known one-offs.
- **Signature/blocking key:** assert surface-variant sessions of one workflow land
  in the same family (high recall), and that genuinely distinct workflows do not
  collapse so far that the LLM can't re-split them.
- **LLM clustering:** eval-tested (trigger + behaviour) plus the sub-agent rubric
  in the reference; not unit-tested.
- **End-to-end (2b):** a fixture transcript set → digest → cluster → ledger →
  review, asserting one-offs are dropped, recurrences surface, and
  dismissed/built never resurface.

## Scope

- **In scope:** the machine-wide scanning loop — Tier 1 digest, Tier 2 hybrid
  cluster, Tier 3 curate, the verifier, the `/loop-distiller review` flow, the
  opt-in nudge, consent posture, and the two implementation phases (2a/2b).
- **Out of scope:** changing Trigger A or the Phase 1 kernel beyond the additive
  `list_transcripts`/`fingerprint` extension; any non-local transcript handling;
  auto-building loops; cross-machine sync of the ledger.

## Open questions (resolve at implementation)

- Concrete defaults for thresholds **N** (recurrences, e.g. 3) and **K** (block
  coverage, e.g. 4), and whether they are configurable via env/`references`.
- The exact coarse signature/blocking-key formula over `condense()` buckets
  (which fields, how normalized) — tuned for high recall during 2a.
- Whether the ledger render in `/loop-distiller review` is plain text or a small
  table, and how candidates are ranked (by count, by recency, or a blend).
- The transcript JSONL location/schema and the `~/.claude/projects/*/` layout are
  observed Claude Code conventions — verify against current docs at implementation
  time, per house discipline.
