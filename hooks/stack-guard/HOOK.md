---
name: stack-guard
type: hook
description: 'PreToolUse Bash hook that adds stacked-PR-specific safety checks. Triggers on: "stack guard", "stacked PR safety hook", "block git push --force", "warn wrong stack base", "protect stacked branches", "stack workflow hook". Use this hook with stacked-prs workflows to block plain force pushes, allow force-with-lease, and warn when commands appear to violate `.stack-prs.yaml` branch topology.'
metadata:
  version: 0.1.0
  category: operations
  tags: [git, stacked-prs, hooks, safety]
  difficulty: intermediate
  phase: ship
hook:
  events: [PreToolUse]
  matcher: Bash
  handler: {type: command, command: bash handler.sh, timeout_ms: 5000}
---

# Stack Guard

Adds conservative safety checks for stacked PR workflows. It complements `git-protection` by focusing on stack topology instead of generic destructive Git commands.

## Workflow

1. Read the Bash command from the PreToolUse hook payload.
2. Block plain `git push --force` and `git push -f`.
3. Allow `git push --force-with-lease`.
4. When `.stack-prs.yaml` exists, inspect declared branch parents.
5. Warn when a PR creation command targets a base that conflicts with metadata.
6. Warn when pushing a child while its declared parent has unpushed commits.
7. Warn before PR merge commands in repos with stack metadata so the agent verifies parent-first merge order.

## Behavior

| Operation | Result | Reason |
| --- | --- | --- |
| `git push --force origin branch` | Block | Plain force can overwrite collaborator work |
| `git push -f origin branch` | Block | Short force flag has the same risk |
| `git push --force-with-lease origin branch` | Allow | Lease protects against unseen remote changes |
| `gh pr create --base main --head child` with metadata parent `parent` | Warn | Review diff would include unrelated parent changes |
| `git push origin child` while `parent` has unpushed commits | Warn | Remote child can reference parent commits not available remotely |
| `gh pr merge <number>` with stack metadata | Warn | Merge order must be parent-first |

## Metadata Scope

The hook reads the straightforward `.stack-prs.yaml` shape documented by `skills/stacked-prs`:

```yaml
base: main
branches:
  - name: feat/parser-core
    parent: main
  - name: feat/parser-cache
    parent: feat/parser-core
```

If the file is absent, only force-push protection runs.

## Output

- Blocked commands write a `BLOCKED:` diagnostic to stderr and exit non-zero.
- Topology concerns write a `WARNING:` diagnostic to stderr and exit 0.
- Safe commands exit 0 without output.

## Error Handling

| Problem | Resolution |
| --- | --- |
| Hook payload lacks a Bash command | Exit 0 |
| `.stack-prs.yaml` absent | Run force-push protection only |
| Metadata branch is not found locally | Warn only on commands that can be checked from command text |
| Parent remote ref is absent | Warn that parent has no remote ref |

