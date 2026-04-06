#!/usr/bin/env bash
# read-dedup hook — warns on duplicate file reads within a session.
# Reads tool input JSON from stdin, extracts file_path.
# Emits stderr warning with estimated token count on duplicate reads.
# Always exits 0 (never blocks reads).

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

SESSION_ID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
SESSION_ID=${SESSION_ID:-default}

TRACKER="/tmp/.claude-read-tracker-${SESSION_ID}.txt"

# Check if file was already read this session
if [ -f "$TRACKER" ] && grep -qxF "$FILE_PATH" "$TRACKER"; then
  # Estimate tokens from file size (bytes / 4)
  if [ -f "$FILE_PATH" ]; then
    BYTES=$(wc -c < "$FILE_PATH" | tr -d ' ')
    TOKENS=$((BYTES / 4))
  else
    TOKENS=0
  fi
  echo "⚠ ${FILE_PATH} was already read this session (~${TOKENS} tokens). Use existing knowledge." >&2
  exit 0
fi

# Record this read
echo "$FILE_PATH" >> "$TRACKER"

exit 0
