# Pattern: The Ralph technique

> Geoffrey Huntley, early 2026, via `loops-and-loop-engineering.md` §6. The crudest
> viable loop — most useful as a **baseline and a teaching device**, not usually the
> answer for production.

## What it is

Run an agent inside a plain `while` loop, feeding the **same prompt** against a
**written spec** until the work converges. No orchestration, no separate evaluator
in the classic form — just repetition against a fixed target.

## When it fits

- You want a dead-simple baseline to feel out whether a loop helps at all.
- The spec is stable and the task is the kind that converges by repeated passes.
- Teaching: it makes the "cron + a decision-maker in the body" framing concrete.

For anything you'll run unattended and trust, graduate to
[react-deterministic-verifier](pattern-react-deterministic-verifier.md) so "done" is
checked by a program rather than implied by "the agent stopped changing things."

## Loop shape

```
while not converged:
   run agent with THE SAME prompt against spec.md
   (convergence judged by: spec satisfied / no further changes / budget hit)
```

The honest framing from the reference: a loop is "cron plus a decision-maker in the
body." Ralph is that sentence with the smallest possible wrapper.

## Six-block mapping

| Block | Here |
|---|---|
| Scheduling | The `while` loop itself, or `/loop` (verify mechanic vs current docs) |
| Worktrees | Optional; add if edits could collide |
| Skills | The spec + conventions; keep the spec stable across iterations |
| Connectors | Minimal — often just the filesystem |
| Sub-agents | None in the classic form (its main weakness) |
| Memory | The repo/working tree *is* the state; add a `STATE.md` if you need a ledger |

## Scaffolding notes

- **Add a stop condition.** A bare `while` with no budget is the canonical runaway
  loop. Always cap iterations / wall-clock / tokens.
- Because there's no separate checker, be honest that convergence here is weaker
  evidence than a passing deterministic verifier. Note this in the human-gate doc.
- Keep the spec in a durable file (skill/spec), not regenerated each run.

## Pitfalls

- No maker/checker split → the loop can "converge" on something wrong. Treat Ralph
  output with suspicion; verify before trusting.
- No budget → runaway cost. This pattern fails loudest exactly where loops are
  supposed to be careful.
