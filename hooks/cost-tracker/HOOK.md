---
name: cost-tracker
type: hook
description: 'Tracks per-tool token usage, waste indicators, and session costs. Fires
  on PostToolUse for Read/Write/Edit to estimate tokens per operation and detect wasteful
  patterns (repeated reads, large reads with anatomy summaries, full-file reads). On
  Stop, writes a backward-compatible CSV row and a companion JSON summary with per-tool
  token breakdowns, waste percentage, and top 5 wasteful operations. Integrates with
  read-dedup tracker and anatomy-index for cross-hook waste detection.

  '
metadata:
  version: 2.0.0
  category: operations
  tags: [cost, tokens, usage, logging, waste, efficiency]
  difficulty: intermediate
hook:
  events: [PostToolUse, Stop]
  matcher: ''
  handler: {type: command, command: bash handler.sh, timeout_ms: 5000}
---
# cost-tracker

Tracks per-tool token usage, waste indicators, and session-level costs.

## Events

| Event | Matcher | Purpose |
|-------|---------|---------|
| `PostToolUse` | `Read` | Estimate read tokens, detect waste patterns |
| `PostToolUse` | `Write` | Estimate write tokens |
| `PostToolUse` | `Edit` | Estimate edit tokens (old_string + new_string) |
| `Stop` | — | Write CSV row + companion JSON summary |

## Per-Tool Token Tracking

Each `Read`, `Write`, or `Edit` invocation appends a JSONL record to
`/tmp/.claude-cost-tracker-{session_id}.jsonl`:

```json
{"ts":"2026-03-29T12:00:00Z","tool":"Read","file":"/src/config.ts","tokens":320,"waste":"none"}
```

Token estimation uses the `bytes / 4` heuristic. For `Edit` operations,
tokens are estimated from the combined size of `old_string` + `new_string`
rather than the full file.

## Waste Detection

Three waste indicators are tracked on `Read` operations:

| Waste Type | Trigger |
|-----------|---------|
| `repeated_read` | File appears >1 time in the read-dedup tracker |
| `large_read_with_anatomy` | File is >1000 tokens and has an anatomy-index entry |
| `full_file_read` | File is >2000 tokens and read without `offset`/`limit` params |

Multiple waste types on a single read are joined with `+`
(e.g., `repeated_read+full_file_read`).

### Cross-Hook Integration

- **read-dedup**: Reads `/tmp/.claude-read-tracker-{session_id}.txt` to detect
  duplicate file reads without duplicating tracking logic.
- **anatomy-index**: Checks `.claude/anatomy.md` for file summaries to flag
  large reads where a summary was available.

## Output Files

### CSV (backward compatible)

`~/.claude/cost-log.csv` — one row per session, unchanged format:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp of session end |
| `session_id` | Unique session identifier |
| `total_cost` | Total API cost in USD |
| `total_tokens` | Total tokens consumed (input + output) |

### Companion JSON

`~/.claude/cost-tracker-summary-{session_id}.json` — per-session summary:

```json
{
  "session_id": "abc123",
  "timestamp": "2026-03-29T12:00:00Z",
  "total_cost": 0.45,
  "total_tokens": 12500,
  "tool_tokens": {
    "Read": 8200,
    "Write": 1500,
    "Edit": 300,
    "total": 10000
  },
  "waste": {
    "total_waste_tokens": 3200,
    "waste_pct": 32,
    "top_operations": [
      {"file": "/src/large.ts", "tokens": 2000, "type": "full_file_read"},
      {"file": "/src/config.ts", "tokens": 1200, "type": "repeated_read"}
    ]
  }
}
```

## Usage

```bash
# Total cost this month
awk -F, 'NR>1 {sum+=$3} END {printf "$%.2f\n", sum}' ~/.claude/cost-log.csv

# Top 5 most expensive sessions
sort -t, -k3 -rn ~/.claude/cost-log.csv | head -5

# View waste summary for a session
cat ~/.claude/cost-tracker-summary-SESSION_ID.json | jq '.waste'

# Find sessions with >20% waste
for f in ~/.claude/cost-tracker-summary-*.json; do
  jq -r 'select(.waste.waste_pct > 20) | "\(.session_id): \(.waste.waste_pct)% waste"' "$f" 2>/dev/null
done
```

## Notes

- The CSV format is unchanged from v1 — existing tooling continues to work.
- Per-tool JSONL state is cleaned up on Stop. If a session crashes, stale files
  remain in `/tmp/` and are cleaned by OS temp file rotation.
- Waste percentages are integer (floor division). A session with zero tool
  operations reports 0% waste.
