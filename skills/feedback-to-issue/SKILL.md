---
name: feedback-to-issue
description: >-
  Capture, review, and file a bug report or feedback as a GitHub issue under the
  user's OWN account. Use whenever the user wants to report a bug, give feedback,
  file an issue, or review collected feedback about loop-builder or a loop it
  generated. Sanitizes private content and requires explicit consent before any
  public issue is filed.
---

# Feedback to Issue

Capture feedback locally, then — only on the user's explicit yes — file a clean,
sanitized GitHub issue under the user's own account (via their `gh` session, or a
prefilled browser URL). Nothing is auto-filed.

The full step-by-step flow, guarantees, sanitization rules, dedupe, consent gate,
and the generated-loop opt-in hook live in the reference. Load it on demand:

- `references/feedback-to-issue.md` — the complete playbook (capture → list-open →
  cluster → draft → dedupe → sanitize → **mandatory consent gate** → file →
  mark-filed), plus the maintainer label setup and the generated-loop hook snippet.

Bundled deterministic tooling lives in `scripts/feedback/` (red-green tested under
`scripts/tests/`). Invoke it with `python3 scripts/feedback/cli.py <subcommand>`.
