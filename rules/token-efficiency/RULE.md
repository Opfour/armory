---
name: token-efficiency
type: rule
description: >
  Enforces token-efficient tool usage patterns to reduce context waste and lower
  session costs. Covers file reading strategies (targeted line-range reads, avoiding
  re-reads of in-context files), search-first patterns (Grep/Glob before full Read),
  write discipline (never write unchanged content, append without full read), and
  context management (check summaries before committing to full reads). Use this rule
  when optimizing Claude Code session efficiency, reducing token consumption, or
  establishing tool-usage best practices. Triggers on: "token efficiency",
  "reduce tokens", "context waste", "tool usage", "read efficiency", "minimize
  reads", "save tokens", "optimize reads", "how to reduce token usage",
  "session cost", "context window management".
metadata:
  version: 1.0.0
  scope: global
  applies_to:
    languages: ["*"]
  category: development
  tags: [token-efficiency, context-management, tool-usage, cost-reduction]
  difficulty: beginner
---

# Token Efficiency

Rules for minimizing token waste when using Claude Code tools. Every unnecessary read, redundant write, or unfocused search burns tokens that deliver zero value.

## Search Before Read

Use Grep or Glob to locate what you need before reading entire files.

- **Grep** to find content by pattern — returns matching lines with file paths
- **Glob** to find files by name pattern — returns matching file paths
- **Read** only after you know exactly which file and lines you need

```
# wrong: read the entire file hoping to find a function
Read src/auth/handler.ts            # 500 lines consumed

# right: search first, then read the target
Grep "function validateToken" src/  # 1 line consumed
Read src/auth/handler.ts:142-168    # 26 lines consumed
```

## Never Re-Read In-Context Files

If a file was already read in this conversation, its content is in context. Do not read it again.

- Before issuing a Read, check whether the file already appeared in tool results
- If you need to reference earlier content, work from what is already in context
- The only exception: the file was modified since the last read and you need the updated content

## Targeted Line-Range Reads

When reading large files, specify the exact line range you need.

- Use `offset` and `limit` parameters on Read to fetch only the relevant section
- After a Grep match returns line numbers, read a narrow window around those lines
- Full-file reads are acceptable only for files under ~100 lines or when you genuinely need the entire content

```
# wrong: reading 2000 lines when you need 20
Read src/server.ts

# right: reading only the section you need
Read src/server.ts offset=340 limit=30
```

## Append Without Full Read

When adding content to the end of a file, do not read the entire file first.

- Use Edit with a unique anchor string near the end of the file (a closing brace, a final export, a trailing comment)
- If the file structure is known from earlier context, write directly using the known structure
- A full read is justified only when you do not know the file structure at all

## Check Descriptions Before Full Reads

Before committing to reading a file, use cheaper signals to confirm it is the right target.

- File names and directory structure often reveal purpose without reading content
- Grep a distinctive keyword to confirm the file contains what you expect
- Read the first 20-30 lines (imports, class declaration) to verify before reading the full file

## Never Write Unchanged Content

Do not write a file back with no meaningful changes.

- If an Edit produces `old_string` identical to `new_string`, skip the operation
- If you read a file and determine no changes are needed, do not write it back
- Each write costs tokens for the content and confirmation — skip writes that produce identical output

## Minimize Exploration Passes

Plan your exploration before executing it.

- Decide which files you need to understand before starting a chain of reads
- Batch related Grep queries by pattern when possible instead of running them one at a time
- If exploring a directory structure, one `ls` or Glob call is cheaper than reading every file to understand the layout
