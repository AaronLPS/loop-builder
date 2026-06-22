# feedback-to-issue — design

A low-friction mechanism that captures bug reports and feedback while people use
loop-builder (and the loops it scaffolds), summarizes them, and helps the user
file a GitHub issue **under their own account** — so an early-stage public
project can collect trackable feedback without anyone routing issues through the
maintainer's identity.

## Problem

loop-builder is early-stage and public. As people use it, they hit bugs and form
opinions, but there is no easy path from "that broke / I wish it did X" to a
tracked, triageable GitHub issue. Two hard constraints shape the solution:

1. **Per-user identity.** Each user's issue must be created under *their* GitHub
   account — never the maintainer's. That rules out any baked-in token or
   maintainer-operated service.
2. **Public + privacy.** Feedback can contain machine-local paths, secrets, or
   project content, and the destination is a *public* issue under the user's
   real name. Anything filed must be sanitized and shown to the user first.

## Goal

From inside normal use, a user can run one command and, with a single
confirmation, file a clean, well-structured issue (or upvote an existing one)
on `AaronLPS/loop-builder` as themselves — with zero servers and zero tokens
owned by the project.

## Decisions (locked during brainstorm)

- **Scope:** feedback about both loop-builder itself *and* the loops it
  generates.
- **Capture model:** passive logging during use + an explicit
  `/loop-builder-feedback` command to review and file. No silent filing.
- **Filing path:** use the user's own `gh` CLI if authenticated; otherwise fall
  back to a prefilled browser "new issue" URL. Both create the issue under the
  user's identity.
- **Packaging (Approach A):** a companion skill orchestrates; deterministic work
  (sanitize, dedupe, file) lives in bundled `python3` scripts that are
  red-green tested. Rejected: pure-prompt (non-deterministic sanitization) and
  an external aggregator bot (violates per-user identity).
- **Language:** `python3` for the core scripts (JSONL + URL-encoding +
  redaction); thin bash wrappers only if needed.
- **Dedupe source (v1):** live GitHub issues only. A curated `KNOWN-ISSUES.md`
  is deferred (YAGNI) until live dedupe proves insufficient.

## Architecture

### Units (single responsibility, independently testable)

| Unit | Responsibility | Depends on | Form |
| --- | --- | --- | --- |
| `feedback-log` | append / read / mark-filed feedback entries | local file | pure file ops (python3) |
| `sanitize` | redact local paths, secrets, emails from issue text | none | deterministic; fixture-tested |
| `dedupe` | match a draft against live issues | GitHub read-only API | testable with mock issue lists |
| `file-issue` | create the issue as the user (gh, else URL) | user's gh / browser | dry-run testable |
| `/loop-builder-feedback` skill | orchestrate + summarize entries into human-readable drafts | the four units above | skill (judgment) |

Deterministic, security-relevant, testable work goes in scripts; the
human-language summarization goes in the skill. This mirrors loop-builder's own
durable-vs-changing philosophy.

### Data flow

```
 use loop-builder / run a generated loop
        │  (passive: errors, verifier crash, user frustration)   ┌─ /loop-builder-feedback (explicit)
        ▼                                                        ▼
   append one entry ──►  ~/.loop-builder/feedback.jsonl  (gitignored, local, per-user)
                              │
        /loop-builder-feedback│ review
                              ▼
                  summarize + cluster into 1..N candidate issues (skill)
                              ▼
                  dedupe ◄── gh issue list / GitHub search API (public repo, unauth read)
                              ▼
                  sanitize  (bundled script: paths / secrets / emails)        <- red line
                              ▼
        show final issue + "will be filed as YOUR GitHub account" -> confirm?  <- consent gate
                              ▼
          gh authed? ── yes ─► gh issue create --repo AaronLPS/loop-builder
                    └─ no  ──► prefilled new-issue URL (open browser)
                              ▼
                  mark entries filed (#issue) in the log
```

### Local feedback log (state file)

- Location `~/.loop-builder/feedback.jsonl` — per-user, cross-session,
  independent of the working directory. **Gitignored, never committed.**
- One JSON object per line:
  `{ts, source: "loop-builder" | "<loop-name>", category: "bug"|"feedback"|"idea",
  text, context?: {action, error_excerpt, env}, status: "open"|"filed",
  issue?: 42, schema: 1}`.
- Honors loop-builder's rule: changing state lives in an external file, never in
  a `SKILL.md`.

### Capture

- **Passive:** during a loop-builder session, on a detected error (script
  failure, self-contradiction, clear user frustration) the skill appends one
  entry — quietly, without interrupting the task. Generated loops that opted in
  append runtime failures the same way, tagged with the loop name as `source`.
- **Explicit:** `/loop-builder-feedback` appends the user's report and enters the
  review-and-file flow. With no argument it reviews the existing backlog.

### Summarize + dedupe

- The skill reads unfiled entries, clusters them into candidate issues, and
  drafts each: title, what happened, repro/context, environment (Claude Code
  version, OS, loop-builder version), category/labels.
- Dedupe queries existing issues (unauthenticated read is sufficient for a public
  repo). On a likely match it tells the user "looks like #42 (open)" and offers
  to upvote/comment instead of opening a duplicate. If the query fails
  (rate-limit/offline) it proceeds but warns that dedupe was skipped.

### Sanitize + consent gate (privacy red line)

- Before any content leaves the machine, the bundled sanitizer rewrites the draft
  body: `/home/<user>/` and `/Users/<user>/` collapse to `~`; gitleaks-style
  secret patterns are redacted; emails are flagged. Deterministic and
  fixture-tested, reusing the patterns established by the repo's existing
  secret-scanning work.
- The skill then shows the user the exact final issue (title, body, labels,
  target repo, and "this will be filed as YOUR GitHub account") and requires
  explicit confirmation. Filing is never automatic.

### File issue (per-user identity)

- If `gh auth status` succeeds:
  `gh issue create --repo AaronLPS/loop-builder --title <t> --body-file <f>
  --label via-feedback-tool,<category>` — created as the user.
- Otherwise build a prefilled URL
  `https://github.com/AaronLPS/loop-builder/issues/new?title=...&body=...&labels=...`
  (URL-encoded; if it exceeds ~8KB, truncate with a note and print the full body
  to the terminal for paste) and open the browser; the user submits as
  themselves.
- On success, write back `status: filed, issue: N` for the contributing entries.
- The project owns no token and operates no server in either path — this is what
  makes the per-user-identity constraint hold.

### Generated-loop integration (opt-in per loop)

- When loop-builder scaffolds a loop it offers: "add self-reporting? (the loop
  logs its own errors locally for you to review with /loop-builder-feedback)".
- If accepted, it scaffolds a small hook in the loop's verifier/wrapper that
  appends failures to `~/.loop-builder/feedback.jsonl` tagged with the loop name.
  Purely local; never auto-files; still goes through the same human review flow.

### Repo side (maintainer)

- `.github/ISSUE_TEMPLATE/bug_report.yml` and `feedback.yml` (GitHub issue forms)
  so browser-URL, gh, and manual submissions are all consistent and triageable;
  prefilled content aligns with the template fields.
- Labels: `via-feedback-tool`, `bug`, `feedback`, `loop-runtime`.

## Error handling

- No gh and no browser: print the URL plus the full markdown body for manual
  paste.
- URL too long: truncate with a "(truncated — full body printed below)" note and
  print the full body.
- gh auth missing/expired: fall back to the URL path and say so.
- Offline: leave entries in the log and retry next invocation.
- Sanitizer hits a secret: redact and warn prominently in the review.
- Dedupe query fails: proceed, warn that duplicate-checking was skipped.

## Testing

- Sanitizer fixtures: inputs containing local paths, secrets, and emails assert
  the redacted output (red-green, like `scripts/tests/`).
- `file-issue` dry-run: no network; prints the exact `gh` command or the URL it
  would open.
- Dedupe: matching against a canned issue list (mocked), including the
  no-match and query-failure cases.
- `feedback-log`: append/read/mark-filed round-trips.
- Wired into the existing `scripts/tests/` convention and CI.

## Scope (v1)

- `feedback-log`, `sanitize`, `dedupe`, `file-issue` python3 scripts + tests.
- `/loop-builder-feedback` companion skill (capture, review, summarize, file).
- Passive capture inside loop-builder for its own errors.
- Opt-in self-reporting hook scaffolded into generated loops.
- `.github/ISSUE_TEMPLATE/` issue forms + labels.

## Non-goals / risks

- **Non-goal:** any maintainer-operated server, bot, or shared token; cross-user
  aggregation/analytics; auto-filing without confirmation.
- **Non-goal (deferred):** `KNOWN-ISSUES.md` curated list; rely on live dedupe
  for v1.
- **Risk:** sanitization is best-effort, not a guarantee — the consent gate
  (user sees the final body) is the real backstop, and must never be skippable.
- **Risk:** unauthenticated GitHub reads are rate-limited; dedupe degrades
  gracefully rather than blocking a filing.
- **Risk:** product mechanics for hooking into generated loops depend on the
  loop runtime; keep the hook minimal and mark any uncertain mechanic for
  verification against current docs, consistent with loop-builder's standing
  uncertainty flag.
