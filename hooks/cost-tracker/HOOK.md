---
name: cost-tracker
type: hook
description: 'Logs session cost and token usage to a CSV file after each Claude Code
  session completes. Fires on the Stop event, reads cost and token data from the session
  summary JSON on stdin, and appends a row to ~/.claude/cost-log.csv. Use this hook
  when you want to track API spending over time, identify expensive sessions, or generate
  usage reports from the CSV data.

  '
metadata:
  version: 1.0.0
  category: operations
  tags: [cost, tokens, usage, logging]
  difficulty: beginner
hook:
  events: [Stop]
  matcher: ''
  handler: {type: command, command: bash handler.sh, timeout_ms: 5000}
---
# cost-tracker

Records session cost and token usage to a local CSV file.

## CSV Format

The log file is stored at `~/.claude/cost-log.csv` with the following columns:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp of session end |
| `session_id` | Unique session identifier |
| `total_cost` | Total API cost in USD |
| `total_tokens` | Total tokens consumed (input + output) |

## Usage

Query spending with standard CLI tools:

```bash
# Total cost this month
awk -F, 'NR>1 {sum+=$3} END {printf "$%.2f\n", sum}' ~/.claude/cost-log.csv

# Top 5 most expensive sessions
sort -t, -k3 -rn ~/.claude/cost-log.csv | head -5

# Daily cost breakdown
awk -F, 'NR>1 {split($1,d,"T"); costs[d[1]]+=$3} END {for(k in costs) printf "%s: $%.2f\n", k, costs[k]}' ~/.claude/cost-log.csv
```

## Notes

- The CSV header is written automatically on first use.
- If cost or token data is missing from the session JSON, the row is still written with zero values.
- The file grows unbounded — prune manually or with a cron job if needed.
