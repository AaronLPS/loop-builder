# loop-builder skill — design spec

*Date: 2026-06-19. Source of truth: `reference/loops-and-loop-engineering.md` (treated as authoritative; not re-derived).*

## Purpose

A Claude Code skill that guides a user through designing and scaffolding an agent
**loop** — an unattended, scheduled, self-verifying agent workflow — for whatever
purpose they describe. It is the operational front-end to the knowledge layer in
`loops-and-loop-engineering.md`.

## Audience

A Claude Code power user who wants to stand up a recurring, self-running agent
workflow without hand-deriving the architecture each time. They may never say the
word "loop."

## Decisions (locked)

- **Install location:** repo `.claude/skills/loop-builder/`.
- **Output mode:** scaffold real files into the user's target project (not just a
  template in chat).
- **Tool targeting:** Claude Code concrete defaults (`/schedule`, `/loop`,
  worktrees, sub-agents) **with the doc's uncertainty flag preserved** — generated
  trigger stubs tell the user to verify mechanics against current docs.

## Folder layout

```
loop-builder/
  SKILL.md                                   # <500 lines: elicit -> select -> scaffold
  references/
    loops-and-loop-engineering.md            # backbone, verbatim copy = source of truth
    pattern-evaluator-optimizer.md
    pattern-orchestrator-workers.md
    pattern-react-deterministic-verifier.md
    pattern-ralph.md
  scripts/
    verifier_template.sh                      # generic predicate runner, exits non-zero on fail
    verify_no_p1_unassigned.sh                # the doc's worked example
```

## Trigger description (pushy)

> Use whenever the user wants to automate a recurring task, schedule an agent,
> build a loop, set up monitoring or triage, run an agent unattended overnight, or
> turn a manual workflow into a self-running one — even if they never say the word
> "loop." Walks through designing and scaffolding an unattended, scheduled,
> self-verifying agent workflow.

## SKILL.md body contract (rigid)

1. **Elicit** the seven questions in order, one at a time: goal → trigger →
   discovery → action → verify → state → human gates. The goal must be a checkable
   predicate; push back on vibes ("keep the repo healthy").
2. **Select** the simplest fitting pattern and load **only** that reference
   (progressive disclosure). Default: ReAct + deterministic verifier. Escalate to
   orchestrator–workers only when work genuinely parallelizes.
3. **Emit** the doc's fill-in template, populated with the user's answers.
4. **Scaffold** six artifacts into the target project:
   - the loop's **own** `SKILL.md` → conventions only (durable)
   - `STATE.md` (or a board) → progress ledger (changing)
   - a verifier script (adapted from `scripts/`)
   - a schedule/trigger stub (flagged: verify against current docs)
   - a worktree note if parallel
   - `HUMAN-GATES.md` listing irreversible actions + the budget/stop condition
5. **Enforce** durable-vs-changing: never write mutable state into a SKILL.md;
   never ship a loop without a human-gate list and a budget/stop condition.

## Invariants / acceptance criteria

- "Help me automate triaging my GitHub issues every morning" triggers the skill
  and walks through the seven questions.
- Every generated loop includes a separate verifier, an external state file, and a
  human-gate list.
- No fabricated product facts; source grading and the `/loop` uncertainty flag are
  preserved in the backbone reference and in generated stubs.

## Test prompts

Positive (should fire; none say "loop"):
1. "Help me automate triaging my GitHub issues every morning"
2. "I want an agent to watch my CI and open a fix PR when the nightly build breaks"
3. "Can you set something up to review my inbox each morning and draft replies?"

Negative (should NOT fire):
- "Fix this bug in my parser"
- "Write a one-off script to rename these files"

## TDD for scripts

Red-green on both bundled scripts: write a failing predicate case, watch it fail
(non-zero exit), then make it pass. `verify_no_p1_unassigned.sh` operates on a JSON
fixture of issues so it is testable offline.
