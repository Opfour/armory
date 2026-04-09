#!/usr/bin/env bash
# simplify-ignore hook — collapses marked code blocks before Read.
# Markers: simplify-ignore-start / simplify-ignore-end (any comment syntax).
# On PreToolUse(Read): writes collapsed content to a temp file and redirects
#   the Read tool to the collapsed version via updatedInput.
# On Stop: cleans up session cache directory.
# Always exits 0 (never blocks reads).

set -euo pipefail

INPUT=$(cat)

# Detect event type from hook input
TOOL_NAME=$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
SESSION_ID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
SESSION_ID=${SESSION_ID:-default}

CACHE_DIR="/tmp/.claude-simplify-ignore-${SESSION_ID}"

# Stop event — clean up cache
if [ -z "$TOOL_NAME" ]; then
  rm -rf "$CACHE_DIR" 2>/dev/null || true
  exit 0
fi

# PreToolUse(Read) — collapse marked blocks
FILE_PATH=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Quick check: does the file contain markers?
if ! grep -q 'simplify-ignore-start' "$FILE_PATH" 2>/dev/null; then
  exit 0
fi

# Set up cache directory
mkdir -p "$CACHE_DIR"
CACHE_KEY=$(printf '%s' "$FILE_PATH" | sed 's|/|__|g')
COLLAPSED_FILE="${CACHE_DIR}/${CACHE_KEY}.collapsed"

# Cache original for reference
cp "$FILE_PATH" "${CACHE_DIR}/${CACHE_KEY}.original"

# Collapse marked blocks using awk — write to temp file
awk '
  /simplify-ignore-start/ {
    inside = 1
    count = 0
    match($0, /^[[:space:]]*[^a-zA-Z]*/)
    prefix = substr($0, RSTART, RLENGTH)
    next
  }
  /simplify-ignore-end/ {
    if (inside) {
      printf "%s[COLLAPSED: %d lines — simplify-ignore]\n", prefix, count
      inside = 0
    }
    next
  }
  inside {
    count++
    next
  }
  { print }
' "$FILE_PATH" > "$COLLAPSED_FILE"

ORIGINAL_COUNT=$(wc -l < "$FILE_PATH" | tr -d ' ')
COLLAPSED_COUNT=$(wc -l < "$COLLAPSED_FILE" | tr -d ' ')
DIFF=$((ORIGINAL_COUNT - COLLAPSED_COUNT))

if [ "$DIFF" -le 0 ]; then
  # No lines collapsed — nothing to override
  rm -f "$COLLAPSED_FILE"
  exit 0
fi

# Escape the collapsed file path for JSON
ESCAPED_PATH=$(printf '%s' "$COLLAPSED_FILE" | sed 's/\\/\\\\/g; s/"/\\"/g')

# Also extract offset/limit from original input to preserve them
OFFSET=$(printf '%s' "$INPUT" | sed -n 's/.*"offset"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)
LIMIT=$(printf '%s' "$INPUT" | sed -n 's/.*"limit"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)

# Build updatedInput — redirect Read to the collapsed file
UPDATED_INPUT="{\"file_path\":\"${ESCAPED_PATH}\""
if [ -n "$OFFSET" ]; then
  UPDATED_INPUT="${UPDATED_INPUT},\"offset\":${OFFSET}"
fi
if [ -n "$LIMIT" ]; then
  UPDATED_INPUT="${UPDATED_INPUT},\"limit\":${LIMIT}"
fi
UPDATED_INPUT="${UPDATED_INPUT}}"

# Emit structured JSON: redirect Read + inform agent about collapsed regions
CONTEXT="simplify-ignore: collapsed ${DIFF} lines in ${FILE_PATH} (${ORIGINAL_COUNT} → ${COLLAPSED_COUNT}). Regions marked with simplify-ignore markers are hidden. Do not attempt to edit collapsed regions."
ESCAPED_CONTEXT=$(printf '%s' "$CONTEXT" | sed 's/\\/\\\\/g; s/"/\\"/g')

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"simplify-ignore: redirecting to collapsed file","updatedInput":%s,"additionalContext":"%s"}}' "$UPDATED_INPUT" "$ESCAPED_CONTEXT"

exit 0
