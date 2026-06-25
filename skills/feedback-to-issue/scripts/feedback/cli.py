"""Command-line surface over the feedback modules, called by the
loop-builder-feedback playbook. Each subcommand prints JSON to stdout.

This CLI never confirms a filing on the user's behalf: `file` just performs the
action it is told to. The mandatory consent gate lives in the orchestrating
skill (see references/feedback-to-issue.md).
"""
from __future__ import annotations

import argparse
import json
import sys

import dedupe
import feedback_log
import file_issue
import sanitize as sanitize_mod


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="feedback")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append")
    a.add_argument("--category", required=True)
    a.add_argument("--text", required=True)
    a.add_argument("--source", default="loop-builder")

    sub.add_parser("list-open")

    m = sub.add_parser("mark-filed")
    m.add_argument("--ids", required=True)
    m.add_argument("--issue", required=True, type=int)

    sub.add_parser("sanitize")

    d = sub.add_parser("dedupe")
    d.add_argument("--repo", required=True)
    d.add_argument("--title", required=True)

    f = sub.add_parser("file")
    f.add_argument("--repo", required=True)
    f.add_argument("--title", required=True)
    f.add_argument("--labels", default="")
    f.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "append":
        entry = feedback_log.append(args.category, args.text, source=args.source)
        print(json.dumps(entry, ensure_ascii=False))
    elif args.cmd == "list-open":
        print(json.dumps(feedback_log.list_open(), ensure_ascii=False))
    elif args.cmd == "mark-filed":
        n = feedback_log.mark_filed(args.ids.split(","), args.issue)
        print(json.dumps({"updated": n}))
    elif args.cmd == "sanitize":
        text, notes = sanitize_mod.sanitize(sys.stdin.read())
        print(json.dumps({"text": text, "notes": notes}, ensure_ascii=False))
    elif args.cmd == "dedupe":
        issues = dedupe.fetch_open_issues(args.repo)
        print(json.dumps(dedupe.match(args.title, issues), ensure_ascii=False))
    elif args.cmd == "file":
        labels = [x for x in args.labels.split(",") if x]
        res = file_issue.create(args.repo, args.title, sys.stdin.read(), labels,
                                dry_run=args.dry_run)
        print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
