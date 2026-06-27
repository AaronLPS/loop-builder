# Distillation — rubric, blueprint, handoff

The engine answers one question: **does this session fill the loop-builder
blueprint?** Detection and the blueprint are the same rubric.

## Seven-block detection rubric

| Block | Transcript signal | Evidence source |
| --- | --- | --- |
| Goal (verifiable) | a repeated "done" state — tests pass, "that works", a check that flipped green | `verify` bucket + user text |
| Trigger | a recurring stimulus — similar session openings; (Phase 2) a time/frequency pattern | first user turn |
| Discovery | read-only fan-out to find work | `discovery` bucket |
| Action | mutating calls | `action` bucket |
| Verification | a check step (test/build/re-query/review) | `verify` bucket |
| State | progress tracked (TODOs, notes, issue/PR updates) | `action`/`vcs` + text |
| Human gates | irreversible acts (commit, push, send, merge, deploy) | `vcs` bucket |

**Gating.** Trigger A is *lenient* — the user asked, so 4+ blocks with evidence is
enough to pre-fill; the interview corrects the rest. (Strict, recurrence-based
gating is Phase 2 / Trigger C and is out of scope here.)

## Pre-filled blueprint (the literal loop-builder template)

Emit loop-builder's fill-in template with each line drafted from evidence, an
`⟵ ev:` cite (transcript line indices `i` and/or bucket), and a confidence marker.
Blocks with no evidence are `UNKNOWN → ASK` — never guessed.

```
GOAL (verifiable):   <drafted>            ⟵ ev: <i,…> · conf: high|med|low
TRIGGER:             <drafted or UNKNOWN> ⟵ ev: … · conf: …
DISCOVERY:           <drafted>            ⟵ ev: discovery[i] · conf: …
ACTION:              <drafted>            ⟵ ev: action[i] · conf: …
VERIFY:              <drafted or UNKNOWN> ⟵ ev: verify[i] · conf: …
REUSE (installed):   UNKNOWN — ASK        (loop-builder surveys installed skills/MCP)
REUSE (skill-bank):  UNKNOWN — ASK        (loop-builder runs the skill-bank search)
STATE:               UNKNOWN — ASK
HUMAN GATES:         <from vcs bucket, or UNKNOWN — ASK>
KNOWLEDGE → skill:   UNKNOWN — ASK
BUDGET / stop:       UNKNOWN — ASK
```

**Never fabricate.** No evidence → `UNKNOWN → ASK`. Any `/goal` `/loop`
`/schedule` mechanic, and the transcript-path scheme itself, are annotated
"verify against current Claude Code docs."

## Handoff to loop-builder

1. Present the pre-filled blueprint to the user for correction.
2. Invoke the `loop-builder` skill, passing the corrected answers as the starting
   point for its seven-question interview. loop-builder remains the single
   scaffolding authority — this skill never writes loop files itself.
3. The interview asks exactly the `UNKNOWN → ASK` blocks (and lets the user revise
   any drafted line), then scaffolds as normal.
