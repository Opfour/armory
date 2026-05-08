# Handoff Schema

Every generated handoff uses this schema exactly, at `.docs/handoff.md`.

```markdown
# Handoff — <project name>

**Last touched:** <ISO 8601 timestamp with timezone> · **branch:** `<branch>` · **HEAD:** `<short-sha>` · **session:** <model id>

> Authority: this file owns *transient session state*. Persistent facts live in `~/.claude/projects/<project>/memory/`. Static setup lives in `CLAUDE.md`. Strategic
roadmap lives in `~/.claude/plans/<plan>.md`. Committed history lives in `git log`.

## Status
- Working tree: <N modified, M untracked, K staged> (`<top 3-5 paths>`)
- Tests: <last command> → <pass/fail counts, named failures>
- Lint/type: <ruff/mypy/eslint/tsc state>
- Last verified: <command + timestamp>

## What changed this session
- <bullet per logical change; reference SHAs for commits, paths for uncommitted work>

## Decisions
1. **<decision title>** (<date>) — <rationale, ≤2 sentences>

## Blockers / open questions
- [ ] <unresolved item, with enough context to resume cold>

## Resume checklist
1. <first verification step — usually `git status` to confirm tree matches Status>
2. <second step — usually re-run last test command to confirm same state>
3. <third step — point at the specific file:line where work stopped>
4. <fourth step — flag the next decision to make, if any>

## Refs
- Plan: `<path or "—">`
- Related PRs: <numbers or "—">
- Memory: `<files or "—">`
- Conversation: <searchat query or "—">
```

## Line Budget

The hard cap is 200 lines.

Header and section overhead is approximately 25 lines. The remaining budget belongs to content. If generated content exceeds 200 lines, truncate `## What changed this session` oldest-first and insert:

```markdown
<!-- WARNING: handoff exceeded 200 lines; oldest session changes were truncated. -->
```

Preserve every schema heading even when content must be compressed.

