# What Is a Loop, and What Is Loop Engineering?

*A foundational reference for building a "loop-builder" skill. Written so it can sit under a `SKILL.md` as durable project knowledge — the conventions and mental model a loop-builder skill rereads on every run, not the changing state of any one project.*

---

## 0. How to use this document

This is the **knowledge layer** for a loop-builder skill: it defines what a loop is, the parts every loop needs, and the decisions a user must make to build one. A builder skill's job is to walk a user through those decisions and scaffold the result. The last two sections (7 and 8) are the operational core — the blueprint to elicit from the user, and how to encode a loop as a skill. Sections 1–6 are the concepts that make those steps make sense.

One discipline runs through the whole document: **durable knowledge goes in a skill; changing state goes in memory.** Keep that line visible — it is the single most common mistake in loop design.

---

## 1. What is a loop?

A loop is **not one long prompt**. It is a small self-running system in which an agent runs, gets graded against explicit criteria, revises, and repeats — until the criteria pass or a budget runs out, without a human typing each turn.

The reason loops need engineering at all is one blunt fact: **the agent starts cold every run.** The model forgets everything between runs, so conventions, build commands, review standards, and "what's already done" are re-derived from scratch unless they live outside the context window, on disk. Every long-running agent depends on this trick: the agent forgets, the repo does not.

The minimal anatomy of a working loop has three parts:

- **Generator** — the agent doing the work.
- **Evaluator** — a *separate* agent or program that grades the output against a checkable rubric. A model grading its own output is too generous.
- **The loop** — feeds the evaluator's verdict back to the generator until the rubric passes or the budget is spent.

A useful honest framing from practitioners: a loop is **cron plus a decision-maker in the body**. The interesting engineering is everything you wrap around that decision so it does not run off a cliff.

---

## 2. What is loop engineering?

**Loop engineering is the practice of designing the system that prompts an agent on a schedule, instead of typing each prompt by hand.** You define a recursive goal, give the agent a way to find work, act on it, verify the result, remember what is done, and then let that system drive the agent.

It is the latest step in a short lineage. Per *The New Stack*, developers moved from **prompt engineering → context engineering → harness engineering → loop engineering in under 18 months.** Context engineering — Karpathy's "filling the context window with just the right information for the next step," which Anthropic formalized in September 2025 — was about curating one step's tokens. Loop engineering optimizes the *autonomous system that decides what to prompt, when, and whether the result is acceptable.* Prompt engineering treats the agent as a tool you hold; loop engineering treats it as a long-running process with scheduling, evaluation, memory, and orchestration.

The term was popularized in **June 2026 by Google engineer Addy Osmani**, building on Peter Steinberger's line that you should be designing the loops that prompt your agents, and on **Anthropic Claude Code lead Boris Cherny**, who described his work as writing loops rather than prompting the model directly (reportedly authoring most of his recent code this way). Why it became viable now: by mid-2026 coding agents could run autonomously long enough — and recover from their own mistakes well enough — that the bottleneck moved from the prompt to the system around it.

**The stance that matters:** build the loop like someone who intends to *stay the engineer*, not someone who just presses "go." The same loop design can accelerate a person's judgment or let them abdicate it.

---

## 3. The anatomy of a loop: six building blocks

Osmani's anatomy names six parts. Five are capabilities; the sixth is the spine that holds state between runs. Tool names differ across Claude Code and Codex, but the capabilities are the same.

| # | Block | Its job | What breaks without it |
|---|-------|---------|------------------------|
| 1 | **Automations / scheduling** | The heartbeat — prompts that fire on a cadence and do discovery and triage by themselves; or "run until a verifiable condition holds." | You have a one-off session, not a loop. |
| 2 | **Isolated workspaces** (git worktrees) | Keep parallel agents from colliding on the same files. | Parallel agents corrupt each other's work. |
| 3 | **Skills** (`SKILL.md`) | Codify durable project knowledge once so the loop stops re-deriving conventions every cycle. | Every run is day one; knowledge never compounds. |
| 4 | **Connectors** (MCP) | Plug the loop into real systems — read the tracker, query a DB, open the PR, post to Slack. | The agent comments ("here's the fix") instead of operating (opens the PR, links the ticket). |
| 5 | **Sub-agents** | Split the maker from the checker; each with its own fresh context. | The worker grades its own homework. |
| 6 | **Memory / external state** | Holds what's done and what's next, outside the context window (a markdown file, a Linear or GitHub board). | The cold-start agent repeats work and loses the thread. |

The practical rule for choosing among these: **prefer the simplest pattern that works, and compose blocks rather than reaching for a heavy framework.** A single loop with a deterministic verifier beats an elaborate multi-agent system you cannot debug.

---

## 4. Skills vs. memory: the line you must not blur

Blocks 3 and 6 are close cousins and are constantly confused. They are not interchangeable.

| | **Skill** (durable) | **Memory / external state** (changing) |
|---|---|---|
| Holds | how we build, our conventions, our procedures | what got tried, what passed, what's still open |
| Changes | rarely; version-controlled, reviewed | every run |
| Loaded | read-only, every iteration | read **and written** every iteration |
| Examples | build commands, review standards, "we don't do it that way" | a triage log, a task ledger, a decision record, a Linear board |

A skill is durable knowledge written on the *outside*, where the agent reads it every run; memory is the changing state of *this* project's progress. **Putting mutable state inside a `SKILL.md` is the classic anti-pattern** — skills are version-controlled and effectively read-only per run, so they are the wrong home for anything that changes daily.

A terminology caveat worth flagging: some academic taxonomies (e.g., the "Externalization in LLM Agents" survey) file *semantic knowledge* under memory and reserve *skills* for operational procedures, heuristics, and constraints. So "knowledge management" is an overloaded phrase. In loop-engineering vernacular, **"skills = project knowledge" means the durable-conventions kind specifically.**

---

## 5. Why a loop puts project knowledge in skills

The loop's defining constraint — runs repeatedly, unattended, cold every time — creates four needs, and skills satisfy all four at once. This is *why* skills are the slot for project knowledge:

1. **Defeats amnesia, compounds knowledge.** Conventions in a skill reload every run, so the loop stops re-deriving them. Without skills every run is day one; with them, knowledge compounds.
2. **Per-iteration context economy.** A loop pays token cost on every tick. Skills preload only name + description and load the body when relevant, so an agent keeps many skills on hand with a small context footprint. An always-on context file does not scale that way; skills give *selective* loading.
3. **Repeatability for the verifier.** A loop's maker/checker split needs "done" to mean the same thing each run. Pinning conventions in a skill turns work into consistent, auditable procedures, so behavior doesn't drift across cold starts.
4. **Governed, portable artifacts.** Skills are version-controlled files — diffable, revertible, auditable — which matters when fleets of agents run unattended. Bundle them as a plugin so every sub-agent reads the same knowledge; enterprise setups mount them from a registry with versions, provenance, and RBAC.

In short: the loop forces knowledge to be *external* (amnesia), *selectively loaded* (cost), *stably applied* (verification), and *governed as files* (fleets). Skills are the one block whose properties match all four — while connectors handle changing *external data* and the memory block handles changing *state*.

---

## 6. Loop patterns (pick the simplest that works)

These are the recurring shapes a builder skill should be able to recommend. Several trace to Anthropic's *Building Effective Agents*.

- **Evaluator–optimizer.** One model generates a candidate; a second evaluates it against criteria and returns feedback; they cycle until evaluation passes. Best when you have clear, articulable acceptance criteria.
- **Orchestrator–workers.** A central orchestrator breaks a task into subtasks, delegates each to a worker sub-agent with its own fresh context, and synthesizes results. This is how parallel, overnight agent fleets are built (Osmani's "sub-agents" + "worktrees").
- **ReAct loop with a deterministic verifier.** A single act–observe loop whose "done" check is a program (tests, a linter, a schema check), not a model's opinion. Often the right default.
- **The Ralph technique** (Geoffrey Huntley, early 2026). Run an agent inside a plain `while` loop, feeding the same prompt against a written spec until the work converges. The crudest viable loop — useful as a baseline and a teaching device.

Guidance to encode: **compose patterns; don't reach for a framework you can't debug.** Start with a ReAct loop plus a deterministic verifier, and add orchestration only when the work genuinely parallelizes.

---

## 7. Blueprint: the seven decisions behind every loop

This is the elicitation core of a loop-builder skill. To build a loop for *any* purpose, get explicit answers to these seven, in order. Each maps to a building block from Section 3.

1. **Goal (recursive).** What verifiable condition means "done for now"? State it as a checkable predicate, not a vibe. *Bad:* "keep the repo healthy." *Good:* "every P1 issue has an owner and a plan comment."
2. **Trigger.** What fires the loop — a schedule (cron, `/loop`, `/schedule`), an event (a new PR, an inbound email), or run-until-done?
3. **Discovery.** How does the agent *find* work each cycle? (Query the tracker, scan the inbox, diff CI.) → connectors.
4. **Action.** What is the agent allowed to *do*, and through which tools? → connectors; isolate file work in → worktrees.
5. **Verification.** Who checks the result, and against what? Use a **separate** checker (sub-agent or program). Prefer a deterministic check where one exists. → sub-agents.
6. **State / memory.** Where does "what's done / what's open" persist *outside* the context? (Markdown ledger, Linear, GitHub issues.) → memory. Conventions and "how we do it" go in a → skill, not here.
7. **Human gates.** Which actions are irreversible or high-blast-radius, and therefore require a human approval before execution? (Merging, sending external email, spending, deleting.) This is non-negotiable; see Section 9.

**Worked example — a morning triage loop:**

- *Goal:* zero P1 issues without an assignee and a plan comment.
- *Trigger:* every weekday, 08:00.
- *Discovery:* read open issues labeled P1 via the tracker connector.
- *Action:* assign an owner, post an initial plan comment.
- *Verification:* re-query; assert no P1 issue lacks an assignee.
- *State:* a log of issues already triaged this week.
- *Human gate:* none needed (comments and labels are reversible) — but escalate, don't close, anything ambiguous.

A builder skill can ship this as a fill-in template:

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

---

## 8. Encoding a loop as a skill (skill-builder reference)

A loop-builder skill is itself an "X-builder" skill, so it should borrow the shape of `skill-creator`: **capture intent → interview for edge cases → draft → test on realistic prompts → review with the user → iterate → package.** Apply that same arc to loops.

**Skill mechanics to respect** (from Anthropic's Agent Skills format):

- **Anatomy.** A skill is a folder with a required `SKILL.md` (YAML frontmatter: `name`, `description`) plus optional `scripts/` (deterministic code), `references/` (docs loaded on demand), and `assets/` (templates).
- **Progressive disclosure, three levels:** (1) name + description, always in context (~100 words); (2) the `SKILL.md` body, loaded when the skill triggers (aim < ~500 lines); (3) bundled resources, pulled in only as needed. If the body grows past ~500 lines, push detail into `references/` and point to it.
- **The description is the trigger.** It must say *what the skill does* **and** *when to use it*, and lean slightly "pushy," because skills tend to under-trigger. For a loop-builder: name the surfaces explicitly — *"Use whenever the user wants to automate a recurring task, schedule an agent, build a loop, set up triage/monitoring, or turn a manual workflow into an unattended one."*
- **Writing style.** Imperative voice; explain *why* a rule matters instead of stacking bare "MUST"s; keep it general, not pinned to one example. Define output formats with a literal template; show one worked input→output example.
- **Principle of least surprise.** A skill's behavior should match what its description implies — no hidden actions, no network calls or file access that a reader wouldn't expect.

**Design notes specific to a loop-builder skill:**

- **Organize patterns as variants.** Put each loop pattern (evaluator–optimizer, orchestrator–workers, ReAct+verifier, Ralph) in `references/patterns/`, and let the `SKILL.md` body do *selection* — ask the seven questions, recommend a pattern, then load only the matching reference.
- **Elicit, then scaffold.** The body should run Section 7's seven questions, then emit the fill-in template populated, then generate the six blocks (schedule entry, discovery/action via named connectors, a separate verifier, a state file, and a list of human gates).
- **Bundle deterministic checks as `scripts/`.** Verifiers (schema checks, "no P1 unassigned," test runners) belong in code, not prose — they're the part that must be reliable.
- **Separate durable from changing in the output.** What the builder writes into the loop's *own* skill = conventions. What it writes into the loop's *state file* = progress. The builder skill should enforce this split in everything it generates.
- **Always emit the human-gate list and a stop condition (budget).** A loop with no budget and no gates is the failure mode, not the goal.

---

## 9. Honest limitations

A loop-builder skill should bake these in rather than paper over them — they are the practical posture, not disclaimers.

- **Prompt injection is unsolved.** A loop that reads issues, emails, or web content is ingesting untrusted text on every cycle. Defense-in-depth helps; the durable control is a **permanent human gate on irreversible actions** (merging, sending, spending, deleting). Never let a loop cross those autonomously.
- **Verification is the hard part — harder than ever.** Autonomy is only as trustworthy as the checker. Favor deterministic verifiers; keep the checker separate from the maker; treat a passing self-grade with suspicion.
- **Token economics swing wildly.** Loops can be cheap or alarming depending on cadence, fan-out, and retries. Set explicit budgets (max iterations, token caps, wall-clock) and dynamic intervals (short waits while a build finishes, long waits when nothing's pending).
- **Most of "agentic" is plumbing.** A candid practitioner summary: many shipped agents are a for-loop, an LLM call, and a try/catch around JSON parsing. The discipline is in the guardrails around the decision, not in the decision being magic.

---

## Sources (graded)

**Primary / originating**
- Addy Osmani, *Loop Engineering* (addyosmani.com, June 2026) — coined the term and the six-block anatomy.
- Boris Cherny (Head of Claude Code, Anthropic) and Peter Steinberger (OpenAI) — the "write loops, not prompts" framing, via interviews and reporting below.

**Official (Anthropic)**
- *Equipping agents for the real world with Agent Skills* (anthropic.com/engineering) — Skills definition, progressive disclosure.
- Agent Skills documentation (platform.claude.com; code.claude.com) and the open standard (agentskills.io).
- *Building Effective Agents* (Anthropic) — evaluator–optimizer and orchestrator–workers patterns.

**Peer-reviewed / academic**
- *Externalization in LLM Agents: Memory, Skills, Protocols and Harness Engineering* (arXiv 2604.08224) — the memory-vs-skills taxonomy.

**Secondary explainers** (useful, but blog-grade and weeks-old; treat specific numbers with caution)
- *The New Stack* — the prompt→context→harness→loop lineage; maker/checker harness work.
- Lushbinary; explainx.ai; Tosea.ai; TrueFoundry; cobusgreyling.substack.com; zyte.com — six-block walkthroughs, `/loop` mechanics, the morning-triage example, enterprise registry/RBAC framing.

> **Uncertainty flag.** Loop engineering as a named practice is months old as of mid-2026. The core concepts (cold-start, six blocks, skills-vs-memory, maker/checker) are consistent across primary and official sources. Specific product mechanics (`/loop`, `/schedule`, dynamic intervals, PR counts) come mostly from secondary reporting and may have shifted — verify against current Claude Code / Codex docs before encoding them as fact in a skill.
