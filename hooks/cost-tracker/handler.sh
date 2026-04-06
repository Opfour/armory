#!/usr/bin/env bash
# cost-tracker hook — tracks per-tool token usage, waste indicators, and session costs.
# Events: PostToolUse (Read, Write, Edit), Stop.
# Always exits 0 (logging should never block operations).

set -euo pipefail

CSV_FILE="$HOME/.claude/cost-log.csv"
INPUT=$(cat)

# --- Extract common fields ---

TOOL_NAME=$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
SESSION_ID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
SESSION_ID=${SESSION_ID:-unknown}

# Per-session state: JSONL file with one record per tool invocation
STATE_FILE="/tmp/.claude-cost-tracker-${SESSION_ID}.jsonl"

# --- Helpers ---

estimate_tokens_from_file() {
  local file="$1"
  if [ -f "$file" ]; then
    local bytes
    bytes=$(wc -c < "$file" | tr -d ' ')
    echo $((bytes / 4))
  else
    echo 0
  fi
}

estimate_tokens_from_size() {
  local bytes="$1"
  echo $((bytes / 4))
}

check_read_dedup_tracker() {
  local file="$1"
  local tracker="/tmp/.claude-read-tracker-${SESSION_ID}.txt"
  if [ -f "$tracker" ]; then
    local count
    count=$(grep -cxF "$file" "$tracker" 2>/dev/null || echo 0)
    echo "$count"
  else
    echo 0
  fi
}

check_anatomy_entry() {
  local file="$1"
  local anatomy=".claude/anatomy.md"
  if [ -f "$anatomy" ]; then
    local escaped
    escaped=$(printf '%s' "$file" | sed 's/[.[\/*^$]/\\&/g')
    if grep -q "^${escaped}" "$anatomy" 2>/dev/null; then
      echo 1
    else
      echo 0
    fi
  else
    echo 0
  fi
}

append_operation() {
  # Appends a JSONL record to the session state file
  local tool="$1"
  local file_path="$2"
  local tokens="$3"
  local waste_type="$4"
  local timestamp
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '{"ts":"%s","tool":"%s","file":"%s","tokens":%s,"waste":"%s"}\n' \
    "$timestamp" "$tool" "$file_path" "$tokens" "$waste_type" >> "$STATE_FILE"
}

# --- PostToolUse: Read ---

handle_read() {
  local file_path
  file_path=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ -z "$file_path" ] && return

  local tokens
  tokens=$(estimate_tokens_from_file "$file_path")

  # Determine waste type
  local waste="none"

  # Check 1: Repeated read (cross-reference read-dedup tracker)
  local read_count
  read_count=$(check_read_dedup_tracker "$file_path")
  if [ "$read_count" -gt 1 ]; then
    waste="repeated_read"
  fi

  # Check 2: Large read when anatomy summary existed
  if [ "$tokens" -gt 1000 ]; then
    local rel_path="${file_path#$PWD/}"
    local has_anatomy
    has_anatomy=$(check_anatomy_entry "$rel_path")
    if [ "$has_anatomy" -eq 1 ] && [ "$waste" = "none" ]; then
      waste="large_read_with_anatomy"
    elif [ "$has_anatomy" -eq 1 ] && [ "$waste" = "repeated_read" ]; then
      waste="repeated_read+large_read_with_anatomy"
    fi
  fi

  # Check 3: Full-file read when partial would suffice
  # Heuristic: if file >2000 tokens and no offset/limit params detected, flag it
  local has_offset
  has_offset=$(printf '%s' "$INPUT" | sed -n 's/.*"offset"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)
  local has_limit
  has_limit=$(printf '%s' "$INPUT" | sed -n 's/.*"limit"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)
  if [ "$tokens" -gt 2000 ] && [ -z "$has_offset" ] && [ -z "$has_limit" ]; then
    if [ "$waste" = "none" ]; then
      waste="full_file_read"
    else
      waste="${waste}+full_file_read"
    fi
  fi

  append_operation "Read" "$file_path" "$tokens" "$waste"
}

# --- PostToolUse: Write ---

handle_write() {
  local file_path
  file_path=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ -z "$file_path" ] && return

  local tokens
  tokens=$(estimate_tokens_from_file "$file_path")

  append_operation "Write" "$file_path" "$tokens" "none"
}

# --- PostToolUse: Edit ---

handle_edit() {
  local file_path
  file_path=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ -z "$file_path" ] && return

  # For edits, estimate tokens from old_string + new_string sizes rather than full file
  local old_string new_string
  old_string=$(printf '%s' "$INPUT" | sed -n 's/.*"old_string"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  new_string=$(printf '%s' "$INPUT" | sed -n 's/.*"new_string"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

  local old_bytes new_bytes tokens
  old_bytes=${#old_string}
  new_bytes=${#new_string}
  tokens=$(estimate_tokens_from_size $((old_bytes + new_bytes)))

  append_operation "Edit" "$file_path" "$tokens" "none"
}

# --- Stop: Session summary ---

handle_stop() {
  # Write original CSV row (backward compatible)
  if [ ! -f "$CSV_FILE" ]; then
    echo "timestamp,session_id,total_cost,total_tokens" > "$CSV_FILE"
  fi

  local timestamp
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  local total_cost
  total_cost=$(printf '%s' "$INPUT" | sed -n 's/.*"total_cost"[[:space:]]*:[[:space:]]*\([0-9.]*\).*/\1/p' | head -1)
  total_cost=${total_cost:-0}

  local total_tokens
  total_tokens=$(printf '%s' "$INPUT" | sed -n 's/.*"total_tokens"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)
  total_tokens=${total_tokens:-0}

  echo "${timestamp},${SESSION_ID},${total_cost},${total_tokens}" >> "$CSV_FILE"

  # Generate companion summary JSON from per-tool state
  local summary_file="$HOME/.claude/cost-tracker-summary-${SESSION_ID}.json"

  if [ ! -f "$STATE_FILE" ]; then
    # No per-tool data collected — write minimal summary
    cat > "$summary_file" <<ENDJSON
{"session_id":"${SESSION_ID}","timestamp":"${timestamp}","total_cost":${total_cost},"total_tokens":${total_tokens},"tool_tokens":{},"waste":{"total_waste_tokens":0,"waste_pct":0,"operations":[]}}
ENDJSON
    return
  fi

  # Aggregate per-tool tokens
  local read_tokens=0 write_tokens=0 edit_tokens=0
  local total_tool_tokens=0
  local waste_tokens=0
  local waste_ops=""
  local waste_count=0

  while IFS= read -r line; do
    local tool tokens waste
    tool=$(printf '%s' "$line" | sed -n 's/.*"tool"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    tokens=$(printf '%s' "$line" | sed -n 's/.*"tokens"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p')
    waste=$(printf '%s' "$line" | sed -n 's/.*"waste"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    tokens=${tokens:-0}

    case "$tool" in
      Read) read_tokens=$((read_tokens + tokens)) ;;
      Write) write_tokens=$((write_tokens + tokens)) ;;
      Edit) edit_tokens=$((edit_tokens + tokens)) ;;
    esac
    total_tool_tokens=$((total_tool_tokens + tokens))

    if [ "$waste" != "none" ]; then
      waste_tokens=$((waste_tokens + tokens))
      waste_count=$((waste_count + 1))
      local file_path
      file_path=$(printf '%s' "$line" | sed -n 's/.*"file"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      if [ "$waste_count" -le 5 ]; then
        [ -n "$waste_ops" ] && waste_ops="${waste_ops},"
        waste_ops="${waste_ops}{\"file\":\"${file_path}\",\"tokens\":${tokens},\"type\":\"${waste}\"}"
      fi
    fi
  done < "$STATE_FILE"

  local waste_pct=0
  if [ "$total_tool_tokens" -gt 0 ]; then
    waste_pct=$((waste_tokens * 100 / total_tool_tokens))
  fi

  cat > "$summary_file" <<ENDJSON
{"session_id":"${SESSION_ID}","timestamp":"${timestamp}","total_cost":${total_cost},"total_tokens":${total_tokens},"tool_tokens":{"Read":${read_tokens},"Write":${write_tokens},"Edit":${edit_tokens},"total":${total_tool_tokens}},"waste":{"total_waste_tokens":${waste_tokens},"waste_pct":${waste_pct},"top_operations":[${waste_ops}]}}
ENDJSON

  # Clean up session state file
  rm -f "$STATE_FILE"
}

# --- Main dispatch ---

case "${TOOL_NAME:-}" in
  Read)
    handle_read
    ;;
  Write)
    handle_write
    ;;
  Edit)
    handle_edit
    ;;
  *)
    # Check if this is a Stop event (no tool_name, but has total_cost/session_id)
    if printf '%s' "$INPUT" | grep -q '"total_cost"'; then
      handle_stop
    fi
    ;;
esac

exit 0
