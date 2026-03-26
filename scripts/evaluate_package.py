#!/usr/bin/env python3
"""Standalone CI-compatible package quality evaluator.

Scores packages across 6 dimensions and fails if the score is below
threshold or any CRITICAL finding exists.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

from scripts.frontmatter import extract_body, extract_version, parse_frontmatter, validate_version
from scripts.package_types import REPO_ROOT, TYPES, PackageType

DIMENSION_NAMES = [
    "D1 Frontmatter Quality",
    "D2 Trigger Coverage",
    "D3 Structural Completeness",
    "D4 Content Depth",
    "D5 Consistency",
    "D6 Compliance",
]

MAX_SCORES: dict[str, int] = {
    "D1 Frontmatter Quality": 20,
    "D2 Trigger Coverage": 18,
    "D3 Structural Completeness": 20,
    "D4 Content Depth": 22,
    "D5 Consistency": 12,
    "D6 Compliance": 8,
}


def _count_quoted_triggers(description: str) -> int:
    """Count quoted trigger phrases like "some trigger" in description."""
    return len(re.findall(r'"[^"]{2,}"', description))


def _has_trigger_phrases(description: str) -> bool:
    """Check if description contains 'Trigger' or quoted trigger patterns."""
    if "Trigger" in description:
        return True
    return _count_quoted_triggers(description) > 0


def _has_use_clause(description: str) -> bool:
    """Check for 'Use this' or 'Use when' clause."""
    return bool(re.search(r"Use\s+(this|when)", description))


def _body_word_count(body: str) -> int:
    return len(body.split())


def _has_heading_pattern(body: str, pattern: str) -> bool:
    return bool(re.search(rf"^#+\s+.*({pattern})", body, re.MULTILINE | re.IGNORECASE))


def _has_code_blocks(body: str) -> bool:
    return "```" in body


def _has_tables(body: str) -> bool:
    return bool(re.search(r"\|---", body))


def _has_numbered_lists(body: str) -> bool:
    return bool(re.search(r"^\s*\d+\.\s+", body, re.MULTILINE))


def _is_kebab_case(name: str) -> bool:
    return bool(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name))


def _has_cross_package_refs(body: str) -> bool:
    return "../" in body


def _has_references_dir(pkg_dir: Path) -> bool:
    ref_dir = pkg_dir / "references"
    if not ref_dir.is_dir():
        return False
    return any(ref_dir.iterdir())


def evaluate_package(
    pkg_dir: Path, pkg_type: PackageType,
) -> dict[str, object]:
    """Evaluate a single package and return scoring results."""
    name = pkg_dir.name
    definition = pkg_dir / pkg_type.definition_file

    scores: dict[str, int] = {d: 0 for d in DIMENSION_NAMES}
    findings: list[dict[str, str]] = []

    # --- Parse frontmatter and body ---
    meta: dict[str, object] | None = None
    body = ""
    description = ""
    version_str = ""
    yaml_valid = False

    if not definition.exists():
        findings.append({"severity": "CRITICAL", "message": f"Missing definition file {pkg_type.definition_file}"})
    else:
        content = definition.read_text(encoding="utf-8")
        try:
            meta = parse_frontmatter(content)
            yaml_valid = True
            body = extract_body(content)
            description = str(meta.get("description", "")) if isinstance(meta, dict) else ""
            version_str = extract_version(meta) if isinstance(meta, dict) else ""
        except (ValueError, yaml.YAMLError) as exc:
            findings.append({"severity": "CRITICAL", "message": f"Invalid YAML frontmatter: {exc}"})

    # Check required frontmatter fields
    if meta is not None and isinstance(meta, dict):
        for field in pkg_type.required_frontmatter:
            if not meta.get(field):
                findings.append({"severity": "CRITICAL", "message": f"Missing required frontmatter field: {field}"})

    # ========== D1: Frontmatter Quality (20) ==========
    desc_len = len(description)
    if 200 <= desc_len <= 1024:
        scores["D1 Frontmatter Quality"] += 10
    elif 50 <= desc_len < 200:
        scores["D1 Frontmatter Quality"] += 5
    else:
        findings.append({"severity": "HIGH", "message": f"Description length {desc_len} outside ideal range (200-1024)"})

    if _has_trigger_phrases(description):
        scores["D1 Frontmatter Quality"] += 5
    else:
        findings.append({"severity": "HIGH", "message": "No trigger phrases in description"})

    if _has_use_clause(description):
        scores["D1 Frontmatter Quality"] += 5

    # ========== D2: Trigger Coverage (18) ==========
    trigger_count = _count_quoted_triggers(description)
    if trigger_count >= 6:
        scores["D2 Trigger Coverage"] = 18
    elif trigger_count >= 3:
        scores["D2 Trigger Coverage"] = 12
    elif trigger_count >= 1:
        scores["D2 Trigger Coverage"] = 6
    else:
        findings.append({"severity": "HIGH", "message": "No quoted trigger phrases found"})

    # ========== D3: Structural Completeness (20) ==========
    if _has_heading_pattern(body, r"Step|Phase|Workflow|Stage"):
        scores["D3 Structural Completeness"] += 8
    else:
        findings.append({"severity": "HIGH", "message": "No workflow/phases section found"})

    if _has_heading_pattern(body, r"Error|Troubleshoot"):
        scores["D3 Structural Completeness"] += 4

    if _has_heading_pattern(body, r"Output"):
        scores["D3 Structural Completeness"] += 4

    if _has_references_dir(pkg_dir):
        scores["D3 Structural Completeness"] += 4

    # ========== D4: Content Depth (22) ==========
    wc = _body_word_count(body)
    if wc > 500:
        scores["D4 Content Depth"] += 10
    elif wc > 200:
        scores["D4 Content Depth"] += 5

    if _has_code_blocks(body):
        scores["D4 Content Depth"] += 4

    if _has_tables(body):
        scores["D4 Content Depth"] += 4

    if _has_numbered_lists(body):
        scores["D4 Content Depth"] += 4

    # ========== D5: Consistency & Integrity (12) ==========
    fm_name = str(meta.get("name", "")) if isinstance(meta, dict) else ""
    if fm_name == name:
        scores["D5 Consistency"] += 6
    else:
        findings.append({"severity": "CRITICAL", "message": f"Frontmatter name '{fm_name}' does not match directory '{name}'"})

    if not _has_cross_package_refs(body):
        scores["D5 Consistency"] += 3

    if version_str and validate_version(version_str):
        scores["D5 Consistency"] += 3

    # ========== D6: CONTRIBUTING Compliance (8) ==========
    if _is_kebab_case(name):
        scores["D6 Compliance"] += 4

    if len(name) <= 64:
        scores["D6 Compliance"] += 2

    if yaml_valid:
        scores["D6 Compliance"] += 2

    # --- Compute totals ---
    total = sum(scores.values())
    max_total = sum(MAX_SCORES.values())

    has_critical = any(f["severity"] == "CRITICAL" for f in findings)
    if has_critical:
        capped = int(max_total * 0.4)
        total = min(total, capped)

    percentage = int(total / max_total * 100)

    return {
        "name": name,
        "type": pkg_type.key,
        "scores": scores,
        "max_scores": dict(MAX_SCORES),
        "total": total,
        "percentage": percentage,
        "status": "FAIL" if has_critical else "PASS",
        "findings": findings,
    }


def evaluate_all(threshold: int) -> list[dict[str, object]]:
    """Evaluate all packages across all types."""
    results: list[dict[str, object]] = []
    for pkg_type in TYPES.values():
        type_dir = pkg_type.repo_dir
        if not type_dir.exists():
            continue
        for pkg_dir in sorted(type_dir.iterdir()):
            if not pkg_dir.is_dir() or pkg_dir.name.startswith("."):
                continue
            definition = pkg_dir / pkg_type.definition_file
            if not definition.exists():
                continue
            result = evaluate_package(pkg_dir, pkg_type)
            if result["percentage"] < threshold:  # type: ignore[operator]
                result["status"] = "FAIL"
            results.append(result)
    return results


def evaluate_single(path: str, threshold: int) -> list[dict[str, object]]:
    """Evaluate a single package by path."""
    from scripts.package_types import detect_type_from_path

    pkg_dir = Path(path).resolve()
    if not pkg_dir.is_dir():
        pkg_dir = REPO_ROOT / path
    if not pkg_dir.is_dir():
        print(f"Error: path '{path}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    pkg_type = detect_type_from_path(pkg_dir)
    result = evaluate_package(pkg_dir, pkg_type)
    if result["percentage"] < threshold:  # type: ignore[operator]
        result["status"] = "FAIL"
    return [result]


def print_text(results: list[dict[str, object]]) -> None:
    """Print results in human-readable text format."""
    for r in results:
        scores = r["scores"]
        max_scores = r["max_scores"]
        assert isinstance(scores, dict)
        assert isinstance(max_scores, dict)

        print(f"Package: {r['name']} ({r['type']})")
        for dim in DIMENSION_NAMES:
            label = f"  {dim}:"
            value = f"{scores[dim]}/{max_scores[dim]}"
            print(f"{label:<36s}{value:>6s}")
        print(f"  {'Overall:':<34s}{r['total']}/{sum(max_scores.values())} ({r['percentage']}%)")
        print(f"  Status: {r['status']}")
        if r["findings"]:
            findings = r["findings"]
            assert isinstance(findings, list)
            for f in findings:
                assert isinstance(f, dict)
                print(f"    [{f['severity']}] {f['message']}")
        print()

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    print(f"Summary: {len(results)} packages evaluated, {passed} passed, {failed} failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate package quality")
    parser.add_argument("--path", type=str, help="Evaluate a single package by path")
    parser.add_argument("--threshold", type=int, default=70, help="Minimum passing score (default: 70)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output JSON instead of text")
    args = parser.parse_args()

    if args.path:
        results = evaluate_single(args.path, args.threshold)
    else:
        results = evaluate_all(args.threshold)

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        print_text(results)

    has_failure = any(r["status"] == "FAIL" for r in results)
    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
