---
name: read-dedup
type: hook
description: 'Detects and warns about duplicate file reads within a Claude Code session.
  Fires on PreToolUse for the Read tool, tracks files read in a session-scoped temp
  file, and emits a stderr warning with estimated token count when a file is read again.
  Reduces wasted context by nudging the model to reuse knowledge from earlier reads.
  Triggers on: duplicate read detection, token waste, re-read prevention, file read
  tracker, context dedup.

  '
metadata:
  version: 1.0.0
  category: operations
  tags: [context, dedup, tokens, efficiency]
  difficulty: beginner
hook:
  events: [PreToolUse]
  matcher: Read
  handler: {type: command, command: bash handler.sh, timeout_ms: 5000}
---
# read-dedup

Warns when Claude Code reads the same file twice in a single session.

## How It Works

On every `Read` tool invocation, the hook checks whether the target file has
already been read during the current session. If so, it emits a stderr warning
with the file's estimated token count:

```
⚠ src/config.ts was already read this session (~520 tokens). Use existing knowledge.
```

The model sees stderr output and can adjust its behavior accordingly.

## Token Estimation

Uses a rough heuristic: `file_size_bytes / 4`. This approximates the typical
byte-to-token ratio for source code and prose.

## Session Tracking

Read history is stored in `/tmp/.claude-read-tracker-{session_id}.json` as a
plain newline-delimited list of file paths. The tracker file is cleaned up
automatically when Claude Code starts a new session (install the `Stop` event
variant to clean up on exit, or rely on OS temp file cleanup).

## Limitations

- Partial reads (offset/limit) of the same file still count as a duplicate.
- Token estimate is approximate — actual tokenization varies by content.
- Does not distinguish between reading different ranges of the same file.
