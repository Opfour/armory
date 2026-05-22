#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)".*/\1/p' | head -1)

if [ -z "$CMD" ]; then
  exit 0
fi

is_git_push=false
case "$CMD" in
  *git\ push*) is_git_push=true ;;
esac

if [ "$is_git_push" = true ]; then
  if printf '%s\n' "$CMD" | grep -Eq '(^|[[:space:]])--force-with-lease([=[:space:]]|$)'; then
    :
  elif printf '%s\n' "$CMD" | grep -Eq '(^|[[:space:]])(--force|-f)([[:space:]]|$)'; then
    echo "BLOCKED: plain git push --force rewrites remote history; use --force-with-lease for stack rebases." >&2
    exit 1
  fi
fi

metadata=".stack-prs.yaml"
if [ ! -f "$metadata" ]; then
  exit 0
fi

declared_parent() {
  branch="$1"
  awk -v wanted="$branch" '
    /^[[:space:]]*-[[:space:]]*name:[[:space:]]*/ {
      current=$0
      sub(/^[[:space:]]*-[[:space:]]*name:[[:space:]]*/, "", current)
      gsub(/^"|"$/, "", current)
      gsub(/^'\''|'\''$/, "", current)
      next
    }
    current == wanted && /^[[:space:]]*parent:[[:space:]]*/ {
      parent=$0
      sub(/^[[:space:]]*parent:[[:space:]]*/, "", parent)
      gsub(/^"|"$/, "", parent)
      gsub(/^'\''|'\''$/, "", parent)
      print parent
      exit
    }
  ' "$metadata"
}

extract_flag_value() {
  flag="$1"
  printf '%s\n' "$CMD" | awk -v flag="$flag" '
    {
      for (i = 1; i <= NF; i++) {
        if ($i == flag && i < NF) {
          print $(i + 1)
          exit
        }
        if (index($i, flag "=") == 1) {
          value=$i
          sub(flag "=", "", value)
          print value
          exit
        }
      }
    }
  '
}

if printf '%s\n' "$CMD" | grep -Eq '(^|[[:space:]])gh[[:space:]]+pr[[:space:]]+create([[:space:]]|$)'; then
  base=$(extract_flag_value "--base")
  head=$(extract_flag_value "--head")
  if [ -n "$base" ] && [ -n "$head" ]; then
    parent=$(declared_parent "$head")
    if [ -n "$parent" ] && [ "$parent" != "$base" ]; then
      echo "WARNING: .stack-prs.yaml declares parent '$parent' for '$head', but PR command uses base '$base'." >&2
    fi
  fi
fi

if [ "$is_git_push" = true ]; then
  branch=$(printf '%s\n' "$CMD" | awk '
    {
      for (i = NF; i >= 1; i--) {
        if ($i !~ /^-/ && $i != "push" && $i != "git" && $i != "origin") {
          print $i
          exit
        }
      }
    }
  ')
  if [ -z "$branch" ] || [ "$branch" = "$CMD" ]; then
    branch=$(git branch --show-current 2>/dev/null || true)
  fi
  parent=$(declared_parent "$branch")
  if [ -n "$parent" ]; then
    if ! git show-ref --verify --quiet "refs/remotes/origin/$parent"; then
      echo "WARNING: parent branch '$parent' for '$branch' has no origin ref; push parent before child." >&2
    elif [ -n "$(git log --oneline "origin/$parent..$parent" 2>/dev/null)" ]; then
      echo "WARNING: parent branch '$parent' has unpushed commits; push parent before child '$branch'." >&2
    fi
  fi
fi

if printf '%s\n' "$CMD" | grep -Eq '(^|[[:space:]])gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
  echo "WARNING: stack metadata exists; verify parent PRs are merged before merging a child PR." >&2
fi

exit 0
