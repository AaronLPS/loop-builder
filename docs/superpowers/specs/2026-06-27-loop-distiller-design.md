# loop-distiller — design

A new peer skill that turns real AI-interaction history into a *pre-filled
loop-builder blueprint*. Inspired by hermes-agent's "autonomous skill creation
after complex tasks," but adapted to Claude Code's runtime and this plugin's
consent ethos: it watches what you actually do, recognizes a workflow worth
automating, and hands `loop-builder` a blueprint with the seven answers already
drafted from evidence — so a high-quality, comprehensive loop falls out of daily
use instead of a cold interview.

## Problem

`loop-builder` only fires when the user already knows they want a loop and starts
the interview cold. But the best loop candidates are buried in everyday work: a
multi-step thing you did, then did again, then again — never noticing it had
hardened into a routine worth automating. There is no path from "I keep doing
this by hand" to "here is a drafted loop for it."

Hermes solves the analogous problem by autonomously crystallizing completed tasks
into skills. Two constraints make a direct copy wrong here:

1. **Runtime.** Hermes is its own agent runtime with an always-on process and an
   FTS5 session index. Claude Code has no always-on process the plugin controls;
   "watching" must come from a concrete mechanism — an on-demand command, a hook,
   or a dogfooded scheduled loop.
2. **Ethos.** This repo is consent-first (feedback-to-issue's mandatory consent
   gate; the privacy push gate). Hermes' "automatic by default, emit many skills"
   would mean transcript-reading without asking and uncurated skill sprawl — both
   against the grain here.

## Goal

From normal use, a user can turn a workflow they actually performed into a
drafted loop with one action — the engine pre-fills the loop-builder blueprint
from transcript evidence, never fabricates, and routes the result through the
unchanged `loop-builder` interview. Detection runs locally and surfaces nothing
the user did not ask to see (Trigger A) or did not opt into (Trigger C).

## Decisions (locked during brainstorm)

- **Output: loops only.** The engine is a smart front-end for `loop-builder`; it
  never emits standalone skills. This is a deliberate rejection of Hermes-style
  skill sprawl — the bar is one well-formed, self-verifying loop per *real*
  pattern, not twenty uncurated `SKILL.md`s.
- **One engine, pluggable triggers.** A shared engine (detector + distiller) sits
  behind interchangeable triggers. The hard part (detection quality) is built
  once, behind the cheapest trigger first; later triggers are purely additive.
- **Trigger A (on-demand) ships first.** Build it now. Fully consent-first, zero
  idle cost, no new infrastructure.
- **Trigger C (scanning loop) is the additive phase.** A dogfooded scheduled loop
  that reads across sessions — the only view that survives heavy `/clear`-based
  context management and that sees cross-session repetition.
- **Trigger B (per-session hook) is rejected.** A `Stop`/`SessionEnd` hook assumes
  one session ≈ one workflow. The target user `/clear`s frequently mid-task, so a
  hook would fire on incomplete fragments, add latency to a high-frequency action,
  and never see the whole workflow. C subsumes B's "watch without being asked"
  job, done correctly across sessions.
- **Housing: a new standalone skill** `skills/loop-distiller/`. "Distill my recent
  work into a loop" is a genuine standalone trigger (per AGENTS.md's graduation
  rule), and both A and C must call the same engine.
- **`loop-builder` stays the single scaffolding authority.** The distiller hands
  over a blueprint and invokes `loop-builder` unchanged; all of its human-gate,
  budget, and verifier discipline still runs.
- **Detector rubric = the seven loop blocks.** Detection is not a separate
  heuristic to invent — it is "does this history fill the blueprint?" The detector
  and the blueprint share one rubric.
- **Never fabricate.** Blocks without evidence are marked `UNKNOWN → ASK`, not
  guessed — the same posture as "never fabricate flags." The interview then asks
  exactly those blanks.

## Architecture

```
  ┌────────── triggers (pluggable) ──────────┐
  │  A. on-demand   "distill my recent work" │   phase 1 (now)
  │  C. scanning loop (dogfooded, scheduled) │   phase 2 (additive)
  └────────────────────┬─────────────────────┘
                       ▼
        ┌──────────  loop-distiller  ──────────┐
        │  ① DETECTOR  is this loop-worthy?     │
        │     rubric = the seven loop blocks    │
        │  ② DISTILLER transcript → 7 pre-filled│
        │     blueprint answers + evidence cites│
        └────────────────────┬──────────────────┘
                       ▼  (hands off the pre-filled blueprint)
                  loop-builder → interview (user corrects) → scaffold
```

### Units (single responsibility)

| Unit | Responsibility | Form |
| --- | --- | --- |
| detector | score a transcript (or cluster) against the seven-block rubric; decide loop-worthy or not | skill judgment, evidence-cited |
| distiller | map transcript evidence → the literal loop-builder fill-in template, with citations + confidence, `UNKNOWN → ASK` where evidence is thin | skill judgment |
| handoff | invoke `loop-builder` with the pre-filled blueprint | skill |
| C: scanner loop | scheduled cross-session scan → cluster → ledger of candidates | a loop (dogfooded), local-only |
| C: ledger/review | `loops/loop-distiller-scan/STATE.md` + `/loop-distiller review` to pull candidates | state file + skill command |

### The detector (the "say no to 95%" filter)

Detection asks whether the history contains raw material for the seven blocks.
Each block has concrete transcript signals:

| Block | Signal in a transcript |
| --- | --- |
| Goal (verifiable) | a repeated "done" state — tests pass, "that works", a check that flipped green |
| Trigger | a recurring stimulus — similar session openings; (C only) a time/frequency pattern |
| Discovery | read-only fan-out early: `grep`/`find`/`gh list`/file reads to *find* the work |
| Action | mutating calls: `Edit`/`Write`/`Bash`/MCP writes |
| Verification | a check step: test run, build, re-query, review |
| State | progress tracked: TODOs, notes, issue/PR updates |
| Human gates | irreversible acts: commit, push, send, merge, deploy |

Loop-worthiness = how many blocks have evidence (and, for C, how many times the
pattern recurred). **A is lenient** — the user asked, so 4+ blocks present is
enough to pre-fill and let the interview correct. **C is strict** — recurrence
must clear a threshold *and* block coverage, or it stays silent. Strict
gatekeeping is C's job; A does not gatekeep.

### The distiller & handoff

The distiller emits the literal loop-builder fill-in template, each line
pre-filled from evidence with an `⟵ ev:` citation and a confidence marker;
unsupported blocks become explicit `UNKNOWN → ASK`. Example:

```
GOAL (verifiable):   "all P1 issues have an owner + plan comment"   ⟵ ev: msgs 4,17,31 · conf: high
TRIGGER:             schedule? (you did this ~daily at ~9am)        ⟵ ev: 3 sessions · conf: med
DISCOVERY:           `gh issue list --label P1`                     ⟵ ev: tool-call L22 · conf: high
ACTION:              assign + comment via gh                        ⟵ ev: tool-calls · conf: high
VERIFY:              re-query P1s unassigned                        ⟵ ev: msg 40 · conf: med
STATE:               UNKNOWN — no ledger seen                       ⟵ ASK in interview
HUMAN GATES:         UNKNOWN — you never closed/merged here         ⟵ ASK in interview
BUDGET / stop:       UNKNOWN                                        ⟵ ASK in interview
```

The user corrects evidence-backed drafts and answers only genuinely-open blocks,
instead of seven cold questions. The handoff then invokes `loop-builder`
unchanged.

## Trigger A — on-demand (phase 1, ships now)

- Invoked by intent ("turn what I just did into a loop", "distill my recent
  work") or an explicit `/loop-distiller`.
- Reads the **current session transcript** (in-context, or re-read from the
  session JSONL under `~/.claude/projects/<encoded-path>/`).
- Runs detector → distiller → presents the pre-filled blueprint → invokes
  `loop-builder`.
- Lenient gating (the user asked). Zero idle cost, no background process, no
  hooks. Fully consent-first.

## Trigger C — scanning loop (phase 2, additive, dogfooded)

C is itself a loop, specified with loop-builder's own seven blocks — the flagship
dogfood example:

```
GOAL (verifiable):  every recurring pattern (≥N occurrences in the scan window) is
                    either surfaced as a candidate or dismissed — recorded in the ledger
TRIGGER:            schedule → low-frequency (e.g. weekly), dynamic interval. NOT per-session.
DISCOVERY:          scan transcript JSONL since last watermark; dispatch a cluster
                    sub-agent (mirrors the existing skill-bank search-agent pattern)
ACTION:             cluster recurring multi-step patterns → run distiller → write a
                    candidate row to the ledger.  LOCAL WRITE ONLY.
VERIFY (separate):  a separate check that each candidate clears threshold (≥N recurrences,
                    ≥K blocks) and is not a dupe of an already-surfaced/dismissed one
STATE:              loops/loop-distiller-scan/STATE.md — candidates, counts, status, watermark
HUMAN GATES:        BUILDING is the hard gate. C only proposes; it NEVER invokes
                    loop-builder or writes project files on its own. Reading history
                    is local-only and never leaves the machine.
BUDGET / stop:      cap transcripts/run; scan deltas since watermark only; token cap
```

### Consent & privacy posture (mirrors feedback-to-issue's "capture locally, act only on explicit yes")

- **Opt-in install.** C is not on by default; the user deliberately sets up the
  scanning loop.
- **Local-only.** Transcripts are read in the user's own session and never sent
  anywhere external.
- **Surfacing: pull + opt-in SessionStart nudge.** Default is pull — C maintains
  the ledger; the user reviews with `/loop-distiller review` when they choose.
  An optional toggle adds one quiet line at session start ("2 loop candidates
  waiting — /loop-distiller review"); a tap, not a workflow interruption, and it
  can be turned off. (Directly honors the rejection of intrusive per-session
  hooks.)
- **Build is always the user's action.** Surfacing ≠ building. The user picks a
  candidate, which runs the A-style handoff into `loop-builder`.

## Scope

- **In scope now (phase 1):** the `loop-distiller` skill — detector, distiller,
  handoff, and Trigger A end to end.
- **In scope as design (phase 2):** Trigger C — the scanning loop, ledger,
  `/loop-distiller review`, opt-in nudge, and consent posture. Specified here so
  phase 1 is built engine-first for both, but implemented in a later branch.
- **Out of scope:** emitting standalone skills; auto-building loops without the
  user; any non-local transcript handling; changes to `loop-builder`'s interview
  or scaffold beyond accepting a pre-filled blueprint.

## Open questions (resolve at implementation)

- Exact transcript JSONL location and schema must be verified against current
  Claude Code (annotate as "verify against current docs", per house discipline).
- Concrete thresholds N (recurrences) and K (block coverage) for C's strict gate.
- Whether the pre-filled blueprint is passed to `loop-builder` as a file, an
  argument, or inlined into the invoking prompt.
