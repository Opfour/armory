#!/usr/bin/env python3
"""Sync shared template files into consuming package directories."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.package_types import REPO_ROOT

TEMPLATES_DIR = REPO_ROOT / "_templates"

TEMPLATE_CONSUMERS: dict[str, list[str]] = {
    "detection-patterns.md": ["skills/humanize", "skills/linkedin-post-style", "skills/manuscript-review"],
    "project-detection.md": ["skills/ship-workflow", "skills/plan-review", "skills/qa-systematic"],
}


def sync_template(template_name: str, consumers: list[str]) -> list[str]:
    """Sync a single template to all its consumers. Returns list of updated paths."""
    source = TEMPLATES_DIR / template_name
    if not source.exists():
        print(f"  skip: {template_name} (template not yet created)", file=sys.stderr)
        return []

    source_content = source.read_bytes()
    updated: list[str] = []

    for consumer in consumers:
        target_dir = REPO_ROOT / consumer / "references"
        target = target_dir / template_name

        if target.exists() and target.read_bytes() == source_content:
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        rel = target.relative_to(REPO_ROOT)
        updated.append(str(rel))
        print(f"  synced: {rel}")

    return updated


def main() -> int:
    """Sync all templates to their consumers."""
    all_updated: list[str] = []

    for template_name, consumers in TEMPLATE_CONSUMERS.items():
        updated = sync_template(template_name, consumers)
        all_updated.extend(updated)

    if all_updated:
        print(f"\n{len(all_updated)} file(s) updated — re-stage and commit")
        return 1

    print("All templates in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
