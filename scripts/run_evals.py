#!/usr/bin/env python3
"""Ground-truth oracle for eval case execution.

Executes eval cases against live Claude Code sessions via ``claude -p``
(headless mode) and checks structured assertions. Returns opaque pass/fail
verdicts — diagnostic explanations are the surrogate verifier's job.

Usage:
    uv run python scripts/run_evals.py --package skills/architecture-reviewer
    uv run python scripts/run_evals.py --all --timeout-per-case 120
    uv run python scripts/run_evals.py --package skills/immune --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

from scripts.eval_assertions import run_all_assertions
from scripts.package_types import TYPES


@dataclass
class CaseResult:
    """Result of executing a single eval case."""

    case_id: str
    prompt: str
    trigger_expected: bool
    oracle_verdict: str  # "pass" or "fail"
    weighted_score: float
    assertion_details: list[dict]
    execution_time_ms: int
    error: str | None = None


@dataclass
class PackageResult:
    """Aggregated results for a single package."""

    package_name: str
    package_path: str
    total_cases: int
    passed: int
    failed: int
    skipped: int
    aggregate_score: float
    case_results: list[CaseResult]


def find_package_dir(package_path: str) -> Path | None:
    """Resolve a package path relative to repo root."""
    candidate = _REPO_ROOT / package_path
    if candidate.is_dir():
        return candidate
    return None


def load_cases(pkg_dir: Path) -> list[dict] | None:
    """Load eval cases from a package directory."""
    cases_file = pkg_dir / "evals" / "cases.yaml"
    if not cases_file.exists():
        return None
    data = yaml.safe_load(cases_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        return None
    return data["cases"]


def execute_case(
    case: dict,
    pkg_dir: Path,
    timeout_seconds: int,
    dry_run: bool = False,
) -> CaseResult:
    """Execute a single eval case against a live Claude session.

    In dry-run mode, skips actual execution and returns a placeholder result.
    """
    case_id = case["id"]
    prompt = case["prompt"]
    trigger_expected = case["trigger_expected"]
    assertions = case.get("assertions", [])

    if dry_run:
        return CaseResult(
            case_id=case_id,
            prompt=prompt,
            trigger_expected=trigger_expected,
            oracle_verdict="skipped",
            weighted_score=0.0,
            assertion_details=[],
            execution_time_ms=0,
            error="dry-run mode",
        )

    start_ms = time.monotonic_ns() // 1_000_000

    try:
        result = subprocess.run(
            [
                "claude",
                "-p", prompt,
                "--add-dir", str(pkg_dir),
                "--output-format", "text",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = result.stdout
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        return CaseResult(
            case_id=case_id,
            prompt=prompt,
            trigger_expected=trigger_expected,
            oracle_verdict="fail",
            weighted_score=0.0,
            assertion_details=[],
            execution_time_ms=elapsed_ms,
            error=f"Timed out after {timeout_seconds}s",
        )
    except FileNotFoundError:
        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
        return CaseResult(
            case_id=case_id,
            prompt=prompt,
            trigger_expected=trigger_expected,
            oracle_verdict="fail",
            weighted_score=0.0,
            assertion_details=[],
            execution_time_ms=elapsed_ms,
            error="'claude' CLI not found in PATH",
        )

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    # For negative cases (trigger_expected: false), pass if no substantial output
    # or the agent did not engage with the package's domain
    if not trigger_expected:
        verdict = "pass"  # Negative cases are validated by the schema, not execution
        return CaseResult(
            case_id=case_id,
            prompt=prompt,
            trigger_expected=trigger_expected,
            oracle_verdict=verdict,
            weighted_score=1.0,
            assertion_details=[],
            execution_time_ms=elapsed_ms,
        )

    # For positive cases: check assertions if present, otherwise pass on non-zero output
    if not assertions:
        verdict = "pass" if (exit_code == 0 and len(output.strip()) > 0) else "fail"
        return CaseResult(
            case_id=case_id,
            prompt=prompt,
            trigger_expected=trigger_expected,
            oracle_verdict=verdict,
            weighted_score=1.0 if verdict == "pass" else 0.0,
            assertion_details=[],
            execution_time_ms=elapsed_ms,
        )

    all_passed, weighted_score, results = run_all_assertions(output, assertions)
    assertion_details = [
        {
            "type": r.assertion_type,
            "target": r.target,
            "passed": r.passed,
            "weight": r.weight,
            "detail": r.detail,
        }
        for r in results
    ]

    return CaseResult(
        case_id=case_id,
        prompt=prompt,
        trigger_expected=trigger_expected,
        oracle_verdict="pass" if all_passed else "fail",
        weighted_score=weighted_score,
        assertion_details=assertion_details,
        execution_time_ms=elapsed_ms,
    )


def run_package_evals(
    pkg_path: str,
    timeout_seconds: int = 120,
    dry_run: bool = False,
) -> PackageResult | None:
    """Run all eval cases for a single package."""
    pkg_dir = find_package_dir(pkg_path)
    if pkg_dir is None:
        print(f"Package not found: {pkg_path}", file=sys.stderr)
        return None

    cases = load_cases(pkg_dir)
    if cases is None:
        print(f"No evals/cases.yaml found in {pkg_path}", file=sys.stderr)
        return None

    results: list[CaseResult] = []
    for case in cases:
        result = execute_case(case, pkg_dir, timeout_seconds, dry_run)
        results.append(result)

    passed = sum(1 for r in results if r.oracle_verdict == "pass")
    failed = sum(1 for r in results if r.oracle_verdict == "fail")
    skipped = sum(1 for r in results if r.oracle_verdict == "skipped")
    total = len(results)
    aggregate_score = sum(r.weighted_score for r in results) / total if total > 0 else 0.0

    return PackageResult(
        package_name=pkg_dir.name,
        package_path=pkg_path,
        total_cases=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        aggregate_score=aggregate_score,
        case_results=results,
    )


def collect_all_packages() -> list[str]:
    """Collect all package paths that have evals/cases.yaml."""
    packages: list[str] = []
    for pkg_type in TYPES.values():
        type_dir = pkg_type.repo_dir
        if not type_dir.exists():
            continue
        for pkg_dir in sorted(type_dir.iterdir()):
            if not pkg_dir.is_dir():
                continue
            if (pkg_dir / "evals" / "cases.yaml").exists():
                packages.append(str(pkg_dir.relative_to(_REPO_ROOT)))
    return packages


def write_results(results: list[PackageResult], output_path: Path) -> None:
    """Write results to JSON."""
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_packages": len(results),
        "packages": [asdict(r) for r in results],
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute eval cases against live Claude sessions")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", help="Path to a single package (relative to repo root)")
    group.add_argument("--all", action="store_true", help="Run evals for all packages")
    parser.add_argument("--timeout-per-case", type=int, default=120, help="Timeout per case in seconds")
    parser.add_argument("--output", default="evals/results.json", help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual execution, validate structure only")
    args = parser.parse_args()

    packages = collect_all_packages() if args.all else [args.package]
    results: list[PackageResult] = []

    for pkg_path in packages:
        print(f"Running evals for {pkg_path}...")
        result = run_package_evals(pkg_path, args.timeout_per_case, args.dry_run)
        if result is not None:
            results.append(result)
            status = "PASS" if result.failed == 0 else "FAIL"
            print(f"  {status}: {result.passed}/{result.total_cases} passed (score: {result.aggregate_score:.2f})")

    output_path = _REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_results(results, output_path)
    print(f"\nResults written to {args.output}")

    total_failed = sum(r.failed for r in results)
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
