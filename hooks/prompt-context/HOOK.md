---
name: prompt-context
type: hook
description:
  "Injects a text file into every prompt as additionalContext via the UserPromptSubmit
  event. Reads from project-level .claude/prompt-context.txt first, falling back to
  ~/.claude/prompt-context.txt. Fail-open: missing or unreadable files exit 0 silently
  rather than blocking input. Use this hook to enforce output styles, inject project
  reminders, prime roles, or apply constraints that survive context compaction — the
  injection lands adjacent to the user prompt on every turn, the highest-attention
  slot in the context window. Triggers on: inject prompt context, persistent
  instructions, system prompt injection, context injection hook, output style hook.

  "
metadata:
  version: 1.0.0
  category: operations
  tags: [context, prompt, style, injection, compaction-immune]
  difficulty: beginner
hook:
  events: [UserPromptSubmit]
  matcher: ""
  handler: { type: command, command: bash handler.sh, timeout_ms: 5000 }
---

# prompt-context

Injects a text file into every user prompt as `additionalContext`.

## Why This Hook Exists

Claude Code offers several mechanisms for persistent instructions — `CLAUDE.md`,
`outputStyle`, `--append-system-prompt` — but each has structural limitations:

| Mechanism                | Limitation                                                   |
| ------------------------ | ------------------------------------------------------------ |
| `CLAUDE.md`              | Loaded at session start; drifts out of attention by turn 30+ |
| `outputStyle`            | System-prompt-level; models sometimes second-guess it        |
| `--append-system-prompt` | Single slot; conflicts with other wrappers                   |
| Compact Instructions     | Survives `/compact` but still competes with conversation     |

A `UserPromptSubmit` hook re-fires on every turn. Its output lands immediately
adjacent to the user's request — the highest-attention position in the context
window. Rules injected here are compaction-immune and recency-biased.

## File Lookup Order

The hook checks two locations and uses the first file found:

1. **Project-level:** `.claude/prompt-context.txt` (relative to working directory)
2. **Global:** `~/.claude/prompt-context.txt`

This enables per-project overrides while maintaining a global default.

## Fail-Open Design

If neither file exists or the file is unreadable, the hook exits 0 with no
output. This prevents a missing or corrupted rules file from blocking user
input.

## Example Content

A `prompt-context.txt` for terse output enforcement:

```text
Apply to your next response:
- No preamble, no postamble, no narration
- Strip hedging (think/perhaps/might/maybe/seems/likely/probably)
- Strip praise (great/perfect/excellent/amazing/fantastic)
- Strip soft language (would you like, if you'd prefer, you may want)
- Strip meta-commentary (let's, now we'll, moving on, next, first)
- Strip engagement (feel free, let me know, hope this helps, happy to)
- Strip terminal questions unless the user explicitly asked one
- After tool calls, stop. Do not summarize what just happened.
- Code over prose. Facts over hedging. Stop at the information boundary.
```

Other use cases:

- **Role priming:** "You are reviewing code as a security auditor. Flag OWASP Top 10 patterns."
- **Project reminders:** "This repo uses pnpm. Never suggest npm install."
- **Output constraints:** "All responses must include file:line references."

## Subagent Limitation

Subagents (Explore, Plan, code-reviewer, etc.) have isolated contexts and do
not fire `UserPromptSubmit`. To cover subagent output, pair this hook with
an `outputStyle` setting:

```json
{
  "outputStyle": "concise"
}
```

The hook handles main-agent output; the output style handles subagent output.

## Modifying Rules

Edit the `prompt-context.txt` file. Changes take effect on the next prompt —
no restart required, because the hook re-reads the file on every invocation.

To disable temporarily, rename the file (e.g., `prompt-context.txt.disabled`).
The hook fails open and the session reverts to default behavior.
