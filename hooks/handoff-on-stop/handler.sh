#!/usr/bin/env bash
set -u

if [ ! -f ".docs/handoff.md" ]; then
  exit 0
fi

log_file=".docs/handoff.log"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
script="$repo_root/skills/handoff/scripts/handoff.py"

if [ -x "$script" ]; then
  "$script" --project-root "$PWD" >/dev/null 2>>"$log_file" || true
elif command -v uv >/dev/null 2>&1 && [ -f "$script" ]; then
  uv run "$script" --project-root "$PWD" >/dev/null 2>>"$log_file" || true
else
  printf '%s handoff-on-stop: generator unavailable\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >>"$log_file" 2>/dev/null || true
fi

exit 0
