#!/usr/bin/env python3
"""SkillsBench harness — bootstrap benchmark for Memento-Skills integration.

Loads tasks from ``evals/skillsbench/tasks/``, executes them against a live
Claude session in one of two configurations (A: full armory, B: primitives
only), and scores the output against each task's assertion rules.

This module contains three layers:

1. **Pure logic** (task loading, validation, assertion scoring, result
   aggregation) — fully unit-tested in ``tests/test_run_skillsbench.py``.
2. **Execution orchestration** (spawning ``claude -p``, worktree isolation,
   per-run capture) — gated behind the ``--live`` flag because it requires
   an installed ``claude`` CLI and burns real budget. Dry-run mode exercises
   only the pure logic for CI.
3. **Comparison and reporting** — reads two result files and reports the
   Config A vs Config B delta against the S3 exit criterion (≥15pp).

See ``evals/skillsbench/README.md`` for the experiment design. Full
execution is deferred to the operator — a meaningful benchmark requires
hours of live execution and should be scheduled deliberately.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

_SUPPORTED_CRITERION_TYPES = {"assertion"}
_SUPPORTED_ASSERTION_TYPES = {"contains", "not_contains", "matches_regex"}

# Tolerance for floating-point comparisons in compare_reports. Pass-rate
# subtractions like 0.70 - 0.60 produce values slightly below 0.10 in
# IEEE-754, which would incorrectly fail a threshold of exactly 0.10.
# One microunit (1e-6 percentage points) is small enough to be
# semantically irrelevant and large enough to absorb FP error.
_COMPARE_TOLERANCE_PP = 1e-6


@dataclass
class TaskDefinition:
    """A single SkillsBench task loaded from YAML."""

    id: str
    description: str
    category: str
    difficulty: str
    prompt: str
    assertions: list[dict]
    pass_threshold: float
    max_turns: int
    max_tokens: int
    timeout_seconds: int
    tags: list[str]
    source_path: str


@dataclass
class TaskRunResult:
    """Result of running a single task in a single configuration."""

    task_id: str
    config: str
    attempt: int
    verdict: str  # "pass" | "fail" | "error" | "skipped"
    weighted_score: float
    output_excerpt: str
    assertion_results: list[dict]
    execution_time_ms: int
    error: str | None = None


@dataclass
class BenchmarkReport:
    """Aggregated report across all tasks in one configuration."""

    config: str
    timestamp: str
    total_tasks: int
    passed: int
    failed: int
    errored: int
    skipped: int
    pass_rate: float
    mean_score: float
    per_task: list[TaskRunResult] = field(default_factory=list)


def load_task(path: Path) -> TaskDefinition:
    """Load and validate a task YAML file.

    Args:
        path: Path to a task YAML under evals/skillsbench/tasks/.

    Returns:
        Parsed TaskDefinition.

    Raises:
        ValueError: If the file is missing required fields or uses an
            unsupported criterion or assertion type.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")

    required = {"id", "description", "category", "prompt", "success_criterion", "limits"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"{path}: missing required fields: {sorted(missing)}")

    if raw["id"] != path.stem:
        raise ValueError(
            f"{path}: task id {raw['id']!r} must match filename stem {path.stem!r}"
        )

    criterion = raw["success_criterion"]
    if criterion.get("type") not in _SUPPORTED_CRITERION_TYPES:
        raise ValueError(
            f"{path}: unsupported criterion type {criterion.get('type')!r} "
            f"(supported: {sorted(_SUPPORTED_CRITERION_TYPES)})"
        )

    assertions = criterion.get("assertions") or []
    if not assertions:
        raise ValueError(f"{path}: criterion has no assertions")
    for idx, assertion in enumerate(assertions):
        if assertion.get("type") not in _SUPPORTED_ASSERTION_TYPES:
            raise ValueError(
                f"{path}: assertion {idx} has unsupported type {assertion.get('type')!r}"
            )
        if "target" not in assertion or "weight" not in assertion:
            raise ValueError(
                f"{path}: assertion {idx} missing 'target' or 'weight'"
            )

    limits = raw["limits"]
    return TaskDefinition(
        id=raw["id"],
        description=raw["description"],
        category=raw["category"],
        difficulty=raw.get("difficulty", "medium"),
        prompt=raw["prompt"],
        assertions=assertions,
        pass_threshold=float(criterion.get("pass_threshold", 0.7)),
        max_turns=int(limits.get("max_turns", 5)),
        max_tokens=int(limits.get("max_tokens", 10000)),
        timeout_seconds=int(limits.get("timeout_seconds", 180)),
        tags=list(raw.get("tags") or []),
        source_path=str(path),
    )


def load_task_set(tasks_dir: Path) -> list[TaskDefinition]:
    """Load every YAML task under a directory, sorted by id."""
    if not tasks_dir.is_dir():
        return []
    tasks: list[TaskDefinition] = []
    for path in sorted(tasks_dir.glob("*.yaml")):
        tasks.append(load_task(path))
    return tasks


def check_assertions(
    output: str,
    assertions: list[dict],
) -> tuple[float, list[dict]]:
    """Score output against a task's assertions.

    Args:
        output: The assistant's final output text.
        assertions: Parsed assertion list from a task definition.

    Returns:
        A tuple of (weighted_score, per_assertion_detail). The score is
        the sum of weights for passing assertions divided by the sum of
        all weights (so the score is in ``[0.0, 1.0]`` regardless of
        whether the weights themselves sum to 1).
    """
    total_weight = sum(float(a["weight"]) for a in assertions)
    if total_weight <= 0:
        return 0.0, []

    passed_weight = 0.0
    details: list[dict] = []
    for assertion in assertions:
        a_type = assertion["type"]
        target = str(assertion["target"])
        weight = float(assertion["weight"])
        passed = _check_assertion(output, a_type, target)
        if passed:
            passed_weight += weight
        details.append(
            {
                "type": a_type,
                "target": target,
                "weight": weight,
                "passed": passed,
            }
        )

    return passed_weight / total_weight, details


def _check_assertion(output: str, a_type: str, target: str) -> bool:
    """Evaluate one assertion against output text.

    Args:
        output: Assistant output to check.
        a_type: Assertion type (contains, not_contains, matches_regex).
        target: Literal or regex target per assertion type.

    Returns:
        True if the assertion passes.
    """
    if a_type == "contains":
        return target in output
    if a_type == "not_contains":
        return target not in output
    if a_type == "matches_regex":
        return re.search(target, output) is not None
    raise ValueError(f"unsupported assertion type: {a_type}")


def verdict_from_score(score: float, threshold: float) -> str:
    """Convert a weighted score into a pass/fail verdict."""
    return "pass" if score >= threshold else "fail"


def aggregate_report(
    config: str,
    results: list[TaskRunResult],
) -> BenchmarkReport:
    """Aggregate per-task results into a BenchmarkReport.

    When a task has multiple attempts, only the median-scored attempt is
    used for the aggregate (matches the plan's "median of 3 runs" rule).
    """
    by_task: dict[str, list[TaskRunResult]] = {}
    for r in results:
        by_task.setdefault(r.task_id, []).append(r)

    median_attempts: list[TaskRunResult] = []
    for attempts in by_task.values():
        sorted_attempts = sorted(attempts, key=lambda r: r.weighted_score)
        median_attempts.append(sorted_attempts[len(sorted_attempts) // 2])

    total = len(median_attempts)
    passed = sum(1 for r in median_attempts if r.verdict == "pass")
    failed = sum(1 for r in median_attempts if r.verdict == "fail")
    errored = sum(1 for r in median_attempts if r.verdict == "error")
    skipped = sum(1 for r in median_attempts if r.verdict == "skipped")
    pass_rate = passed / total if total > 0 else 0.0
    mean_score = (
        sum(r.weighted_score for r in median_attempts) / total if total > 0 else 0.0
    )

    return BenchmarkReport(
        config=config,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        total_tasks=total,
        passed=passed,
        failed=failed,
        errored=errored,
        skipped=skipped,
        pass_rate=pass_rate,
        mean_score=mean_score,
        per_task=median_attempts,
    )


def compare_reports(
    report_a: BenchmarkReport,
    report_b: BenchmarkReport,
    min_delta_pp: float = 15.0,
) -> dict:
    """Compare two configuration reports against the S3 exit criterion.

    Args:
        report_a: Config A report (armory-loaded).
        report_b: Config B report (primitives-only).
        min_delta_pp: Required percentage-point advantage for Config A.
            Default 15.0 matches the plan's S3 threshold.

    Returns:
        Dict with the delta, verdict, and supporting numbers.
    """
    delta_pp = (report_a.pass_rate - report_b.pass_rate) * 100
    s3_met = delta_pp + _COMPARE_TOLERANCE_PP >= min_delta_pp
    return {
        "config_a_pass_rate": report_a.pass_rate,
        "config_b_pass_rate": report_b.pass_rate,
        "delta_pp": delta_pp,
        "min_delta_pp": min_delta_pp,
        "s3_exit_met": s3_met,
        "verdict": "curation_validated" if s3_met else "thesis_unconfirmed",
        "total_tasks_a": report_a.total_tasks,
        "total_tasks_b": report_b.total_tasks,
    }


def run_task_live(
    task: TaskDefinition,
    config: str,
    allowed_tools: list[str] | None = None,
) -> TaskRunResult:
    """Execute a single task against a live ``claude`` session.

    **Operator note:** this function actually spawns ``claude -p`` and
    burns budget. Guard calls behind the ``--live`` CLI flag. The pure
    logic above (loading, scoring, aggregation) is what the unit tests
    exercise; this function is only covered by integration runs.

    Args:
        task: The task to run.
        config: ``"A"`` or ``"B"`` — used only for labeling the result.
        allowed_tools: Explicit tool allowlist for ``claude -p``. If
            ``None``, defaults to a broad read-only set; Config B runs
            should restrict to the primitives.

    Returns:
        A TaskRunResult with the verdict and captured output excerpt.
    """
    start_ms = time.monotonic_ns() // 1_000_000
    tools = allowed_tools or ["Read", "Glob", "Grep", "Bash", "WebFetch"]
    tmpdir = tempfile.mkdtemp(prefix="skillsbench_")
    try:
        result = subprocess.run(
            [
                "claude",
                "-p", task.prompt,
                "--output-format", "text",
                "--allowedTools", *tools,
            ],
            capture_output=True,
            text=True,
            timeout=task.timeout_seconds,
            cwd=tmpdir,
        )
        output = result.stdout or ""
        error: str | None = None
        if result.returncode != 0:
            error = f"claude returncode={result.returncode}: {result.stderr[:500]}"
    except subprocess.TimeoutExpired:
        output = ""
        error = f"timed out after {task.timeout_seconds}s"
    except FileNotFoundError:
        output = ""
        error = "'claude' CLI not found in PATH"

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    if error:
        return TaskRunResult(
            task_id=task.id,
            config=config,
            attempt=1,
            verdict="error",
            weighted_score=0.0,
            output_excerpt="",
            assertion_results=[],
            execution_time_ms=elapsed_ms,
            error=error,
        )

    score, details = check_assertions(output, task.assertions)
    return TaskRunResult(
        task_id=task.id,
        config=config,
        attempt=1,
        verdict=verdict_from_score(score, task.pass_threshold),
        weighted_score=score,
        output_excerpt=output[:2000],
        assertion_results=details,
        execution_time_ms=elapsed_ms,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the SkillsBench bootstrap benchmark",
    )
    parser.add_argument(
        "--tasks-dir",
        default="evals/skillsbench/tasks",
        help="Directory of task YAML files",
    )
    parser.add_argument(
        "--task",
        help="Run a single task by path (mutually exclusive with --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every task under --tasks-dir",
    )
    parser.add_argument(
        "--config",
        choices=["A", "B"],
        default="A",
        help="A: full armory, B: primitives only + librarian",
    )
    parser.add_argument(
        "--output",
        default="evals/skillsbench/results/latest.json",
        help="Path to write the benchmark report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load tasks and validate schema without running claude",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually invoke claude -p (otherwise dry-run is implied)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("REPORT_A", "REPORT_B"),
        help="Compare two saved reports and print the S3 verdict",
    )
    args = parser.parse_args()

    if args.compare:
        return _compare_command(args.compare[0], args.compare[1])

    if not args.task and not args.all:
        parser.error("one of --task or --all is required")

    if args.task:
        tasks = [load_task(_REPO_ROOT / args.task)]
    else:
        tasks = load_task_set(_REPO_ROOT / args.tasks_dir)

    if not tasks:
        print(f"No tasks found in {args.tasks_dir}", file=sys.stderr)
        return 1

    if args.dry_run or not args.live:
        print(f"Loaded {len(tasks)} task(s) for config {args.config}")
        print("Dry run — no tasks executed. Pass --live to actually run claude -p.")
        for t in tasks:
            print(f"  - {t.id} ({t.category}/{t.difficulty}): {t.description}")
        return 0

    allowed_tools: list[str] | None
    if args.config == "B":
        allowed_tools = ["Read", "Glob", "Grep", "Bash", "WebFetch"]
    else:
        allowed_tools = None

    results: list[TaskRunResult] = []
    for task in tasks:
        print(f"Running {task.id} [{args.config}]...")
        result = run_task_live(task, args.config, allowed_tools=allowed_tools)
        results.append(result)
        print(f"  verdict={result.verdict} score={result.weighted_score:.2f}")

    report = aggregate_report(args.config, results)
    output_path = _REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(report), indent=2), encoding="utf-8"
    )
    print(
        f"Report written to {args.output} "
        f"(pass_rate={report.pass_rate:.2%}, mean_score={report.mean_score:.2f})"
    )
    return 0 if report.failed == 0 and report.errored == 0 else 1


def _compare_command(path_a: str, path_b: str) -> int:
    """Implement the ``--compare`` subcommand."""
    data_a = json.loads((_REPO_ROOT / path_a).read_text(encoding="utf-8"))
    data_b = json.loads((_REPO_ROOT / path_b).read_text(encoding="utf-8"))
    report_a = BenchmarkReport(
        config=data_a["config"],
        timestamp=data_a["timestamp"],
        total_tasks=data_a["total_tasks"],
        passed=data_a["passed"],
        failed=data_a["failed"],
        errored=data_a["errored"],
        skipped=data_a["skipped"],
        pass_rate=data_a["pass_rate"],
        mean_score=data_a["mean_score"],
    )
    report_b = BenchmarkReport(
        config=data_b["config"],
        timestamp=data_b["timestamp"],
        total_tasks=data_b["total_tasks"],
        passed=data_b["passed"],
        failed=data_b["failed"],
        errored=data_b["errored"],
        skipped=data_b["skipped"],
        pass_rate=data_b["pass_rate"],
        mean_score=data_b["mean_score"],
    )
    comparison = compare_reports(report_a, report_b)
    print(json.dumps(comparison, indent=2))
    return 0 if comparison["s3_exit_met"] else 2


if __name__ == "__main__":
    sys.exit(main())
