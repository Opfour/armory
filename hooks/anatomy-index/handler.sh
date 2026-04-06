#!/usr/bin/env bash
# anatomy-index hook — maintains .claude/anatomy.md project file index.
# Dispatches based on tool_name from stdin JSON.
# Always exits 0 (informational only, never blocks tools).

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

INDEX_DIR=".claude"
INDEX_FILE="${INDEX_DIR}/anatomy.md"

EXCLUDE_DIRS="node_modules|__pycache__|\.git|dist|build|\.next|venv|\.venv|\.mypy_cache|\.pytest_cache|\.tox|\.eggs"

# --- Helpers ---

estimate_tokens() {
  local file="$1"
  if [ -f "$file" ]; then
    local bytes
    bytes=$(wc -c < "$file" | tr -d ' ')
    echo $((bytes / 4))
  else
    echo 0
  fi
}

extract_description() {
  local file="$1"
  local ext="${file##*.}"
  local desc=""

  case "$ext" in
    py)
      # First docstring or comment
      desc=$(sed -n '1,20{
        /^[[:space:]]*"""/{
          s/^[[:space:]]*"""//
          s/"""[[:space:]]*$//
          /^$/!{p;q;}
          n
          s/^[[:space:]]*//
          s/""".*//
          p;q
        }
        /^[[:space:]]*#[[:space:]]/{
          s/^[[:space:]]*#[[:space:]]*//
          p;q
        }
      }' "$file" 2>/dev/null)
      ;;
    ts|js|tsx|jsx|mjs|cjs)
      # First // comment or /** */ block
      desc=$(sed -n '1,20{
        /^[[:space:]]*\/\/[[:space:]]/{
          s/^[[:space:]]*\/\/[[:space:]]*//
          p;q
        }
        /^[[:space:]]*\/\*\*/{
          s/^[[:space:]]*\/\*\*[[:space:]]*//
          s/[[:space:]]*\*\/.*//
          /^$/!{p;q;}
          n
          s/^[[:space:]]*\*[[:space:]]*//
          s/[[:space:]]*\*\/.*//
          p;q
        }
      }' "$file" 2>/dev/null)
      ;;
    sh|bash|zsh)
      # First # comment after shebang
      desc=$(sed -n '1,10{
        /^#!/d
        /^[[:space:]]*#[[:space:]]/{
          s/^[[:space:]]*#[[:space:]]*//
          p;q
        }
      }' "$file" 2>/dev/null)
      ;;
  esac

  if [ -z "$desc" ]; then
    desc=$(basename "$file")
  fi

  # Truncate to ~80 chars
  printf '%s' "$desc" | head -c 80
}

build_index_line() {
  local file="$1"
  local tokens
  local desc
  tokens=$(estimate_tokens "$file")
  desc=$(extract_description "$file")
  printf '%-50s | %-60s | ~%s tokens\n' "$file" "$desc" "$tokens"
}

should_exclude() {
  local path="$1"
  echo "$path" | grep -qE "(^|/)(${EXCLUDE_DIRS})(/|$)"
}

build_full_index() {
  mkdir -p "$INDEX_DIR"

  {
    echo "# Project Anatomy"
    echo ""
    echo "Auto-generated file index. One line per file with description and token estimate."
    echo ""
    echo '```'
  } > "$INDEX_FILE"

  # Use git ls-files if in a git repo, otherwise find
  local files
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    files=$(git ls-files --cached --others --exclude-standard 2>/dev/null | sort)
  else
    files=$(find . -type f -not -path '*/\.*' | sed 's|^\./||' | sort)
  fi

  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if should_exclude "$f"; then
      continue
    fi
    # Skip binary files and very large files (>100KB)
    if [ -f "$f" ] && [ "$(wc -c < "$f" | tr -d ' ')" -lt 102400 ]; then
      if file -b --mime-type "$f" 2>/dev/null | grep -q "^text/"; then
        build_index_line "$f" >> "$INDEX_FILE"
      fi
    fi
  done <<< "$files"

  echo '```' >> "$INDEX_FILE"
}

update_index_entry() {
  local file="$1"
  if [ ! -f "$INDEX_FILE" ]; then
    return
  fi
  local new_line
  new_line=$(build_index_line "$file")
  # Remove old entry and add new one
  local escaped_file
  escaped_file=$(printf '%s' "$file" | sed 's/[.[\/*^$]/\\&/g')
  if grep -q "^${escaped_file}" "$INDEX_FILE" 2>/dev/null; then
    sed -i '' "/^${escaped_file}/c\\
${new_line}" "$INDEX_FILE" 2>/dev/null || true
  else
    # Insert before closing ``` marker
    sed -i '' "/^\`\`\`$/i\\
${new_line}" "$INDEX_FILE" 2>/dev/null || true
  fi
}

lookup_file() {
  local file="$1"
  if [ ! -f "$INDEX_FILE" ]; then
    return
  fi
  local escaped_file
  escaped_file=$(printf '%s' "$file" | sed 's/[.[\/*^$]/\\&/g')
  local entry
  entry=$(grep "^${escaped_file}" "$INDEX_FILE" 2>/dev/null || true)
  if [ -n "$entry" ]; then
    echo "📋 ${entry}" >&2
  fi
}

# --- Main dispatch ---

# Build index if it doesn't exist yet
if [ ! -f "$INDEX_FILE" ]; then
  build_full_index
fi

case "${TOOL_NAME}" in
  Read)
    FILE_PATH=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
    if [ -n "$FILE_PATH" ]; then
      # Convert to relative path if possible
      REL_PATH="${FILE_PATH#$PWD/}"
      lookup_file "$REL_PATH"
    fi
    ;;
  Write|Edit)
    FILE_PATH=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
    if [ -n "$FILE_PATH" ]; then
      REL_PATH="${FILE_PATH#$PWD/}"
      update_index_entry "$REL_PATH"
    fi
    ;;
  *)
    # Other tools — no action needed
    ;;
esac

exit 0
