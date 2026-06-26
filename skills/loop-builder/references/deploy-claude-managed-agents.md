# Deploy target: Claude Managed Agents

> A *managed runtime* to run a loop on, not a pattern. Where the other references
> answer "what shape is this loop," this one answers "where does it run." Load it
> in Phase 1.5 if the user has access to Claude Managed Agents and would rather use
> native features than hand-roll blocks against Claude Code primitives.

## ⚠️ Uncertainty flag (read first)

Claude Managed Agents launched into **public beta on 2026-04-09** and gained
features month to month (scheduling + credential access in June 2026). It is exactly
the kind of fast-moving product mechanic this skill refuses to hardcode. The mapping
below is drawn from **secondary reporting**, so treat specifics as directional and
**verify against the current Claude Platform docs before relying on any feature,
flag, or name.** Always keep a Claude Code fallback (`/loop`, worktrees, sub-agents,
a bundled verifier script, a `STATE.md` file) so a loop still works if a managed
feature is unavailable or has changed.

## What it is

Cloud-hosted agents on the Claude Platform: you define an outcome, the agent runs
unattended, and you're notified (e.g. webhook) when it's done. It ships native
analogues for most of the six building blocks — which is *why* it's a natural deploy
target, and a good independent validation that the six-block anatomy is sound.

## When to target it (vs. local Claude Code)

- **Target it** when the loop should run unattended in the cloud, needs scheduled
  runs and authenticated access to external services, and you'd rather use a managed
  scheduler / grader / memory than build them.
- **Stay on local Claude Code** when the work is repo-local, you want everything in
  version control, or you can't depend on a beta platform. The skill's default
  scaffold already covers this.
- These are **complementary**: you can design the loop with the seven questions and
  *then* choose where it runs.

## Block-by-block mapping

| # | Loop block | Managed Agents native feature *(verify in docs)* | Claude Code fallback |
|---|---|---|---|
| ① | Trigger | cron schedules; "define outcome → run → webhook on done" | `/schedule`, `/loop`, run-until-verifier |
| ② | Isolation | self-hosted sandboxes; specialists on a shared filesystem | git worktrees |
| ③ | Skill (durable) | still the loop's own conventions/rubric — author it the same | same |
| ④ | Connectors | credential vaults, authenticated CLI/services, MCP tunnels | MCP servers, `gh`, etc. |
| ⑤ | Verifier / sub-agents | **"outcomes": write a rubric → a *separate grader* evaluates and retries**; lead agent delegating to parallel specialists | a `scripts/` verifier + a sub-agent checker |
| ⑥ | State / memory | managed **memory**, plus "dreaming" (cross-session learning) | a `STATE.md` ledger / board |
| ⑦ | Human gates | review memory/"dreaming" changes **before they land** | the loop pauses and asks; `HUMAN-GATES.md` |

## How the patterns map

- The **outcomes + separate grader that retries** is the **evaluator–optimizer**
  pattern as a product primitive — and it honors the maker/checker split the skill
  insists on. Still write the rubric down as **durable** knowledge (the loop's
  skill), not as run state.
- The **lead-agent-delegates-to-parallel-specialists** model is
  **orchestrator–workers**; the same "only when work genuinely parallelizes" rule
  applies.

## Scaffolding notes (what stays true regardless of runtime)

- **Still emit the human-gate list and a budget.** A managed scheduler makes runaway
  cost *easier*, not harder — cap iterations/wall-clock and gate irreversible actions
  (the platform's "review before it lands" is one such gate, not a replacement for
  your own list).
- **Watch the durable/changing line with "dreaming."** Self-refining memory is the
  *changing* block (⑥). Don't let it quietly mutate what should be durable
  conventions (③); keep the rubric and conventions in the skill, and prefer
  reviewing memory changes before they land for anything load-bearing.
- **Keep the verifier separate.** Use the managed grader as the checker, but it's
  still a *separate* grader against an explicit rubric — don't collapse maker and
  checker because the platform makes it convenient.

## Sources (secondary; verify against Claude Platform docs)

- InfoQ — *Code with Claude 2026* (Managed Agents, proactive workflows).
- 9to5Mac — Managed Agents three new features (memory, "dreaming", outcomes/grader);
  and the later privacy/security features (sandboxes, MCP tunnels).
- Reporting on the 2026-04-09 launch and the June 2026 scheduling + credential update.
