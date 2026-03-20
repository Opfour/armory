#!/usr/bin/env python3
"""Validate eval cases.yaml files across all package types."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

from scripts.frontmatter import parse_frontmatter
from scripts.package_types import REPO_ROOT, TYPES, PackageType

REQUIRED_CASE_FIELDS = {"id", "prompt", "rubric", "trigger_expected"}


def is_deprecated(pkg_dir: Path, pkg_type: PackageType) -> bool:
    """Check if a package is deprecated by reading its definition file frontmatter."""
    definition = pkg_dir / pkg_type.definition_file
    if not definition.exists():
        return False
    try:
        text = definition.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        return (
            isinstance(meta, dict)
            and meta.get("metadata", {}).get("status") == "deprecated"
        )
    except (ValueError, yaml.YAMLError):
        return False


def validate_case(case: dict, pkg_name: str, idx: int) -> list[str]:
    """Validate a single eval case and return errors."""
    errors: list[str] = []
    prefix = f"{pkg_name} case #{idx}"

    missing = REQUIRED_CASE_FIELDS - set(case.keys())
    if missing:
        errors.append(f"{prefix}: missing required fields: {missing}")
        return errors

    if not isinstance(case["id"], str) or not case["id"]:
        errors.append(f"{prefix}: 'id' must be a non-empty string")

    if not isinstance(case["prompt"], str) or not case["prompt"].strip():
        errors.append(f"{prefix}: 'prompt' must be a non-empty string")

    if not isinstance(case["trigger_expected"], bool):
        errors.append(f"{prefix}: 'trigger_expected' must be a boolean")

    if not isinstance(case["rubric"], list) or len(case["rubric"]) == 0:
        errors.append(f"{prefix}: 'rubric' must be a non-empty list")

    return errors


def validate_pkg_evals(pkg_dir: Path, pkg_type: PackageType) -> list[str]:
    """Validate evals/cases.yaml for a single package."""
    cases_file = pkg_dir / "evals" / "cases.yaml"
    if not cases_file.exists():
        return []

    pkg_name = pkg_dir.name
    deprecated = is_deprecated(pkg_dir, pkg_type)
    errors: list[str] = []

    try:
        data = yaml.safe_load(cases_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"{pkg_name}: invalid YAML in cases.yaml: {e}"]

    if not isinstance(data, dict) or "cases" not in data:
        return [f"{pkg_name}: cases.yaml must have a top-level 'cases' key"]

    cases = data["cases"]
    if not isinstance(cases, list) or len(cases) == 0:
        return [f"{pkg_name}: 'cases' must be a non-empty list"]

    ids: set[str] = set()
    positive_count = 0
    negative_count = 0

    for i, case in enumerate(cases, 1):
        errors.extend(validate_case(case, pkg_name, i))

        case_id = case.get("id", "")
        if case_id in ids:
            errors.append(f"{pkg_name} case #{i}: duplicate id '{case_id}'")
        ids.add(case_id)

        if case.get("trigger_expected") is True:
            positive_count += 1
        elif case.get("trigger_expected") is False:
            negative_count += 1

    if deprecated:
        if positive_count > 0:
            errors.append(f"{pkg_name}: deprecated {pkg_type.key} must have 0 positive cases, found {positive_count}")
    else:
        if positive_count == 0:
            errors.append(f"{pkg_name}: must have at least 1 positive case (trigger_expected: true)")

    if negative_count < 2:
        errors.append(f"{pkg_name}: must have at least 2 negative cases (trigger_expected: false), found {negative_count}")

    return errors


def main() -> int:
    """Validate all eval cases across package types."""
    all_errors: list[str] = []
    counts: dict[str, int] = {}

    for pkg_type in TYPES.values():
        type_dir = pkg_type.repo_dir
        if not type_dir.exists():
            continue

        validated = 0
        for pkg_dir in sorted(type_dir.iterdir()):
            if not pkg_dir.is_dir():
                continue
            cases_file = pkg_dir / "evals" / "cases.yaml"
            if not cases_file.exists():
                continue

            errors = validate_pkg_evals(pkg_dir, pkg_type)
            all_errors.extend(errors)
            validated += 1

        if validated > 0:
            counts[pkg_type.manifest_section] = validated

    total = sum(counts.values())

    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) in {total} eval file(s):", file=sys.stderr)
        for error in all_errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    parts = [f"{count} {label}" for label, count in counts.items()]
    summary = ", ".join(parts) if parts else "0 packages"
    print(f"Validated {summary} — all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
