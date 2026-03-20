#!/usr/bin/env bash
# cost-tracker hook — appends session cost/token data to CSV.
# Reads session summary JSON from stdin on Stop event.
# Always exits 0 (logging should never block shutdown).

set -euo pipefail

CSV_FILE="$HOME/.claude/cost-log.csv"
INPUT=$(cat)

# Write header if file doesn't exist
if [ ! -f "$CSV_FILE" ]; then
  echo "timestamp,session_id,total_cost,total_tokens" > "$CSV_FILE"
fi

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SESSION_ID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
SESSION_ID=${SESSION_ID:-unknown}

TOTAL_COST=$(printf '%s' "$INPUT" | sed -n 's/.*"total_cost"[[:space:]]*:[[:space:]]*\([0-9.]*\).*/\1/p' | head -1)
TOTAL_COST=${TOTAL_COST:-0}

TOTAL_TOKENS=$(printf '%s' "$INPUT" | sed -n 's/.*"total_tokens"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)
TOTAL_TOKENS=${TOTAL_TOKENS:-0}

echo "${TIMESTAMP},${SESSION_ID},${TOTAL_COST},${TOTAL_TOKENS}" >> "$CSV_FILE"

exit 0
