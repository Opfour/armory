---
name: simplify-ignore
type: hook
description: >-
  Collapses code blocks marked with simplify-ignore-start/simplify-ignore-end
  comment markers before the agent reads a file. Redirects the Read tool to a
  collapsed copy via updatedInput and adds additionalContext warning the agent
  not to edit collapsed regions. On Stop, cleans up the session cache directory.
  Prevents agents from modifying infrastructure code, generated code, or complex
  subsystems they should not touch. Language-agnostic — works with any comment
  syntax. Triggers on: "hide code from agent", "code folding", "protect code
  sections", "collapse infrastructure code", "simplify-ignore markers".
metadata:
  version: 1.1.0
  category: operations
  tags: [context, simplify, code-folding, efficiency]
  difficulty: intermediate
hook:
  events: [PreToolUse, Stop]
  matcher: Read
  handler: {type: command, command: bash handler.sh, timeout_ms: 5000}
---
# simplify-ignore

Hides marked code blocks from Claude Code's Read tool, reducing context noise
and preventing agents from modifying protected code sections.

## How It Works

### Marker Format

Add comment markers around code blocks to hide:

```python
# simplify-ignore-start
class InternalCacheManager:
    """Complex infrastructure the agent shouldn't touch."""
    # ... 500 lines of cache invalidation logic ...
# simplify-ignore-end
```

Works with any comment syntax:

```javascript
// simplify-ignore-start
// ... protected code ...
// simplify-ignore-end
```

```html
<!-- simplify-ignore-start -->
<!-- ... protected code ... -->
<!-- simplify-ignore-end -->
```

### Events

| Event | Matcher | Purpose |
|-------|---------|---------|
| `PreToolUse` | `Read` | Redirect Read to a collapsed copy via `updatedInput` |
| `Stop` | — | Clean up the session cache directory |

### PreToolUse (Read)

1. Read the JSON input from stdin to extract `file_path`, `session_id`, and
   optional `offset`/`limit` parameters
2. Check if the file contains `simplify-ignore-start` markers
3. If markers found:
   - Cache the original in `/tmp/.claude-simplify-ignore-{session}/`
   - Generate a collapsed copy with `[COLLAPSED: N lines — simplify-ignore]`
     placeholders replacing each marked block
   - Emit `hookSpecificOutput` JSON with:
     - `permissionDecision: "allow"` — do not block the Read
     - `updatedInput.file_path` — redirected to the collapsed temp file
     - `additionalContext` — informs the agent about collapsed regions
4. If no markers, exit 0 (passthrough — no JSON output)

### Stop

Clean up the session cache directory to avoid temp file accumulation.

## Output Format

On files with markers, the hook emits:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {"file_path": "/tmp/.claude-simplify-ignore-.../file.collapsed"},
    "additionalContext": "simplify-ignore: collapsed 42 lines in /path/to/file.py ..."
  }
}
```

## Caveats

- Edits to collapsed regions are silently ignored — the agent cannot modify
  what it cannot see
- Nested markers are not supported — the first `simplify-ignore-end` closes
  the most recent `simplify-ignore-start`
- The cache is session-scoped and cleaned on Stop — no persistent state
- The collapsed temp file path differs from the original — agents see the
  temp path in Read output but `additionalContext` names the real file
