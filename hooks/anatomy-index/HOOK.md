---
name: anatomy-index
type: hook
description: 'Generates and maintains a project file index with one-line descriptions
  and token estimates. On session start or first tool use, builds .claude/anatomy.md
  by walking the project tree. Before Read, displays the target file summary so Claude
  can decide to skip. After Write/Edit, updates the changed file entry in the index.
  Respects .gitignore exclusions. Triggers on: file index, project map, codebase
  anatomy, file summary index, project structure overview.

  '
metadata:
  version: 1.0.0
  category: operations
  tags: [context, index, anatomy, efficiency]
  difficulty: intermediate
hook:
  events: [PreToolUse, PostToolUse]
  matcher: ''
  handler: {type: command, command: bash handler.sh, timeout_ms: 10000}
---
# anatomy-index

Maintains a lightweight project file index so Claude can make informed decisions
about which files to read.

## How It Works

### Index Generation

On first invocation (when `.claude/anatomy.md` does not exist), the hook walks the
project tree and generates an index with one line per file:

```
src/config.ts | Configuration loader and validator | ~320 tokens
src/index.ts  | Express app entry point            | ~180 tokens
```

### Pre-Read Summary

Before a `Read` tool invocation, the hook looks up the target file in the index
and emits its summary line to stderr. This lets Claude decide whether the read
is necessary based on the description and token cost.

### Post-Write/Edit Update

After a `Write` or `Edit` tool invocation, the hook updates the changed file's
entry in the index with fresh description and token estimate.

## Description Extraction

Extracts the first meaningful comment or docstring from source files:

- **Python**: first docstring (`"""..."""`) or `# comment` at module level
- **TypeScript/JavaScript**: first `//` or `/** ... */` comment
- Falls back to filename-based description for other file types

Descriptions are truncated to ~80 characters.

## Token Estimation

Uses `file_size_bytes / 4` as a rough heuristic.

## Exclusions

Respects `.gitignore` patterns and excludes common directories:
`node_modules`, `__pycache__`, `.git`, `dist`, `build`, `.next`, `venv`, `.venv`

## Index Location

`.claude/anatomy.md` in the project root.
