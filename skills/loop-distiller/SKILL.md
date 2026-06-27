---
name: loop-distiller
description: >-
  Turn a workflow you just performed into a pre-filled loop blueprint. Use when
  the user says "turn what I just did into a loop", "distill my recent work",
  "make a loop out of this session", or otherwise wants to automate a multi-step
  task they already did by hand. Reads the current session transcript, judges
  whether it fills the loop blueprint, drafts the seven answers from evidence
  (never fabricating), and hands off to loop-builder to run the interview and
  scaffold. It never scaffolds loops itself.
---

# Loop Distiller

Turn real session history into a **pre-filled loop-builder blueprint**. This skill
is the evidence front-end; `loop-builder` is the interview and the single
scaffolding authority. Output is always a loop — never a standalone skill.

The backbone knowledge is `references/distillation.md` (rubric + blueprint +
handoff). Load it when you run the flow.

## When this fires

On demand only (Trigger A). The user asks to distill what they just did. There is
no background watching in this phase — a cross-session scanning loop (Trigger C)
is designed in the spec but not built yet.

## Procedure

1. **Read the transcript.** Prefer the current session already in your context.
   For precision or after a `/clear`/compaction, re-read it deterministically:

   ```bash
   python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/loop-distiller/scripts/distiller'); \
   import transcript_reader as tr, json; p = tr.locate(); \
   print(json.dumps(tr.condense(tr.parse(p)), indent=2) if p else 'NO_TRANSCRIPT')"
   ```

   The script's transcript-path scheme is an observed Claude Code convention —
   **verify against current docs**; if it returns `NO_TRANSCRIPT`, fall back to
   the in-context history.

2. **Apply the rubric** from `references/distillation.md`. Count how many of the
   seven blocks have evidence. Lenient gate: 4+ blocks → proceed. Fewer → tell the
   user this session doesn't look like a reusable workflow yet, and stop. (Saying
   no is the point — most sessions are one-offs.)

3. **Draft the blueprint.** Emit loop-builder's fill-in template with each line
   drawn from evidence, an `⟵ ev:` cite, and a confidence marker. Any block
   without evidence is `UNKNOWN → ASK`. **Never fabricate** a value or a `/goal`
   `/loop` `/schedule` flag — flag uncertainty instead.

4. **Hand off to loop-builder.** Present the draft for correction, then invoke the
   `loop-builder` skill with the corrected answers as its interview starting
   point — the corrected answers are passed by inlining them in the conversation,
   not via a file or argument contract. Do not scaffold loop files here.

## What this skill must not do

- Never write a loop, a `SKILL.md`, a `STATE.md`, or any scaffold file — that is
  loop-builder's job.
- Never emit a standalone skill (no Hermes-style skill sprawl — loops only).
- Never invent evidence. `UNKNOWN → ASK` beats a confident guess.

## Collecting feedback and reporting bugs

On an error or when clearly blocked, capture locally (never auto-filed):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback/cli.py" \
  append --category bug --text "<what broke + context>"
```

To review and file, invoke the `loop-builder:feedback-to-issue` skill.
