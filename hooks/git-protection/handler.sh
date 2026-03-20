#!/usr/bin/env bash
# git-protection hook — blocks dangerous git operations.
# Reads tool input JSON from stdin, checks the command field.
# Exit 0 = allow, exit non-zero = block.

set -euo pipefail

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)".*/\1/p' | head -1)

if [ -z "$CMD" ]; then
  exit 0
fi

# Check for dangerous patterns
if printf '%s' "$CMD" | grep -qE 'git\s+push\s+.*(-f|--force)'; then
  echo "BLOCKED: git push --force rewrites remote history." >&2
  exit 1
fi

if printf '%s' "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
  echo "BLOCKED: git reset --hard discards all uncommitted changes." >&2
  exit 1
fi

if printf '%s' "$CMD" | grep -qE 'git\s+branch\s+-D\s+(main|master)'; then
  echo "BLOCKED: git branch -D on main/master deletes the primary branch." >&2
  exit 1
fi

if printf '%s' "$CMD" | grep -qE 'git\s+clean\s+-f?d'; then
  echo "BLOCKED: git clean -fd removes untracked files permanently." >&2
  exit 1
fi

exit 0
