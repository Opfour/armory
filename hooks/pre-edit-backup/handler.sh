#!/usr/bin/env bash
# pre-edit-backup hook — copies file to ~/.claude/backups/ before edit.
# Reads tool input JSON from stdin, extracts file_path.
# Always exits 0 (never blocks edits).

set -euo pipefail

BACKUP_DIR="$HOME/.claude/backups"
MAX_BACKUPS=20

INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

mkdir -p "$BACKUP_DIR"

BASENAME=$(basename "$FILE_PATH")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp "$FILE_PATH" "${BACKUP_DIR}/${TIMESTAMP}_${BASENAME}"

# Enforce retention limit — delete oldest files beyond MAX_BACKUPS
COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -type f | wc -l | tr -d ' ')
if [ "$COUNT" -gt "$MAX_BACKUPS" ]; then
  EXCESS=$((COUNT - MAX_BACKUPS))
  ls -1t "$BACKUP_DIR" | tail -n "$EXCESS" | while read -r OLD; do
    rm -f "${BACKUP_DIR}/${OLD}"
  done
fi

exit 0
