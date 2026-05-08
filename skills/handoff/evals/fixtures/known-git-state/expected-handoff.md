# Handoff — known-git-state

**Last touched:** <timestamp> · **branch:** `<branch>` · **HEAD:** `<short-sha>` · **session:** <model id>

> Authority: this file owns *transient session state*. Persistent facts live in `~/.claude/projects/<project>/memory/`. Static setup lives in `CLAUDE.md`. Strategic
roadmap lives in `~/.claude/plans/<plan>.md`. Committed history lives in `git log`.

## Status
- Working tree: <counts> (`<top paths>`)
- Tests: uv run pytest tests/test_session.py -q → 12 passed
- Lint/type: uv run pytest tests/test_session.py -q → 12 passed
- Last verified: uv run pytest tests/test_session.py -q → 12 passed @ <timestamp>

## What changed this session
- Updated `src/session.py` to preserve failed approach context for the next agent.
- Added `.docs/handoff.last-validation` as a project-local validation marker.

## Decisions
1. **Use lowercase path** (2026-05-08) — `.docs/handoff.md` is the canonical per-project path across agents.

## Blockers / open questions
- [ ] Confirm the next validation command after rebasing the branch.

## Resume checklist
1. Run `git status` and confirm the tree matches the Status section.
2. Re-run the last recorded validation command or establish one if not recorded.
3. Open the first changed path listed above and inspect where work stopped.
4. Resolve the top blocker or make the next recorded decision.

## Refs
- Plan: `—`
- Related PRs: —
- Memory: `—`
- Conversation: searchat query: session handoff lowercase path

