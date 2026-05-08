---
name: handoff-on-stop
type: hook
trigger: stop
description: 'Refreshes `.docs/handoff.md` on session Stop when a project has opted in by already having that file. Invokes the handoff skill silently, logs failures, and continues without blocking shutdown. Triggers on: "handoff on stop", "session end handoff", "auto refresh handoff", "Stop hook", "session continuity hook", "save context on stop". Use this hook when projects need automatic session-continuity updates at the end of coding-agent sessions without creating handoff files everywhere.'
metadata:
  version: 0.1.0
  category: operations
  tags: [handoff, session-continuity, stop-hook, runbook]
  difficulty: intermediate
  phase: ship
hook:
  events: [Stop]
  matcher: ""
  handler: { type: command, command: bash handler.sh, timeout_ms: 10000 }
---

# Handoff On Stop

Refreshes `.docs/handoff.md` at the end of a session for projects that have explicitly opted in.

## Workflow

1. On `Stop`, check the current working directory for `.docs/handoff.md`.
2. If the file is absent, exit 0 with no output.
3. If present, invoke the `handoff` skill behavior silently.
4. If refresh fails, append a diagnostic to `.docs/handoff.log` and exit 0.

## Output

No user-visible output on success or no-op. Failures are logged and do not block the Stop event.

## Error Handling

| Failure | Behavior |
| --- | --- |
| `.docs/handoff.md` absent | No-op, exit 0 |
| Generator script missing | Log and exit 0 |
| Git command failure | Log and exit 0 |
| Write failure | Log and exit 0 |

## Idempotency

The hook performs a full rewrite through the handoff generator. Repeated Stop events update timestamp and state without appending duplicate sections.

