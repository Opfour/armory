#!/usr/bin/env bash
# prompt-context hook — injects a text file as additionalContext on every prompt.
# Checks project-level .claude/prompt-context.txt first, then ~/.claude/prompt-context.txt.
# Fails open: missing or unreadable files exit 0 silently.

set -euo pipefail

# Determine which file to read (project-level takes precedence)
CONTEXT_FILE=""
if [ -r ".claude/prompt-context.txt" ]; then
  CONTEXT_FILE=".claude/prompt-context.txt"
elif [ -r "${HOME}/.claude/prompt-context.txt" ]; then
  CONTEXT_FILE="${HOME}/.claude/prompt-context.txt"
fi

# No file found — fail open
if [ -z "$CONTEXT_FILE" ]; then
  exit 0
fi

# Read content, fail open on error
CONTENT=$(cat "$CONTEXT_FILE" 2>/dev/null) || exit 0
if [ -z "$CONTENT" ]; then
  exit 0
fi

# Escape content for JSON embedding (newlines, quotes, backslashes, tabs)
ESCAPED=$(printf '%s' "$CONTENT" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/	/\\t/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')

# Emit structured JSON output
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}' "$ESCAPED"

exit 0
