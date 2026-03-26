---
name: pre-edit-backup
type: hook
description: 'Creates a backup copy of any file before Claude Code edits it. Fires
  on PreToolUse for the Edit tool, reads the file_path from the tool input JSON, and
  copies the original file to ~/.claude/backups/ with a timestamped filename. Maintains
  a maximum of 20 backup files by deleting the oldest when the limit is exceeded.
  Use this hook when you want a local safety net for file edits that goes beyond git
  history.

  '
metadata:
  version: 1.0.0
  category: operations
  tags: [backup, files, safety, pre-edit]
  difficulty: beginner
hook:
  events: [PreToolUse]
  matcher: Edit
  handler: {type: command, command: bash handler.sh, timeout_ms: 5000}
---
# pre-edit-backup

Automatically backs up files before they are modified by the Edit tool.

## Backup Location

All backups are stored in `~/.claude/backups/`. Each backup file is named:

```
{YYYYMMDD_HHMMSS}_{original_filename}
```

## Retention Policy

A maximum of 20 backup files are retained. When a new backup would exceed this
limit, the oldest backup file (by filesystem modification time) is deleted first.

## Restoration

To restore a file, copy the backup back to its original location:

```bash
cp ~/.claude/backups/20250115_143022_config.toml ./config.toml
```

## Limitations

- Only fires on Edit tool use, not on Write or Bash-based file modifications.
- Binary files are copied as-is without validation.
- The 20-file limit is global across all backed-up files, not per-file.
