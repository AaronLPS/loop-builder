# Pattern: Evaluator–optimizer

> From Anthropic's *Building Effective Agents*, via `loops-and-loop-engineering.md`
> §6. Use when "done" is real but richer than a single program can check.

## What it is

One model **generates** a candidate; a **separate** model **evaluates** it against
explicit criteria and returns feedback; they cycle until the evaluation passes or
the budget is spent. The split — generator ≠ evaluator — is the point; a model
grading its own output is too generous.

## When it fits

- You have **clear, articulable acceptance criteria**, but they need judgement to
  apply (e.g. "the reply is accurate, on-brand, and answers every question asked").
- A pure deterministic check would be too crude to capture quality.
- If your criteria *can* be reduced to a program, prefer
  [react-deterministic-verifier](pattern-react-deterministic-verifier.md) instead —
  it is cheaper and more trustworthy.

## Loop shape

```
loop:
  candidate = generator(task, last_feedback)
  verdict, feedback = evaluator(candidate, rubric)   # SEPARATE agent + fresh context
  if verdict == pass: stop (record candidate + in state)
  else: last_feedback = feedback; iterate
  stop also if budget exhausted
```

Make the rubric explicit and written down (in the loop's skill), so "pass" means
the same thing every cold start. Where any part of the rubric is mechanically
checkable, run that part as a deterministic pre-filter before spending the
evaluator model — a hybrid is usually best.

## Six-block mapping

| Block | Here |
|---|---|
| Scheduling | `/schedule` or run-until-pass (verify mechanic against current docs) |
| Worktrees | If candidates are file edits done in parallel |
| Skills | The rubric and conventions live in the loop's `SKILL.md` |
| Connectors | For discovery/action (inbox, tracker, docs) |
| Sub-agents | **Required** — evaluator is a separate sub-agent with its own context |
| Memory | `STATE.md`: candidates tried, verdicts, what passed |

## Scaffolding notes

- Encode the rubric as a literal checklist in the loop's skill; keep the running
  log of attempts/verdicts in the state file.
- Cap iterations explicitly — evaluator–optimizer can oscillate without converging.
- Human-gate anything the candidate would *send* or *publish* if it passes.

## Pitfalls

- A vague rubric makes the evaluator a rubber stamp. If you can't write the rubric,
  you can't run this loop yet — pin the criteria first.
- Same model, same context for both roles defeats the separation. Keep them apart.
