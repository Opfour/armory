#!/usr/bin/env python3
"""Shared frontmatter parsing utilities for armory package definitions."""
from __future__ import annotations

import re
from typing import Any

import yaml


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from a package definition file."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        raise ValueError("No valid YAML frontmatter found")
    return yaml.safe_load(match.group(1))


def extract_version(meta: dict[str, Any]) -> str:
    """Extract version from metadata.version (preferred) or top-level version (legacy)."""
    metadata = meta.get("metadata")
    if isinstance(metadata, dict) and metadata.get("version"):
        return str(metadata["version"])
    return str(meta.get("version", ""))


def extract_body(content: str) -> str:
    """Extract body content after frontmatter closing '---'."""
    match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", content, re.DOTALL)
    return match.group(1) if match else content


def validate_version(version: str) -> bool:
    """Validate semver format: X.Y.Z (digits only, no pre-release tags)."""
    return bool(re.match(r"^\d+\.\d+\.\d+$", version))
