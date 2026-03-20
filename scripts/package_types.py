#!/usr/bin/env python3
"""Package type registry — single source of truth for all armory package types."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PackageType:
    """Metadata for a package type (skill, agent, hook, etc.)."""

    key: str
    dir_name: str
    definition_file: str
    install_subdir: str
    archive_ext: str
    required_frontmatter: tuple[str, ...]
    manifest_section: str

    @property
    def repo_dir(self) -> Path:
        return REPO_ROOT / self.dir_name


TYPES: dict[str, PackageType] = {
    "skill": PackageType(
        key="skill",
        dir_name="skills",
        definition_file="SKILL.md",
        install_subdir="skills",
        archive_ext=".skill",
        required_frontmatter=("name", "description"),
        manifest_section="skills",
    ),
    "agent": PackageType(
        key="agent",
        dir_name="agents",
        definition_file="AGENT.md",
        install_subdir="agents",
        archive_ext=".agent",
        required_frontmatter=("name", "description", "model", "color"),
        manifest_section="agents",
    ),
    "hook": PackageType(
        key="hook",
        dir_name="hooks",
        definition_file="HOOK.md",
        install_subdir="hooks",
        archive_ext=".hook",
        required_frontmatter=("name", "description", "hook"),
        manifest_section="hooks",
    ),
    "rule": PackageType(
        key="rule",
        dir_name="rules",
        definition_file="RULE.md",
        install_subdir="rules",
        archive_ext=".rule",
        required_frontmatter=("name", "description"),
        manifest_section="rules",
    ),
    "command": PackageType(
        key="command",
        dir_name="commands",
        definition_file="COMMAND.md",
        install_subdir="commands",
        archive_ext=".command",
        required_frontmatter=("name", "description"),
        manifest_section="commands",
    ),
    "utility": PackageType(
        key="utility",
        dir_name="utilities",
        definition_file="UTILITY.md",
        install_subdir="utilities",
        archive_ext=".utility",
        required_frontmatter=("name", "description", "utility"),
        manifest_section="utilities",
    ),
    "preset": PackageType(
        key="preset",
        dir_name="presets",
        definition_file="PRESET.md",
        install_subdir="presets",
        archive_ext=".preset",
        required_frontmatter=("name", "description", "preset"),
        manifest_section="presets",
    ),
}

MANIFEST_PATH = REPO_ROOT / "manifest.yaml"
LEGACY_MANIFEST_PATH = REPO_ROOT / "skills.yaml"

EXCLUDE_NAMES: frozenset[str] = frozenset({
    "__pycache__", "node_modules", ".DS_Store", ".git", "evals",
})
EXCLUDE_SUFFIXES: frozenset[str] = frozenset({".pyc"})


def detect_type_from_path(pkg_path: Path) -> PackageType:
    """Auto-detect package type from directory path."""
    resolved = pkg_path.resolve()
    for pkg_type in TYPES.values():
        if pkg_type.repo_dir == resolved.parent or resolved.is_relative_to(pkg_type.repo_dir):
            return pkg_type
    msg = f"Cannot detect package type from path: {pkg_path}"
    raise ValueError(msg)


def should_exclude(path: Path, root: Path) -> bool:
    """Check if a path should be excluded from copying/packaging."""
    relative = path.relative_to(root)
    for part in relative.parts:
        if part in EXCLUDE_NAMES:
            return True
    return path.suffix in EXCLUDE_SUFFIXES
