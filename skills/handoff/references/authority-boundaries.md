# Authority Boundaries

`.docs/handoff.md` owns transient session state: the current branch, uncommitted or in-flight work, decisions made in the active session, immediate blockers, validation state, and resume steps.

It does not own durable project knowledge.

| Surface | Owns | Does not own |
| --- | --- | --- |
| `.docs/handoff.md` | Session cursor, local working state, blockers, next commands | Long-lived architecture facts, installation docs, committed history |
| `~/.claude/projects/<project>/memory/` | Persistent cross-conversation facts and preferences | Current uncommitted working-tree details |
| `CLAUDE.md` | Static project setup, repo conventions, stable commands | Temporary blockers or half-finished edits |
| `~/.claude/plans/<plan>.md` | Strategic roadmap and multi-session plan | The current cursor inside the roadmap |
| `git log` | Committed history and PR-ready narrative | Uncommitted work, failed attempts, session-local choices |

Promote information out of handoff when it becomes durable:

- Stable setup instruction → `CLAUDE.md`
- Durable architectural decision → memory or ADR
- Completed committed work → commit message, changelog, or PR description
- Multi-session roadmap item → plan file

Agent-agnostic rule: write for any coding agent or human who can read Markdown and run shell commands. Avoid tool-specific assumptions unless they are explicit refs.

