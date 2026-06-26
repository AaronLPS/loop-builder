# Pattern: Orchestrator–workers

> From Anthropic's *Building Effective Agents*, via `loops-and-loop-engineering.md`
> §6. This is how overnight, parallel agent fleets are built (Osmani's "sub-agents"
> + "worktrees"). Escalate to it **only when the work genuinely parallelizes.**

## What it is

A central **orchestrator** breaks a task into independent subtasks, delegates each
to a **worker** sub-agent with its own fresh context, then **synthesizes** the
results. Each worker runs in an isolated workspace so parallel workers don't collide
on the same files.

## When it fits

- The work decomposes into subtasks that are genuinely independent (many issues,
  many files, many repos) and benefit from running at once.
- You'd otherwise wait serially for things that have no ordering dependency.
- If there's really one workstream, do **not** use this — the orchestration is pure
  overhead. Use [react-deterministic-verifier](pattern-react-deterministic-verifier.md).

## Loop shape

```
orchestrator:
  subtasks = plan(task)                       # split into independent units
  for each subtask (in parallel):
     worktree = isolated workspace
     result   = worker(subtask) in worktree   # fresh context each
     verdict  = verifier(result)              # separate checker per result
  synthesis = combine(passing results)
  stop when all subtasks pass or budget exhausted
```

Composition matters: each worker's result still needs its **own** verification —
typically a deterministic check, or an evaluator sub-agent. Orchestration does not
remove the maker/checker split; it multiplies it.

## Six-block mapping

| Block | Here |
|---|---|
| Scheduling | Usually `/schedule` for overnight fleets (verify mechanic vs current docs) |
| Worktrees | **Required** — one isolated workspace per worker, or they corrupt each other |
| Skills | Shared `SKILL.md` so every worker reads the same conventions (bundle as a plugin) |
| Connectors | Discovery (what to fan out over) + action per worker |
| Sub-agents | **Required** — orchestrator + N workers + checker(s) |
| Memory | A board (Linear/GitHub issues) or `STATE.md` tracking each subtask's status |

## Scaffolding notes

- Give every worker the same skill so conventions don't drift across the fleet.
- The state must track per-subtask status so a cold-start orchestrator doesn't
  re-dispatch finished work.
- Budget is doubly important: fan-out multiplies token cost. Cap workers AND
  per-worker iterations.
- Human-gate the *synthesis/merge* step, not just individual actions, when results
  combine into something irreversible.

## Pitfalls

- Reaching for this when work is actually serial — you get a framework you can't
  debug for no parallelism gain. Compose patterns; don't over-build.
- Workers sharing a workspace → corruption. Isolation is not optional here.
