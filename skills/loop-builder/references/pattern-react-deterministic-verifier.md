# Pattern: ReAct loop with a deterministic verifier

> **This is the default.** Reach for it first; only escalate to another pattern when
> this one genuinely cannot express the work. Source: Anthropic's *Building
> Effective Agents* lineage, via `loops-and-loop-engineering.md` §6.

## What it is

A single act → observe loop whose "done" check is a **program** — tests, a linter,
a schema check, a predicate script — not a model's opinion. The agent acts,
observes the verifier's verdict, and repeats until the verifier passes or the
budget is spent.

## When it fits

- There is one workstream, not many parallel ones.
- "Done" can be reduced to a check a computer can run and re-run identically.
- You want the simplest thing that is trustworthy. (Most loops are this.)

If you find yourself wanting several workers in parallel, see
[orchestrator-workers](pattern-orchestrator-workers.md). If "done" is real but only
expressible as nuanced judgement, see
[evaluator-optimizer](pattern-evaluator-optimizer.md).

## Loop shape

```
loop:
  work    = generator acts (read state, find work, do the action)
  verdict = deterministic_verifier()          # a script, exit 0/non-zero
  if verdict == pass: stop (record in state)
  else: feed verdict back to generator; iterate
  stop also if budget exhausted (iterations | tokens | wall-clock)
```

The verifier is the heart. Build it with `scripts/verifier_template.sh` as the
spine and a concrete predicate (e.g. `scripts/verify_no_p1_unassigned.sh`). Keep it
separate from the generator — a maker grading its own homework is the failure mode.

## Six-block mapping

| Block | Here |
|---|---|
| Scheduling | `/schedule` cron or `/loop` (verify mechanic against current docs), or run-until-verifier-passes |
| Worktrees | Only if the action edits files and may run concurrently |
| Skills | The loop's own `SKILL.md` — conventions, "what done means", commands |
| Connectors | Whatever discovery/action needs (tracker, CI, filesystem) |
| Sub-agents | Optional; the verifier being a *program* often removes the need |
| Memory | `STATE.md` ledger of what's done / open |

## Scaffolding notes

- The verifier script is non-negotiable and must be deterministic.
- Always emit the human-gate list and a budget. A ReAct loop with no stop condition
  will happily spin.
- Put "how we decide done" in the loop's skill; put "what we've done" in the state
  file. Never the reverse.

## Pitfalls

- A flaky verifier (network-dependent, time-dependent) makes the whole loop
  untrustworthy. Make checks hermetic where possible (operate on saved JSON, not a
  live query, when verifying).
- Don't let a model "interpret" a failing check into a pass.
