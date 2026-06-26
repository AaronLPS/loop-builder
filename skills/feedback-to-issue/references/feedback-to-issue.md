# Feedback to Issue: Capture, Review, and File

> Load this reference when the user asks to report a bug, give feedback, or review
> collected feedback. It is not read during normal loop-building; its passive-capture
> rule is the only part a generated loop needs inline (as a hook snippet, below).

---

## Purpose and guarantees

Feedback collected by loop-builder stays **local only** until you explicitly choose
to file it. Three guarantees hold unconditionally:

1. **Filed under your account.** Any GitHub issue is filed using your own
   authenticated `gh` session, or, if `gh` is not available, via a prefilled URL
   opened in your browser — never through a shared or anonymous account.
2. **Nothing is auto-filed.** No entry goes to GitHub without an explicit "yes" from
   you at the consent gate described below.
3. **Every draft is sanitized and shown in full** before you are asked to confirm.
   You see the exact title, body, and labels before any action is taken.

---

## Passive capture

When loop-builder hits an error, or when you are clearly blocked and the cause is
worth recording, append a quiet entry to the local log:

```bash
python3 scripts/feedback/cli.py append \
  --category bug \
  --text "<what broke and brief context>"
```

For a generated loop appending its own failure (see the opt-in hook below), add
`--source <loop-name>` so the entry is traceable back to the loop:

```bash
python3 scripts/feedback/cli.py append \
  --category bug \
  --source <loop-name> \
  --text "<what broke and brief context>"
```

Passive capture is intentionally low-friction: one command, no network calls, no
prompts. The entry lands in `~/.loop-builder/feedback.jsonl` (or the path set by
`LOOP_BUILDER_FEEDBACK_FILE`) and waits for a review session.

---

## Review and file flow

Triggered when the user says: "report a bug," "give feedback," "review my feedback,"
or anything equivalent. Work through the steps below in order — do not skip or
reorder them.

### Step 1 — Load the backlog

```bash
python3 scripts/feedback/cli.py list-open
```

This returns all entries with `status == "open"`. Read the list, identify entries
that belong together (same root cause, same broken flow), and cluster them into one
or more candidate issues. Each cluster becomes one draft.

### Step 2 — Draft each candidate issue

For each cluster, write:

- **Title** — one sentence: what broke or what is missing. Concrete and searchable;
  avoid vague terms like "problem" or "error."
- **Body** — three parts:
  1. What happened (the symptom, with relevant log lines or output from the entries).
  2. Repro / context (the loop name, the command that failed, the state at the time).
  3. Environment (OS, Claude Code version if known, any relevant config).
- **Labels** — always include `via-feedback-tool` plus the entry's category (`bug`,
  `feedback`, or `idea`). Separate with commas. Labels such as `enhancement` are
  freeform GitHub labels you may add, but they are not valid `--category` values.

### Step 3 — Deduplicate

Before filing, check whether a matching issue already exists:

```bash
python3 scripts/feedback/cli.py dedupe \
  --repo AaronLPS/loop-builder \
  --title "<draft title>"
```

The command returns a list of open issues ranked by similarity. If a strong match
appears (same symptom, same context), offer the user two options instead of filing
a new issue:

- Upvote or add a comment to the existing issue (link them to it).
- Proceed to file a new issue if theirs is genuinely distinct.

If no strong match exists, proceed to the next step.

### Step 4 — Sanitize the body

Write the draft body to a temporary file (`body.md`) first — issue bodies are
multi-line markdown and shell-quoting with `echo` mangles them. Then run the
sanitizer:

```bash
# Write the draft to a temp file
cat > body.md <<'EOF'
<your draft body here>
EOF
```

Pass that file through `sanitize` to catch local paths, email addresses, API
keys, or other private content before it leaves the machine:

```bash
python3 scripts/feedback/cli.py sanitize < body.md
```

The command returns `{"text": "<cleaned body>", "notes": [...]}`. Surface any
`notes` to the user — these are the specific items the sanitizer flagged or
redacted. The user decides whether the redaction is correct or whether the draft
needs manual editing before proceeding.

### Step 5 — Consent gate (mandatory; never skip)

Show the user **everything** that will be filed, verbatim:

```
Title:   <sanitized title>
Body:
  <sanitized body>
Labels:  via-feedback-tool, <category>
Repo:    AaronLPS/loop-builder
Account: your GitHub account (via gh / browser)
```

Then ask: "File this issue? (yes / no / edit first)"

**Do not proceed without an explicit yes.** If the user says "edit first," return to
drafting. If the user says no, drop the draft and ask whether to keep the entries
open or discard them.

### Step 6 — File the issue

On explicit yes:

```bash
python3 scripts/feedback/cli.py file \
  --repo AaronLPS/loop-builder \
  --title "<sanitized title>" \
  --labels via-feedback-tool,<category> < body.md
```

The command returns a JSON result. Two outcomes:

- `"method": "gh"` — the issue was filed via the `gh` CLI. Report the issue number
  (`result.issue`) to the user so they can follow up.
- `"method": "url"` — `gh` is not available or not authenticated. A prefilled URL
  was opened in the user's browser. Tell the user to review the prefilled form and
  click Submit themselves.

### Step 7 — Mark entries as filed

Once the issue exists (either path above), mark the source entries so they no longer
appear in `list-open`:

```bash
python3 scripts/feedback/cli.py mark-filed \
  --ids <comma-separated entry ids> \
  --issue <issue number>
```

This closes the loop: future `list-open` calls return a clean backlog.

---

## Generated-loop opt-in hook

When scaffolding a loop, ask: "Add self-reporting to this loop? (logs its own errors
locally for you to review later — never auto-files)"

If the user opts in, add the following snippet to the loop's verifier or wrapper
script. It runs after the verifier exits non-zero and appends the failure locally;
it never opens a network connection or files anything:

```bash
# loop self-report (local only; review/file later with loop-builder feedback)
python3 "$LOOP_BUILDER_SCRIPTS/cli.py" append --category bug \
  --source "<loop-name>" --text "verifier failed: $(tail -n 3 "$VERIFIER_LOG")" || true
```

Variables the loop must define before calling this snippet:

- `LOOP_BUILDER_SCRIPTS` — absolute path to this skill's `scripts/feedback/`
  directory, i.e. `${CLAUDE_PLUGIN_ROOT}/skills/feedback-to-issue/scripts/feedback`,
  resolved at scaffold time and baked into the generated loop.
- `VERIFIER_LOG` — path to the log file the verifier writes each run.
- `<loop-name>` — the loop's own name (literal, substituted at scaffold time).

The `|| true` guard keeps the hook from breaking a verifier failure path where
the exit code matters. The hook appends silently if it succeeds and silently
discards its own failure if it cannot write the log.

---

## Quick reference

| Step | Command | When |
|------|---------|------|
| Capture a local entry | `cli.py append --category <cat> --text "..."` | on error / blockage |
| Load the backlog | `cli.py list-open` | start of review session |
| Check for duplicates | `cli.py dedupe --repo ... --title "..."` | after drafting, before filing |
| Sanitize the body | `cli.py sanitize < body.md` | before showing consent gate |
| File the issue | `cli.py file --repo ... --title "..." --labels ... < body.md` | after explicit yes |
| Mark entries filed | `cli.py mark-filed --ids ... --issue <N>` | after successful file |

---

## Maintainer setup

For the `gh` filing path to work, the following labels must exist in the repo
(created once; `gh issue create` errors on unknown labels):

```bash
gh label create via-feedback-tool --description "filed via the feedback tool"
gh label create bug --description "something is broken"
gh label create feedback --description "general feedback"
gh label create idea --description "feature request or idea"
```

Run these once against the target repo after initial setup.
