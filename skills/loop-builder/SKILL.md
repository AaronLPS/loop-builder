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
contradict it. If a product mechanic (`/goal`, `/loop`, `/schedule`, dynamic intervals) is
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

Create a TodoWrite item per phase so nothing is skipped — and a **distinct** item for
the Phase 1.5 skill-bank search (dispatch the searcher over `references/skill-bank/`),
the step most easily missed because installed capabilities are already in view and the
bank is not.

---

## Phase 1 — Elicit the seven decisions

Ask these **one at a time, in order.** Each maps to a building block. Capture the
answer before moving on. Don't accept vibes where a predicate is required.

1. **Goal (recursive).** "What verifiable condition means *done for now*?" Push for
   a checkable predicate, not a vibe.
   - Bad: "keep the repo healthy." Good: "every P1 issue has an owner and a plan
     comment." If the answer is a vibe, ask "how would a script know it's true?"
2. **Trigger.** "What fires it — a schedule (cron / `/schedule` / `/loop`), an
   event (new PR, inbound email), or run-until-done (`/goal <verifiable condition>`,
   often paired with `/loop` for a self-terminating loop on a schedule)?"
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

## Phase 1.5 — Survey reusable capabilities (don't rebuild what exists)

Before choosing a pattern, survey what already exists that can *serve a block* instead
of being built from scratch — the "compose blocks; don't reach for a framework you
can't debug" principle applied to the build itself. **Search both sources below every
time, in order, and map both to the loop's blocks.** Neither is optional.

**1.5a — Installed.** Use `find-skills` (or scan the available skills / MCP list) for
capabilities already on the machine (ready to use immediately).

**1.5b — skill-bank — do not skip, even if 1.5a already seems to cover a block.**
**Search the bank** for capabilities matching the blocks this loop needs. The bank is
large, so don't read it inline — dispatch a search sub-agent:

Dispatch a general-purpose sub-agent using the prompt in
`references/skill-bank/search-agent.md`, passing the loop's block needs (e.g. "verifier
for X; connector for Y"). It reads the whole bank — `references/skill-bank/recommended.md`
(curated standouts) and `references/skill-bank/catalog/*.md` (the comprehensive
listings) — in its own context, judges relevance semantically, and returns a short
shortlist per need: the best-fit entries (name, source, block, one-line why, and whether
it's a recommended standout), or "none applicable — <reason>". It prefers standouts when
they fit and only reaches into the catalogs when they don't.

*Fallback (if sub-agents aren't available):* read `references/skill-bank/recommended.md`
directly, and scan a specific `catalog/<source>.md` for any block the standouts don't
cover — same discipline.

Borrow from the shortlist: recommend-and-record only (surface source + install pointer +
a named fallback; never inline external code), confirming license and mechanics against
source at borrow time. The point is to surface proven prior art before you settle, so
you compose instead of rebuild.

Map what you find — from **both** the installed set (1.5a) and the skill-bank search
results (1.5b) — to the blocks the loop needs; recommend only what **genuinely changes
the design**, not an exhaustive inventory:

- **Verifier (⑤)** — is there an installed skill or program that can *be* the
  deterministic check or the evaluator? (e.g. `codex` can act as an independent,
  *different-model* evaluator — a stronger maker/checker split than a same-model
  sub-agent.)
- **Connector (④)** — an MCP/skill that already reads the tracker, the docs, the DB,
  the inbox? (e.g. `context7` for official library docs; a GitHub MCP for issues.)
- **Sub-agents (⑤) / workers** — an existing research or worker agent the loop can
  dispatch rather than hand-rolling one.
- **Runtime** — is a managed agent runtime available (e.g. **Claude Managed Agents**)
  that provides scheduling, a grader/verifier, memory, and approval gates *natively*?
  If so, consider scaffolding for it instead of hand-rolling those blocks — see
  `references/deploy-claude-managed-agents.md`. It's beta and fast-moving, so verify
  against current docs and keep a Claude Code fallback.

Two rules when you recommend reuse, because an external skill is *changing* state you
don't control:

1. **Name a fallback** for anything you wire in ("use `codex`; if unavailable, a
   general-purpose sub-agent"), so a cold start still works if the skill is missing
   or has changed.
2. **Don't bind to unverified mechanics** — note the skill's name and that its
   behavior should be confirmed, rather than assuming flags or outputs.

Surface the shortlist to the user and let them choose what to wire in. Record the
choices in the `REUSE:` line of the template below.

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
REUSE (installed):      ____  (skill/MCP → block it serves ; fallback: ____)
REUSE (skill-bank):     ____  (bank result → block ; install + fallback ; or "none applicable — why")
STATE (persist outside): ____  (file | board | issues)
HUMAN GATES:            ____   (irreversible actions list)
KNOWLEDGE → skill:      ____   (conventions the loop should not re-derive)
BUDGET / stop:          ____   (max iterations | token cap | wall-clock)
```

### 3b. Scaffold the six building blocks

Split the artifacts by durability so the loop is **invocable by name**, then
confirm the locations with the user (these are the defaults):

- **Durable → an installed skill.** Put the loop's own `SKILL.md` (plus its verifier
  and any templates) under `.claude/skills/<loop-name>/`. This matters mechanically:
  `/goal` and `/loop` run a *prompt*, not a folder, so the loop is started by a
  prompt that **invokes its skill by name/description** (e.g. "run the `<loop-name>`
  loop"). A `SKILL.md` left under `loops/` is *not* a discoverable skill and can't be
  invoked that way — it would have to be read by explicit path instead.
- **Changing → a state folder.** Put run state under `<project>/loops/<loop-name>/`
  (`STATE.md`, plus any run inputs/outputs). Read and written every run.

Every loop gets **all six** blocks; a missing one is what breaks (see the table).

| # | Block | What you write | Durable or changing |
|---|---|---|---|
| 1 | **Scheduling** | A trigger stub (cron line / `/schedule` / `/loop` / `/goal <condition>` / run-until-verifier) | durable |
| 2 | **Isolation** | A note/command for git worktrees *if* file work runs in parallel | durable |
| 3 | **Skill** | The loop's **own** `SKILL.md`, **installed under `.claude/skills/<loop-name>/`** — conventions only | **durable** |
| 4 | **Connectors** | Named MCP/tools for discovery + action | durable |
| 5 | **Verifier** | A **separate** check — start from `scripts/verifier_template.sh` | durable |
| 6 | **State** | `STATE.md` ledger (or board) in `loops/<loop-name>/` — what's done / open | **changing** |

Concretely, write:

- **`.claude/skills/<loop-name>/SKILL.md`** — the loop's own skill: its goal,
  conventions, the pattern it uses, how to run it, and what "done" means. Installing
  it here is what makes the loop invocable by a prompt. **Conventions only — never
  progress.**
- **`loops/<loop-name>/STATE.md`** — a ledger the loop reads and writes each run: a
  table of items with status, plus "last run" notes. This is the changing half; keep
  it out of the skill.
- **A verifier script** — copy `scripts/verifier_template.sh` and wire it to the
  user's predicate. If it's a "no P1 unassigned"-style check, adapt
  `scripts/verify_no_p1_unassigned.sh`. The verifier must be *separate* from the
  generator and deterministic where possible.
- **A trigger stub** — how the loop is *launched*. `/goal` and `/loop` run a
  *prompt*, so the stub must **name the loop** (`run the <loop-name> loop`) to load
  its skill. Match the launcher to the trigger type from Q2 — **don't default
  everything to `/loop`**, which only makes sense for a recurring cadence:
    - **Run-until-done / on-demand** (you start it when there's new input — e.g. a
      comparison loop): just invoke it, `/goal "<condition>"  run the <loop-name>
      loop`. **No `/loop`** — it isn't recurring; the trigger is *you*.
    - **Scheduled** (a cadence): `/schedule "<cron>" …`, or `/loop <interval>` for a
      simple interval; pair with `/goal "<condition>"` to self-terminate each run.
    - **Event-driven** (fire when something appears): `/goal`/`/loop` can't *listen*
      for events. Either **(a) poll** — a low-frequency `/loop <interval>` that checks
      a queue/inbox and runs only when there's new work — or **(b) a real external
      launcher** (a git hook, CI/webhook, file-watcher, or a managed runtime; see
      `references/deploy-claude-managed-agents.md`) that invokes the loop when the
      event fires.
  `/goal` maps directly to the recursive Goal (Q1), so its condition must be the same
  checkable predicate. **Annotate that these mechanics may have changed — verify
  against current docs; never fabricate flags.**
- **`HUMAN-GATES.md`** — the irreversible-actions list **and** the budget/stop
  condition, together. This file is mandatory; see below.
- **Self-reporting (opt-in).** Ask: "Add self-reporting to this loop? (logs its own
  errors locally for you to review later — never auto-files)" If yes, add the hook
  snippet from the `loop-builder:feedback-to-issue` skill's
  `references/feedback-to-issue.md` to the verifier. Errors collect
  locally; the user files them deliberately in a later review session.

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

## Worked examples

Three filled-in templates, chosen to span the grid: different patterns, different
trigger types, and the two gate postures (soft "escalate" vs. a hard stop on an
irreversible action). Use them to calibrate the shape of a good answer — don't copy
one verbatim onto a different-shaped problem.

### Example 1 — morning GitHub triage *(ReAct + deterministic · scheduled · soft gate)*

```
GOAL (verifiable):      zero P1 issues without an assignee AND a plan comment
TRIGGER:                schedule → every weekday 08:00 (cron "0 8 * * 1-5")
DISCOVERY (find work):  list open P1 issues   (connector: GitHub MCP / gh)
ACTION (do work):       assign an owner, post an initial plan comment (tools: gh)
VERIFY (separate check): re-query, assert no P1 lacks assignee  (deterministic? y →
                         scripts/verify_no_p1_unassigned.sh)
REUSE (installed):      GitHub MCP → connector (④); fallback: gh CLI
REUSE (skill-bank):     none applicable — verifier is a bundled deterministic script
                         (searched the bank; nothing fits better)
STATE (persist outside): loops/triage/STATE.md — issues triaged this week
HUMAN GATES:            none auto-closes; escalate (don't close) anything ambiguous
KNOWLEDGE → skill:      label taxonomy, what a "plan comment" must contain
BUDGET / stop:          max 25 issues/run; stop when verifier passes or cap hit
```

Pattern: ReAct + deterministic verifier (one workstream, program-checkable goal).
Comments and labels are reversible, so no hard human gate is required — but the
*budget* and the *escalate-don't-close* rule still ship.

### Example 2 — inbox draft-replies *(evaluator–optimizer · run-until-done · hard gate)*

```
GOAL (verifiable):      every unread thread from the last 24h is either drafted-and-
                        queued or explicitly skipped with a logged reason
TRIGGER:                run-until-done → you start it when you sit down. No recurring
                        /loop needed; the loop self-terminates at the goal each run.
DISCOVERY (find work):  list unread threads in the last 24h  (connector: Gmail MCP)
ACTION (do work):       write a reply into the drafts folder per thread
                        (tools: Gmail MCP — DRAFTS ONLY, no send scope)
VERIFY (separate check): a SEPARATE evaluator sub-agent grades each draft against a
                        rubric (answers the question, right tone, no overcommitment)
                        — judgement, not a script (deterministic? n)
REUSE (installed):      Gmail MCP → connector (④); codex as a different-model
                        evaluator (⑤); fallback: a general-purpose sub-agent
REUSE (skill-bank):     none applicable — evaluator is the installed different-model
                        sub-agent (searched the bank)
STATE (persist outside): loops/inbox/STATE.md — threads drafted / skipped + reasons
HUMAN GATES:            SENDING is a hard gate — the loop only drafts; you press send
KNOWLEDGE → skill:      voice/tone guide, what never to commit to in writing,
                        who to escalate to instead of answering
BUDGET / stop:          max 20 threads/run; stop when each is drafted-or-skipped
```

Pattern: Evaluator–optimizer — drafts need *judgement*, so a separate evaluator
grades against a rubric (a different-model checker is stronger than a same-model
one). Sending is irreversible and prompt-injection-exposed, so it is a permanent
human gate — the single most important line in this loop. Note the trigger: it is
*you*, not a clock, so there is no `/loop`.

### Example 3 — nightly CI fix *(ReAct + deterministic · event-driven · isolated · hard gate)*

```
GOAL (verifiable):      latest nightly build is green, OR a fix PR exists linked to
                        the failure
TRIGGER:                event-driven → on nightly-build failure. /goal·/loop can't
                        LISTEN, so either a CI/webhook launcher invokes the loop, or a
                        low-frequency /loop polls build status and runs only on a new
                        red build.
DISCOVERY (find work):  read the failing job log + the diff since last green
                        (connector: GitHub / CI MCP)
ACTION (do work):       reproduce, write a fix, open a PR
                        (tools: gh ; isolation: worktree? y — parallel file work)
VERIFY (separate check): re-run build/tests on the fix branch; green = pass
                        (deterministic? y — the build itself is the verifier)
REUSE (installed):      GitHub MCP → connector (④); the build command is the
                        verifier; fallback: gh CLI
REUSE (skill-bank):     gstack:investigate (⑤) surfaced by the bank search for root-causing
                        failures; install: clone into ~/.claude/skills/; fallback:
                        inline debugging; verify mechanics against source
STATE (persist outside): loops/ci-watch/STATE.md — failures seen, fix PRs, status
HUMAN GATES:            opening a PR is fine; MERGING is a hard gate — a human reviews
KNOWLEDGE → skill:      how to run the build locally, where flaky tests live,
                        branch / PR conventions
BUDGET / stop:          max 3 fix attempts/failure; stop when green or a PR is open
```

Pattern: ReAct + deterministic verifier again (the build is the program-checkable
predicate), but event-triggered and worktree-isolated because file work runs in
parallel. The verifier is the same kind as Example 1 yet the *trigger* and
*isolation* differ — a reminder that pattern, trigger, and isolation are independent
choices.

## Output discipline checklist

Before declaring the loop scaffolded, confirm:

- [ ] All seven decisions answered; goal is a checkable predicate.
- [ ] **Installed** capabilities surveyed (1.5a — find-skills / MCP list).
- [ ] **skill-bank searched** (1.5b): the search sub-agent (or the direct-read fallback) was run over `recommended.md` + `catalog/*.md`; relevant entries surfaced, or "none applicable — <reason>" recorded. Not skippable.
- [ ] Anything wired in (installed or bank) has a named fallback.
- [ ] One pattern chosen; only its reference was loaded.
- [ ] Populated template shown to the user.
- [ ] Six blocks scaffolded as files in the loop folder.
- [ ] A **separate** verifier exists (script or sub-agent), deterministic if possible.
- [ ] An **external state file** exists — and no mutable state lives in any SKILL.md.
- [ ] `HUMAN-GATES.md` lists irreversible actions **and** a budget/stop condition.
- [ ] Any `/goal` `/loop` `/schedule` mechanic is flagged "verify against current docs."

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

## Collecting feedback and reporting bugs

Bugs and rough edges are captured **locally** — never auto-filed — and filed to
GitHub under **your own account** only when you explicitly say so.

**Passive capture (on errors).** When loop-builder hits an error or you are clearly
blocked, append a quiet entry:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback/cli.py" \
  append --category bug --text "<what broke + context>"
```

This writes to `~/.loop-builder/feedback.jsonl` only. No network call is made.

**Review and file.** When the user asks to "report a bug," "give feedback," or
"review feedback," invoke the `loop-builder:feedback-to-issue` skill — it owns the
full flow (list-open → cluster → draft → dedupe → sanitize → **mandatory consent
gate** → file → mark-filed) under the user's own account. Do not inline that flow
here.

**Generated loops.** During scaffolding, ask whether to add self-reporting to the
loop (the opt-in hook lives in the `loop-builder:feedback-to-issue` skill's
`references/feedback-to-issue.md`). When opted in, resolve the feedback CLI path via
`${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback` and bake it into
the loop's `LOOP_BUILDER_SCRIPTS` variable. Self-reporting logs failures locally; the
loop never contacts GitHub on its own.
