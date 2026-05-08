---
name: handoff
type: command
description: 'Slash-command wrapper for the handoff skill. `/handoff` refreshes `.docs/handoff.md`; `/handoff init` scaffolds the schema in greenfield projects; both preserve the 200-line cap and authority boundary. Triggers on: "/handoff", "/handoff init", "update handoff", "refresh handoff", "session handoff", "create handoff", "resume checklist". Use this command when pausing, ending, transferring, or resuming in-flight coding work across agent sessions.'
metadata:
  version: 0.1.0
  category: development
  tags: [handoff, slash-command, session-continuity, runbook]
  difficulty: intermediate
  phase: ship
command:
  syntax: /handoff [init]
  handler: inline
  dependencies:
    - skills/handoff
---

# Handoff Command

Thin slash-command entry point for the `handoff` skill.

## Workflow

1. `/handoff` invokes the handoff skill in refresh mode.
2. `/handoff init` invokes the handoff skill in scaffold mode.
3. The command writes only `.docs/handoff.md`.
4. The command preserves the schema, authority boundary, and 200-line hard cap.

## Operations

| Command | Output | Use |
| --- | --- | --- |
| `/handoff` | Full rewrite of `.docs/handoff.md` | End or pause a session |
| `/handoff init` | Empty schema scaffold if absent | Project initialization |

## Output

The command delegates to:

```bash
uv run skills/handoff/scripts/handoff.py --project-root "$PWD"
uv run skills/handoff/scripts/handoff.py --project-root "$PWD" --init
```

## Error Handling

| Problem | Resolution |
| --- | --- |
| Not in a git repository | Report the git error unless running `init` |
| `.docs/` missing | Create it |
| Existing handoff absent during refresh | Create a populated file rather than failing |
| Existing handoff present during init | Leave it untouched |

