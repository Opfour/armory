#!/usr/bin/env python3
"""Skill misalignment detection.

Compares agent performance WITH vs WITHOUT each skill loaded to identify
skills that degrade output quality. Based on the EvoSkills finding that
some human-curated skills actively hurt performance (Natural Science: -18pp).

Usage:
    uv run python scripts/detect_misalignment.py --all --dry-run
    uv run python scripts/detect_misalignment.py --skill skills/architecture-reviewer
    uv run python scripts/detect_misalignment.py --all --threshold 5
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

from scripts.package_types import TYPES
from scripts.run_evals import execute_case, load_cases


@dataclass
class MisalignmentResult:
    """Misalignment analysis for a single skill."""

    skill_name: str
    skill_path: str
    cases_tested: int
    score_with_skill: float
    score_without_skill: float
    delta: float
    classification: str  # "helpful" | "neutral" | "harmful"
    details: list[dict]


def classify_delta(delta: float, threshold: float) -> str:
    """Classify a skill based on its performance delta.

    Args:
        delta: score_with - score_without (positive = skill helps)
        threshold: minimum delta to be classified as helpful/harmful
    """
    if delta >= threshold:
        return "helpful"
    if delta <= -threshold:
        return "harmful"
    return "neutral"


def has_assertions(cases: list[dict]) -> bool:
    """Check if any positive case has structured assertions."""
    return any(
        case.get("trigger_expected") is True and case.get("assertions")
        for case in cases
    )


def collect_skills_with_assertions() -> list[tuple[str, Path]]:
    """Find all skills that have eval cases with assertions."""
    skills_type = TYPES.get("skill")
    if skills_type is None:
        return []

    results: list[tuple[str, Path]] = []
    skills_dir = skills_type.repo_dir
    if not skills_dir.exists():
        return results

    for pkg_dir in sorted(skills_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue
        cases = load_cases(pkg_dir)
        if cases is not None and has_assertions(cases):
            rel_path = str(pkg_dir.relative_to(_REPO_ROOT))
            results.append((rel_path, pkg_dir))

    return results


def analyze_skill(
    skill_path: str,
    pkg_dir: Path,
    timeout_seconds: int,
    threshold: float,
    dry_run: bool = False,
) -> MisalignmentResult | None:
    """Analyze a single skill for misalignment."""
    cases = load_cases(pkg_dir)
    if cases is None:
        return None

    positive_cases = [c for c in cases if c.get("trigger_expected") is True and c.get("assertions")]
    if not positive_cases:
        return None

    details: list[dict] = []
    scores_with: list[float] = []
    scores_without: list[float] = []

    for case in positive_cases:
        if dry_run:
            # In dry-run, report structure without execution
            details.append({
                "case_id": case["id"],
                "score_with": 0.0,
                "score_without": 0.0,
                "delta": 0.0,
                "status": "dry-run",
            })
            scores_with.append(0.0)
            scores_without.append(0.0)
            continue

        # Run WITH skill
        result_with = execute_case(case, pkg_dir, timeout_seconds, dry_run=False)
        # Run WITHOUT skill (pass a non-existent dir to avoid loading the skill)
        result_without = execute_case(case, _REPO_ROOT, timeout_seconds, dry_run=False)

        scores_with.append(result_with.weighted_score)
        scores_without.append(result_without.weighted_score)
        details.append({
            "case_id": case["id"],
            "score_with": result_with.weighted_score,
            "score_without": result_without.weighted_score,
            "delta": result_with.weighted_score - result_without.weighted_score,
        })

    avg_with = sum(scores_with) / len(scores_with) if scores_with else 0.0
    avg_without = sum(scores_without) / len(scores_without) if scores_without else 0.0
    delta = avg_with - avg_without

    return MisalignmentResult(
        skill_name=pkg_dir.name,
        skill_path=skill_path,
        cases_tested=len(positive_cases),
        score_with_skill=round(avg_with, 4),
        score_without_skill=round(avg_without, 4),
        delta=round(delta, 4),
        classification=classify_delta(delta, threshold / 100),
        details=details,
    )


def write_report(results: list[MisalignmentResult], output_path: Path) -> None:
    """Write misalignment report to YAML."""
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_skills_analyzed": len(results),
        "classifications": {
            "helpful": sum(1 for r in results if r.classification == "helpful"),
            "neutral": sum(1 for r in results if r.classification == "neutral"),
            "harmful": sum(1 for r in results if r.classification == "harmful"),
        },
        "skills": [asdict(r) for r in results],
    }
    output_path.write_text(
        yaml.dump(report, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect skill misalignment (skills that hurt performance)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skill", help="Path to a single skill (relative to repo root)")
    group.add_argument("--all", action="store_true", help="Analyze all skills with assertions")
    parser.add_argument("--threshold", type=float, default=5.0, help="Delta threshold in percentage points (default: 5)")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per case in seconds")
    parser.add_argument("--output", default="misalignment-report.yaml", help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Report structure without executing")
    args = parser.parse_args()

    if args.all:
        skills = collect_skills_with_assertions()
        if not skills:
            print("No skills with structured assertions found. Add assertions to evals/cases.yaml first.")
            return 0
    else:
        pkg_dir = _REPO_ROOT / args.skill
        if not pkg_dir.is_dir():
            print(f"Skill not found: {args.skill}", file=sys.stderr)
            return 1
        skills = [(args.skill, pkg_dir)]

    results: list[MisalignmentResult] = []

    for skill_path, pkg_dir in skills:
        print(f"Analyzing {skill_path}...")
        result = analyze_skill(skill_path, pkg_dir, args.timeout, args.threshold, args.dry_run)
        if result is not None:
            results.append(result)
            icon = {"helpful": "+", "neutral": "=", "harmful": "!"}[result.classification]
            print(f"  [{icon}] {result.classification}: delta={result.delta:+.4f} "
                  f"(with={result.score_with_skill:.4f}, without={result.score_without_skill:.4f})")

    if not results:
        print("No skills with testable assertions found.")
        return 0

    output_path = _REPO_ROOT / args.output
    write_report(results, output_path)
    print(f"\nReport written to {args.output}")

    harmful = [r for r in results if r.classification == "harmful"]
    if harmful:
        print(f"\nWARNING: {len(harmful)} skill(s) may be degrading performance:")
        for r in harmful:
            print(f"  - {r.skill_name}: {r.delta:+.4f} delta")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
