#!/usr/bin/env python3
"""Backward-compatible wrapper — use scripts/package.py instead."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.package import main, package_skill
from scripts.package import validate_frontmatter as _validate_frontmatter
from scripts.frontmatter import parse_frontmatter
from scripts.frontmatter import extract_version as _extract_version_str
from scripts.frontmatter import validate_version as _validate_version_bool
from scripts.package_types import TYPES, should_exclude

# Re-export for backward compatibility
is_excluded = should_exclude


def extract_version(meta: dict[str, Any]) -> str | None:
    """Backward-compatible extract_version that returns None instead of empty string."""
    result = _extract_version_str(meta)
    return result if result else None


def validate_version(version: str) -> None:
    """Backward-compatible validate_version that raises on failure."""
    if not _validate_version_bool(version):
        raise ValueError(f"Invalid version '{version}' — must be semver (e.g. 1.0.0)")


def validate_frontmatter(skill_dir: Path) -> dict[str, Any]:
    """Backward-compatible skill-only frontmatter validation."""
    return _validate_frontmatter(skill_dir, TYPES["skill"])

__all__ = [
    "extract_version",
    "is_excluded",
    "main",
    "package_skill",
    "parse_frontmatter",
    "validate_frontmatter",
    "validate_version",
]

if __name__ == "__main__":
    sys.exit(main())
