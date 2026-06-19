---
name: loop-builder
description: >-
  Design and scaffold an agent "loop" — an unattended, scheduled, self-verifying
  agent workflow. Use this whenever the user wants to automate a recurring task,
  schedule an agent, run an agent unattended or overnight, set up monitoring,
  triage, or alerting, poll something on a cadence, or turn a manual repeated
  workflow into a self-running one — even if they never say the word "loop." If a
  request implies "do this every day / on a schedule / until some condition holds,
  without me typing each time," reach for this skill. It walks the seven-question
  blueprint, picks the simplest loop pattern, and scaffolds the six building blocks
  (schedule, isolation, skill, connectors, verifier, state) with a human-gate list
  and a budget.
---

# Loop Builder

Guide the user through designing and scaffolding a **loop**: a small self-running
system in which an agent finds work, acts, gets graded by a *separate* checker,
and repeats until a verifiable condition holds or a budget runs out — without a
human typing each turn.

The backbone knowledge for everything here is
`references/loops-and-loop-engineering.md`. It is the source of truth; do not
contradict it. If a product mechanic (`/loop`, `/schedule`, dynamic intervals) is
uncertain, say so and tell the user to verify against current Claude Code / Codex
docs — that uncertainty flag is real and must survive into what you generate.

## The one rule that runs through everything

**Durable knowledge → a skill. Changing state → memory.**

- Conventions, commands, "how we decide done," rubrics → the loop's **own**
  `SKILL.md` (read-only each run).
- What's been tried, what passed, what's still open → an external **state file**
  (read *and written* each run).

Putting mutable state inside a `SKILL.md` is the classic anti-pattern — skills are
version-controlled and effectively read-only per run. Enforce this split in
everything you generate. If you catch yourself writing progress into a skill, stop
and move it to the state file.

## Why loops need this at all

The agent **starts cold every run** — it forgets everything between runs. So
conventions, commands, and "what's already done" must live outside the context
window, on disk. The agent forgets; the repo does not. Every building block below
exists to serve that one fact.

## Process

Work in three phases, in order: **elicit → select → scaffold.** Do not jump to
scaffolding before the seven answers exist — a loop with a missing block is the
failure mode, not a shortcut.

Create a TodoWrite item per phase so nothing is skipped.

---

## Phase 1 — Elicit the seven decisions

Ask these **one at a time, in order.** Each maps to a building block. Capture the
answer before moving on. Don't accept vibes where a predicate is required.

1. **Goal (recursive).** "What verifiable condition means *done for now*?" Push for
   a checkable predicate, not a vibe.
   - Bad: "keep the repo healthy." Good: "every P1 issue has an owner and a plan
     comment." If the answer is a vibe, ask "how would a script know it's true?"
2. **Trigger.** "What fires it — a schedule (cron / `/schedule` / `/loop`), an
   event (new PR, inbound email), or run-until-done?"
3. **Discovery.** "How does the agent *find* work each cycle?" (query the tracker,
   scan the inbox, diff CI) → a connector.
4. **Action.** "What is it allowed to *do*, through which tools?" → connectors; note
   whether file work needs an isolated worktree.
5. **Verification.** "Who checks the result, and against what? It must be a
   *separate* checker — a program where one exists." → sub-agent or script.
6. **State / memory.** "Where does *what's done / what's open* persist outside the
   context — a markdown ledger, Linear, GitHub issues?"
7. **Human gates.** "Which actions are irreversible or high-blast-radius and need a
   human approval first — merging, sending external email, spending, deleting?"
   This is non-negotiable (see Limitations).

Then capture two more that aren't optional:

- **Knowledge → skill.** "What conventions should the loop *not* re-derive every
  run?" (build/test commands, review standards, "we don't do it that way").
- **Budget / stop.** "What caps a run — max iterations, a token cap, wall-clock?"

If the user is fuzzy on the goal, slow down — every other decision hangs off a
crisp, checkable goal.

---

## Phase 2 — Select the simplest fitting pattern

Recommend **one** pattern, then load **only** its reference file (progressive
disclosure — don't read all four). Default to ReAct + deterministic verifier and
justify any escalation.

| If… | Pattern | Load |
|---|---|---|
| One workstream; "done" is a program-checkable predicate | **ReAct + deterministic verifier** *(default)* | `references/pattern-react-deterministic-verifier.md` |
| Clear criteria that need *judgement*, not just a script | **Evaluator–optimizer** | `references/pattern-evaluator-optimizer.md` |
| Work genuinely parallelizes into independent subtasks | **Orchestrator–workers** | `references/pattern-orchestrator-workers.md` |
| You want a crude baseline / teaching loop | **Ralph** | `references/pattern-ralph.md` |

Guidance to repeat to the user: **prefer the simplest pattern that works, and
compose blocks rather than reaching for a heavy framework you can't debug.** A
single loop with a deterministic verifier beats an elaborate multi-agent system you
can't reason about. Escalate to orchestrator–workers only when the work *genuinely*
parallelizes.

---

## Phase 3 — Emit the template, then scaffold

### 3a. Emit the populated fill-in template

Show the user this template filled with their answers (the literal shape from the
reference). This is the contract before any files are written:

```
GOAL (verifiable):      ____
TRIGGER:                schedule | event | run-until-done → ____
DISCOVERY (find work):  ____   (connector: ____)
ACTION (do work):       ____   (tools: ____ ; isolation: worktree? y/n)
VERIFY (separate check): ____  (deterministic? y/n)
STATE (persist outside): ____  (file | board | issues)
HUMAN GATES:            ____   (irreversible actions list)
KNOWLEDGE → skill:      ____   (conventions the loop should not re-derive)
BUDGET / stop:          ____   (max iterations | token cap | wall-clock)
```

### 3b. Scaffold the six building blocks

Ask the user where the loop should live (default: a new folder in the current
project, e.g. `<project>/loops/<loop-name>/`). Then generate these artifacts.
Every loop gets **all six**; a missing block is what breaks (see the table).

| # | Block | What you write | Durable or changing |
|---|---|---|---|
| 1 | **Scheduling** | A trigger stub (cron line / `/schedule` / `/loop` / run-until-verifier) | durable |
| 2 | **Isolation** | A note/command for git worktrees *if* file work runs in parallel | durable |
| 3 | **Skill** | The loop's **own** `SKILL.md` — conventions only | **durable** |
| 4 | **Connectors** | Named MCP/tools for discovery + action | durable |
| 5 | **Verifier** | A **separate** check — start from `scripts/verifier_template.sh` | durable |
| 6 | **State** | `STATE.md` ledger (or board) — what's done / open | **changing** |

Concretely, write into the loop folder:

- **`SKILL.md`** — the loop's own skill: its goal, conventions, the pattern it uses,
  how to run it, and what "done" means. **Conventions only — never progress.**
- **`STATE.md`** — a ledger the loop reads and writes each run: a table of items
  with status, plus "last run" notes. This is the changing half; keep it out of the
  skill.
- **A verifier script** — copy `scripts/verifier_template.sh` and wire it to the
  user's predicate. If it's a "no P1 unassigned"-style check, adapt
  `scripts/verify_no_p1_unassigned.sh`. The verifier must be *separate* from the
  generator and deterministic where possible.
- **A trigger stub** — the schedule/event entry. Use Claude Code mechanics
  concretely (`/schedule "<cron>" …`, `/loop`, worktrees) but **annotate that these
  mechanics may have changed — verify against current docs.** Never fabricate flags.
- **`HUMAN-GATES.md`** — the irreversible-actions list **and** the budget/stop
  condition, together. This file is mandatory; see below.

### 3c. Always emit human gates + a budget

A loop with no budget and no gates is the failure mode, not the goal. `HUMAN-GATES.md`
must contain:

- **Human gates:** every irreversible / high-blast-radius action that requires
  human approval before execution — merging, sending external email/messages,
  spending money, deleting, publishing. The loop must never cross these
  autonomously. If the user named none, challenge it: most loops touch at least one.
- **Budget / stop condition:** max iterations, token cap, or wall-clock — whichever
  the user chose. Prefer dynamic intervals (short waits while a build finishes, long
  waits when nothing's pending) where the scheduler supports it.

Refuse to call the loop "done" if either is missing.

## Worked example — morning GitHub triage

A complete fill-in, to show the shape of a good answer:

```
GOAL (verifiable):      zero P1 issues without an assignee AND a plan comment
TRIGGER:                schedule → every weekday 08:00 (cron "0 8 * * 1-5")
DISCOVERY (find work):  list open P1 issues   (connector: GitHub MCP / gh)
ACTION (do work):       assign an owner, post an initial plan comment (tools: gh)
VERIFY (separate check): re-query, assert no P1 lacks assignee  (deterministic? y →
                         scripts/verify_no_p1_unassigned.sh)
STATE (persist outside): loops/triage/STATE.md — issues triaged this week
HUMAN GATES:            none auto-closes; escalate (don't close) anything ambiguous
KNOWLEDGE → skill:      label taxonomy, what a "plan comment" must contain
BUDGET / stop:          max 25 issues/run; stop when verifier passes or cap hit
```

Pattern: ReAct + deterministic verifier (one workstream, program-checkable goal).
Comments and labels are reversible, so no hard human gate is required — but the
*budget* and the *escalate-don't-close* rule still ship.

## Output discipline checklist

Before declaring the loop scaffolded, confirm:

- [ ] All seven decisions answered; goal is a checkable predicate.
- [ ] One pattern chosen; only its reference was loaded.
- [ ] Populated template shown to the user.
- [ ] Six blocks scaffolded as files in the loop folder.
- [ ] A **separate** verifier exists (script or sub-agent), deterministic if possible.
- [ ] An **external state file** exists — and no mutable state lives in any SKILL.md.
- [ ] `HUMAN-GATES.md` lists irreversible actions **and** a budget/stop condition.
- [ ] Any `/loop` `/schedule` mechanic is flagged "verify against current docs."

## Limitations to bake in (not disclaimers)

State these to the user as the operating posture:

- **Prompt injection is unsolved.** A loop that reads issues, emails, or web content
  ingests untrusted text every cycle. The durable control is a permanent **human
  gate on irreversible actions** — never let the loop merge/send/spend/delete
  autonomously.
- **Verification is the hard part.** Autonomy is only as trustworthy as the checker.
  Favor deterministic verifiers; keep checker separate from maker; distrust a
  passing self-grade.
- **Token economics swing wildly.** Cadence, fan-out, and retries dominate cost. Set
  explicit budgets and dynamic intervals.
- **Most of "agentic" is plumbing.** The discipline is in the guardrails around the
  decision, not in the decision being magic.
