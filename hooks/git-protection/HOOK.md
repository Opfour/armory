---
name: git-protection
type: hook
description: >
  Blocks dangerous git operations that can cause irreversible data loss. Intercepts
  Bash tool invocations before execution and inspects the command string for destructive
  patterns: force-push (push --force / push -f), hard reset (reset --hard), deletion of
  main/master branches (branch -D main/master), and aggressive clean (clean -fd). Use
  this hook when working in repositories where accidental destructive git commands could
  wipe uncommitted work or rewrite shared history.
metadata:
  version: 1.0.0
hook:
  events:
    - PreToolUse
  matcher: "Bash"
  handler:
    type: command
    command: "bash handler.sh"
    timeout_ms: 5000
---

# git-protection

Prevents destructive git operations from executing through Claude Code.

## Blocked Operations

| Pattern | Risk |
|---------|------|
| `git push --force` / `git push -f` | Rewrites remote history, destroys collaborators' work |
| `git reset --hard` | Discards all uncommitted changes permanently |
| `git branch -D main` / `git branch -D master` | Deletes the primary branch |
| `git clean -fd` | Removes untracked files and directories permanently |

## Behavior

The hook reads the tool input JSON from stdin, extracts the `command` field, and
checks it against the blocked patterns. If a match is found, the hook exits with
code 1 and prints a diagnostic message explaining which operation was blocked and
why.

Commands that do not match any blocked pattern pass through (exit 0).

## Bypassing

Remove or disable this hook in your `settings.json` if you need to run these
commands intentionally. The hook is a safety net, not a policy enforcer.
