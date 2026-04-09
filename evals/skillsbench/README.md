# SkillsBench — Bootstrap Benchmark for Memento-Skills Integration

**Purpose:** quantify whether armory's curated skill library provides a real
efficacy advantage over a primitives-only baseline equipped with the
`skill-librarian` write loop. This is the kill-switch experiment for the
Memento-Skills integration (see `MEMENTO_SKILLS_PLAN.md` Phase 4).

## The Experiment

Two configurations run the same task set:

| Config   | Packages loaded                                           | Librarian | Router |
| -------- | --------------------------------------------------------- | --------- | ------ |
| **A**    | Full armory (106+ packages)                               | Passive   | Active |
| **B**    | Primitives only: `web-fetch`, `bash`, `filesystem`, `tavily` | Active    | —      |

Config A measures the curated library's zero-shot performance.
Config B measures what the write loop can grow from scratch on the same tasks.

**Exit criterion (S3 in the plan):** Config A must beat Config B by ≥15
percentage points on pass rate. If Config B converges toward Config A, that
is itself a validation signal for the curation effort — document it.

## Layout

```
evals/skillsbench/
├── README.md          # this file
├── schema.yaml        # task YAML schema reference
├── tasks/             # seed task set (expand before full runs)
│   ├── task_001_*.yaml
│   └── ...
└── results/           # per-run output (gitignored)
    └── YYYY-MM-DD-run-N.json
```

## Running the Benchmark

**Status:** harness ready, seed task set partial. **Full execution is deferred
to the operator** — a meaningful run requires hours of live `claude -p`
execution and should be scheduled with budget awareness.

```bash
# Single task, dry-run (validates harness without live execution)
uv run python scripts/run_skillsbench.py --task evals/skillsbench/tasks/task_001_*.yaml --dry-run

# Full sweep, Config A only
uv run python scripts/run_skillsbench.py --config A --all

# Full sweep, both configs, 3 runs each, median verdict
uv run python scripts/run_skillsbench.py --all --runs 3

# Operator workflow for comparison
uv run python scripts/run_skillsbench.py --all --config A --output results/run-A.json
uv run python scripts/run_skillsbench.py --all --config B --output results/run-B.json
uv run python scripts/run_skillsbench.py --compare results/run-A.json results/run-B.json
```

## Task Set Scope

The current seed set is **5 synthetic integration tasks** chosen to exercise
different armory capabilities without requiring external APIs or human
judgment for scoring. Before running a verdict-bearing benchmark, expand to
at least 50 tasks — the plan calls for GAIA-public samples plus additional
synthetic tasks, but GAIA sampling is deferred until the harness has been
validated on the seed set.

Tasks in the seed set all use the `assertion` success criterion, which
checks the model's final output against a list of regex/contains rules with
weights. More complex tasks (multi-file edits, artifact checks) should add
new criterion types rather than shoehorning into this schema.

## What This Does Not Measure

- **Cost efficiency** — token and time totals are logged but are not part of
  the pass/fail criterion.
- **Code quality of generated artifacts** — only the final assistant response
  is scored against assertions. Tasks requiring artifact quality checks need
  a richer success criterion type.
- **Librarian drafting quality** — the librarian's drafted skills during
  Config B runs are captured but their correctness is not benchmarked here.
  That belongs to `package-evaluator`, not SkillsBench.

## Gotchas

- **Worktree isolation is required for Config B.** The librarian writes new
  skill files during the run. Without worktree isolation, those writes
  contaminate the live repo. The harness spawns `claude -p` inside a fresh
  worktree per task.
- **Non-determinism.** A single run per task is not a verdict — the plan
  specifies median of 3 runs. The harness supports `--runs N` for this.
- **Context window.** Long tasks may exceed the default context limit. The
  harness fails such tasks loudly rather than silently truncating.

## Reference

- `scripts/run_skillsbench.py` — harness implementation
- `scripts/build_router_index.py` — Config A router index (must be fresh)
- `agents/skill-librarian/AGENT.md` — Config B write-loop agent
- `MEMENTO_SKILLS_PLAN.md` Phase 4 — exit criteria and analysis plan
