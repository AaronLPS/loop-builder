# skill-bank — recommended (curated standouts)

A curated catalog of proven external skills/plugins/workflows worth borrowing when
building a loop. Pointers only — nothing here is vendored. Each entry is tagged by the
loop block it can serve: (1) scheduling, (2) isolation, (3) skill/conventions,
(4) connectors, (5) verifier, (6) state. Borrow by recommend-and-record: cite the
source + install pointer + a named fallback; never inline external code. Sources and
the refresh procedure live in `sources.yml`. This file is the **curated standouts** —
the entries the skill-bank search sub-agent prefers. It is not loaded directly each
build; in Phase 1.5 loop-builder dispatches a searcher (see
`references/skill-bank/search-agent.md`) that reads this file plus the comprehensive
`catalog/<source>.md` listings and returns the best-fit shortlist.

| name | type | blocks | purpose | source | install | license | synced |
|------|------|--------|---------|--------|---------|---------|--------|
| superpowers:test-driven-development | skill | 5 | red-green TDD discipline usable as a loop's verifier rubric | https://github.com/obra/superpowers | clone into ~/.claude/skills/ | MIT | obra/superpowers@main 2026-06-19 |
| superpowers:brainstorming | workflow | 3 | structured design dialogue for shaping a loop's conventions | https://github.com/obra/superpowers | clone into ~/.claude/skills/ | MIT | obra/superpowers@main 2026-06-19 |
| superpowers:writing-plans | skill | 3 | structured plan-authoring conventions applicable to loop phase design | https://github.com/obra/superpowers | clone into ~/.claude/skills/ | MIT | obra/superpowers@main 2026-06-19 |
| superpowers:using-git-worktrees | skill | 2 | safely create isolated git worktrees for loop isolation steps | https://github.com/obra/superpowers | clone into ~/.claude/skills/ | MIT | obra/superpowers@main 2026-06-19 |
| ecc:verification-loop | skill | 5 | build-test-lint-typecheck-security gate usable as a loop's exit criterion | https://github.com/affaan-m/ecc | clone into ~/.claude/skills/ | MIT | affaan-m/ecc@main 2026-06-19 |
| ecc:autonomous-loops | workflow | 1,3 | sequential pipeline and DAG orchestration patterns for self-running loops | https://github.com/affaan-m/ecc | clone into ~/.claude/skills/ | MIT | affaan-m/ecc@main 2026-06-19 |
| ecc:coding-standards | skill | 3 | language best-practice conventions to embed in a loop's skill layer | https://github.com/affaan-m/ecc | clone into ~/.claude/skills/ | MIT | affaan-m/ecc@main 2026-06-19 |
| ecc:strategic-compact | skill | 6 | context-management checkpoints that preserve loop state across sessions | https://github.com/affaan-m/ecc | clone into ~/.claude/skills/ | MIT | affaan-m/ecc@main 2026-06-19 |
| awesome-claude-skills:playwright-skill | skill | 5 | model-invoked Playwright browser automation for loop acceptance testing | https://github.com/lackeyjb/playwright-skill | clone into ~/.claude/skills/ | MIT | ComposioHQ/awesome-claude-skills@main 2026-06-19 |
| awesome-claude-skills:connect | plugin | 4 | Composio bridge connecting a loop to 500+ SaaS apps as connectors | https://github.com/ComposioHQ/awesome-claude-skills | follow install instructions in skill folder | Apache-2.0 | ComposioHQ/awesome-claude-skills@main 2026-06-19 |
| awesome-claude-skills:mcp-builder | skill | 4 | guided MCP server creation for adding custom connectors to a loop | https://github.com/ComposioHQ/awesome-claude-skills | follow install instructions in skill folder | Apache-2.0 | ComposioHQ/awesome-claude-skills@main 2026-06-19 |
| gstack:ship | workflow | 5 | test-sync + audit + PR creation pipeline usable as a loop's release verifier | https://github.com/garrytan/gstack | clone repo and add skill dir to CLAUDE.md | MIT | garrytan/gstack@main 2026-06-19 |
| gstack:investigate | skill | 5 | systematic root-cause debugging workflow for diagnosing loop failures | https://github.com/garrytan/gstack | clone repo and add skill dir to CLAUDE.md | MIT | garrytan/gstack@main 2026-06-19 |
| gstack:review | skill | 3 | staff-engineer code review with auto-fix for loop convention enforcement | https://github.com/garrytan/gstack | clone repo and add skill dir to CLAUDE.md | MIT | garrytan/gstack@main 2026-06-19 |
| claude-for-legal:ip-legal | plugin | 3,4 | IP trademark/patent/copyright triage and portfolio management plugin suite | https://github.com/anthropics/claude-for-legal | clone repo and load plugin via .claude-plugin manifest | Apache-2.0 | anthropics/claude-for-legal@main 2026-06-19 |
| claude-for-legal:commercial-legal | plugin | 3,4 | contract review and renewal-tracking plugin for loops operating on agreements | https://github.com/anthropics/claude-for-legal | clone repo and load plugin via .claude-plugin manifest | Apache-2.0 | anthropics/claude-for-legal@main 2026-06-19 |
