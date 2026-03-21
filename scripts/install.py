#!/usr/bin/env python3
"""TUI installer for armory — copies packages to ~/.claude/{type}/."""
from __future__ import annotations

import shutil
import stat
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Prompt
from rich.table import Table

from scripts.frontmatter import extract_body, extract_version, parse_frontmatter
from scripts.package_types import (
    MANIFEST_PATH,
    REPO_ROOT,
    TYPES,
    PackageType,
    should_exclude,
)

DEFAULT_CLAUDE_DIR = Path.home() / ".claude"
PROFILES_PATH = REPO_ROOT / "profiles.yaml"

# Types that install as body-only .md files (frontmatter stripped)
BODY_ONLY_TYPES: frozenset[str] = frozenset({"rule", "command"})

# Type display colors for TUI
TYPE_COLORS: dict[str, str] = {
    "skill": "cyan",
    "agent": "magenta",
    "hook": "yellow",
    "rule": "green",
    "command": "blue",
    "utility": "red",
    "preset": "bright_black",
}

console = Console()


class InstallAction(Enum):
    INSTALL = "install"
    UPGRADE = "upgrade"
    REINSTALL = "reinstall"
    SKIP = "skip"


@dataclass(frozen=True)
class PackageInfo:
    name: str
    version: str
    description: str
    source_path: Path
    pkg_type: PackageType


@dataclass(frozen=True)
class InstallPlan:
    package: PackageInfo
    action: InstallAction
    installed_version: str | None
    target_path: Path


def parse_version(v: str) -> tuple[int, int, int]:
    """Parse semver string into comparable tuple."""
    parts = v.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version: {v}")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def is_newer(repo: str, installed: str) -> bool:
    """Return True if repo version is strictly newer than installed."""
    return parse_version(repo) > parse_version(installed)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_packages(pkg_type: PackageType | None = None) -> list[PackageInfo]:
    """Discover available packages from manifest or definition files.

    If pkg_type is None, discover all types.
    """
    types_to_scan = [pkg_type] if pkg_type else list(TYPES.values())

    if MANIFEST_PATH.exists():
        return _discover_from_manifest(types_to_scan)
    return _discover_from_definition_files(types_to_scan)


def _discover_from_manifest(types_to_scan: list[PackageType]) -> list[PackageInfo]:
    """Read packages from manifest.yaml (new format: packages.skills, packages.agents, etc.)."""
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    packages_section = manifest.get("packages", {})
    packages: list[PackageInfo] = []

    for pt in types_to_scan:
        for entry in packages_section.get(pt.manifest_section, []):
            source = REPO_ROOT / entry["path"]
            if not source.is_dir():
                continue
            packages.append(PackageInfo(
                name=entry["name"],
                version=entry.get("version", "0.0.0"),
                description=entry.get("description", ""),
                source_path=source,
                pkg_type=pt,
            ))

    return packages


def _discover_from_definition_files(types_to_scan: list[PackageType]) -> list[PackageInfo]:
    """Fallback: parse definition files directly from type directories."""
    console.print("[dim]No manifest found — parsing definition files directly[/dim]")
    packages: list[PackageInfo] = []

    for pt in types_to_scan:
        repo_dir = pt.repo_dir
        if not repo_dir.is_dir():
            continue

        for pkg_dir in sorted(repo_dir.iterdir()):
            def_file = pkg_dir / pt.definition_file
            if not pkg_dir.is_dir() or not def_file.exists():
                continue

            content = def_file.read_text(encoding="utf-8")
            try:
                meta = parse_frontmatter(content)
            except ValueError:
                continue

            name = meta.get("name", "")
            if not name:
                continue

            version = extract_version(meta) or "0.0.0"
            packages.append(PackageInfo(
                name=name,
                version=version,
                description=meta.get("description", "").strip(),
                source_path=pkg_dir,
                pkg_type=pt,
            ))

    return packages


# ---------------------------------------------------------------------------
# Installed version detection
# ---------------------------------------------------------------------------


def get_installed_version(
    install_dir: Path, pkg_name: str, pkg_type: PackageType,
) -> str | None:
    """Read version from an installed package's definition file, or None if not installed."""
    if pkg_type.key in BODY_ONLY_TYPES:
        # Body-only types are single .md files, not directories
        installed_file = install_dir / f"{pkg_name}.md"
        if not installed_file.exists():
            return None
        content = installed_file.read_text(encoding="utf-8")
        try:
            meta = parse_frontmatter(content)
        except ValueError:
            return "0.0.0"
        return extract_version(meta) or "0.0.0"

    def_file = install_dir / pkg_name / pkg_type.definition_file
    if not def_file.exists():
        return None

    content = def_file.read_text(encoding="utf-8")
    try:
        meta = parse_frontmatter(content)
    except ValueError:
        return "0.0.0"

    return extract_version(meta) or "0.0.0"


# ---------------------------------------------------------------------------
# Install plan building
# ---------------------------------------------------------------------------


def build_install_plans(
    packages: list[PackageInfo],
    claude_dir: Path,
    *,
    reinstall: bool = False,
) -> list[InstallPlan]:
    """Determine install/upgrade/reinstall/skip action for each package."""
    plans: list[InstallPlan] = []

    for pkg in packages:
        install_dir = claude_dir / pkg.pkg_type.install_subdir
        if pkg.pkg_type.key in BODY_ONLY_TYPES:
            target = install_dir / f"{pkg.name}.md"
        else:
            target = install_dir / pkg.name

        installed_version = get_installed_version(install_dir, pkg.name, pkg.pkg_type)

        # Symlinks are externally managed — skip (only for directory-based types)
        if pkg.pkg_type.key not in BODY_ONLY_TYPES and target.is_symlink():
            console.print(
                f"[yellow]Skipping {pkg.name} — {target} is a symlink (externally managed)[/yellow]"
            )
            continue

        if installed_version is None:
            action = InstallAction.INSTALL
        elif is_newer(pkg.version, installed_version):
            action = InstallAction.UPGRADE
        elif reinstall:
            action = InstallAction.REINSTALL
        else:
            action = InstallAction.SKIP

        plans.append(InstallPlan(
            package=pkg,
            action=action,
            installed_version=installed_version,
            target_path=target,
        ))

    return plans


# ---------------------------------------------------------------------------
# TUI display
# ---------------------------------------------------------------------------


def display_plans(plans: list[InstallPlan]) -> None:
    """Display package table with color-coded actions, grouped by type."""
    table = Table(title="Available Packages", show_lines=False)
    table.add_column("#", style="bold", width=4)
    table.add_column("Type", justify="center")
    table.add_column("Name", style="cyan")
    table.add_column("Repo Version", justify="center")
    table.add_column("Installed", justify="center")
    table.add_column("Action", justify="center")

    action_styles = {
        InstallAction.INSTALL: "[green]install[/green]",
        InstallAction.UPGRADE: "[yellow]upgrade[/yellow]",
        InstallAction.REINSTALL: "[blue]reinstall[/blue]",
        InstallAction.SKIP: "[dim]skip[/dim]",
    }

    for i, plan in enumerate(plans, 1):
        installed = plan.installed_version or "—"
        action_text = action_styles[plan.action]
        type_color = TYPE_COLORS.get(plan.package.pkg_type.key, "white")
        type_label = f"[{type_color}]{plan.package.pkg_type.key}[/{type_color}]"

        table.add_row(
            str(i),
            type_label,
            plan.package.name,
            plan.package.version,
            installed,
            action_text,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Selection parsing
# ---------------------------------------------------------------------------


def parse_selection(raw: str, total: int) -> list[int]:
    """Parse user selection string into list of 0-based indices.

    Accepts: '1,3,5-8,all' or 'q' to quit.
    """
    raw = raw.strip().lower()
    if raw in ("q", "quit", "exit"):
        return []
    if raw == "all":
        return list(range(total))

    indices: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            if start < 1 or end > total or start > end:
                raise ValueError(f"Range {part} out of bounds (1-{total})")
            indices.extend(range(start - 1, end))
        else:
            num = int(part)
            if num < 1 or num > total:
                raise ValueError(f"Number {num} out of bounds (1-{total})")
            indices.append(num - 1)

    return sorted(set(indices))


# ---------------------------------------------------------------------------
# Package installation
# ---------------------------------------------------------------------------


def copy_package(source: Path, target: Path) -> int:
    """Copy package directory, excluding unwanted files. Returns file count."""
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    count = 0
    for src_file in sorted(source.rglob("*")):
        if not src_file.is_file():
            continue
        if should_exclude(src_file, source):
            continue

        rel = src_file.relative_to(source)
        dst_file = target / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        count += 1

    return count


def install_body_only(source_path: Path, target_path: Path, pkg_type: PackageType) -> int:
    """Install a body-only package (rules, commands) — extract body, write single .md file."""
    def_file = source_path / pkg_type.definition_file
    content = def_file.read_text(encoding="utf-8")
    body = extract_body(content)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(body, encoding="utf-8")
    return 1


def install_utility(source: Path, target: Path, pkg_type: PackageType) -> int:
    """Install a utility package — copy directory and chmod +x entry_point."""
    count = copy_package(source, target)

    # Read definition file for entry_point
    def_file = source / pkg_type.definition_file
    if def_file.exists():
        content = def_file.read_text(encoding="utf-8")
        try:
            meta = parse_frontmatter(content)
        except ValueError:
            return count
        utility_meta = meta.get("utility", {})
        if isinstance(utility_meta, dict):
            entry_point = utility_meta.get("entry_point")
            if entry_point:
                ep_path = target / entry_point
                if ep_path.exists():
                    current = ep_path.stat().st_mode
                    ep_path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return count


def install_package(plan: InstallPlan) -> int:
    """Install a single package according to its type. Returns file count."""
    pkg = plan.package
    key = pkg.pkg_type.key

    if key in BODY_ONLY_TYPES:
        return install_body_only(pkg.source_path, plan.target_path, pkg.pkg_type)
    if key == "utility":
        return install_utility(pkg.source_path, plan.target_path, pkg.pkg_type)
    # skill, agent, hook, preset — copy full directory
    return copy_package(pkg.source_path, plan.target_path)


_ACTION_LABELS: dict[InstallAction, str] = {
    InstallAction.INSTALL: "Installed",
    InstallAction.UPGRADE: "Upgraded",
    InstallAction.REINSTALL: "Reinstalled",
}


def execute_plans(plans: list[InstallPlan], selected: list[int]) -> None:
    """Execute selected installation plans."""
    to_install = [plans[i] for i in selected if plans[i].action != InstallAction.SKIP]

    if not to_install:
        console.print("[dim]Nothing to install — all selected packages are up to date.[/dim]")
        return

    with Progress(console=console) as progress:
        task = progress.add_task("Installing packages...", total=len(to_install))

        for plan in to_install:
            progress.update(task, description=f"Installing {plan.package.name}...")
            file_count = install_package(plan)
            progress.advance(task)
            label = _ACTION_LABELS.get(plan.action, "Installed")
            console.print(
                f"  {label} [{TYPE_COLORS.get(plan.package.pkg_type.key, 'white')}]"
                f"{plan.package.pkg_type.key}[/] "
                f"[cyan]{plan.package.name}[/cyan] "
                f"v{plan.package.version} ({file_count} files)"
            )

    # Summary
    console.print()
    summary = Table(title="Installation Summary", show_lines=False)
    summary.add_column("Type")
    summary.add_column("Package", style="cyan")
    summary.add_column("Action")
    summary.add_column("Version")

    for plan in to_install:
        label = _ACTION_LABELS.get(plan.action, "installed").lower()
        type_color = TYPE_COLORS.get(plan.package.pkg_type.key, "white")
        if plan.action == InstallAction.UPGRADE:
            ver = f"{plan.installed_version} -> {plan.package.version}"
        else:
            ver = plan.package.version
        summary.add_row(
            f"[{type_color}]{plan.package.pkg_type.key}[/{type_color}]",
            plan.package.name,
            label,
            ver,
        )

    console.print(summary)
    console.print(
        Panel(
            "Restart Claude Code to load the new packages.",
            title="Done",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# Profile support
# ---------------------------------------------------------------------------


def load_profiles() -> dict[str, dict]:
    """Load profiles from profiles.yaml."""
    if not PROFILES_PATH.exists():
        return {}
    data = yaml.safe_load(PROFILES_PATH.read_text(encoding="utf-8"))
    return data.get("profiles", {})


def resolve_profile_packages(
    profile_name: str,
    profiles: dict[str, dict],
    visited: set[str] | None = None,
) -> dict[str, set[str]]:
    """Resolve a profile into {type_key: {pkg_names}} with include-chain expansion.

    Returns a dict mapping package type keys to sets of package names.
    If the profile has 'all: true', returns an empty dict (caller treats as all packages).
    """
    if visited is None:
        visited = set()
    if profile_name in visited:
        return {}
    visited.add(profile_name)

    profile = profiles.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown profile: {profile_name}")

    if profile.get("all", False):
        return {}  # sentinel: caller installs everything

    result: dict[str, set[str]] = {}

    # Resolve includes first
    for included in profile.get("includes", []):
        included_pkgs = resolve_profile_packages(included, profiles, visited)
        if not included_pkgs and profiles.get(included, {}).get("all", False):
            return {}  # included profile is "all"
        for type_key, names in included_pkgs.items():
            result.setdefault(type_key, set()).update(names)

    # Add this profile's packages
    for type_key, names in profile.get("packages", {}).items():
        # type_key in profiles.yaml matches manifest_section (e.g., "skills", "agents")
        # Map to PackageType key
        pkg_type_key = _section_to_type_key(type_key)
        if pkg_type_key:
            result.setdefault(pkg_type_key, set()).update(names)

    return result


def _section_to_type_key(section: str) -> str | None:
    """Map manifest section name to PackageType key."""
    for pt in TYPES.values():
        if pt.manifest_section == section:
            return pt.key
    return None


def filter_by_profile(
    packages: list[PackageInfo], profile_name: str,
) -> list[PackageInfo]:
    """Filter packages to those matching a profile."""
    profiles = load_profiles()
    resolved = resolve_profile_packages(profile_name, profiles)

    # Empty dict from an "all: true" profile means install everything
    profile_data = profiles.get(profile_name, {})
    if profile_data.get("all", False) or (
        not resolved
        and any(
            profiles.get(inc, {}).get("all", False)
            for inc in profile_data.get("includes", [])
        )
    ):
        return packages

    return [
        pkg for pkg in packages
        if pkg.pkg_type.key in resolved and pkg.name in resolved[pkg.pkg_type.key]
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Main entry point for the TUI installer."""
    import argparse

    parser = argparse.ArgumentParser(description="Install armory packages to ~/.claude/")
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="Allow reinstalling packages that are already at the same version",
    )
    parser.add_argument(
        "--type",
        dest="pkg_type",
        choices=list(TYPES.keys()),
        help="Filter to a single package type",
    )
    parser.add_argument(
        "--profile",
        help="Install packages matching a profile from profiles.yaml",
    )
    args = parser.parse_args()

    console.print(Panel("armory installer", border_style="blue"))

    # Discover
    type_filter = TYPES.get(args.pkg_type) if args.pkg_type else None
    packages = discover_packages(type_filter)

    if args.profile:
        packages = filter_by_profile(packages, args.profile)

    if not packages:
        console.print("[red]No packages found.[/red]")
        return 1

    # Sort by type then name for grouped display
    packages.sort(key=lambda p: (p.pkg_type.key, p.name))

    claude_dir = DEFAULT_CLAUDE_DIR
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Build plans
    plans = build_install_plans(packages, claude_dir, reinstall=args.reinstall)
    if not plans:
        console.print("[dim]No installable packages found.[/dim]")
        return 0

    # Display
    display_plans(plans)

    # Count actionable
    actionable = [i for i, p in enumerate(plans) if p.action != InstallAction.SKIP]
    if not actionable:
        console.print("[dim]All packages are up to date. Use --reinstall to force reinstallation.[/dim]")
        return 0

    # Select
    while True:
        raw = Prompt.ask(
            f"\nEnter package numbers to install ([green]1,3,5-8[/green], [green]all[/green], or [red]q[/red] to quit)"
        )
        if raw.strip().lower() in ("q", "quit", "exit"):
            console.print("[dim]Cancelled.[/dim]")
            return 0

        try:
            selected = parse_selection(raw, len(plans))
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            continue

        if not selected:
            console.print("[dim]No packages selected.[/dim]")
            continue

        break

    # Filter to actionable selections
    selected_actionable = [i for i in selected if plans[i].action != InstallAction.SKIP]
    if not selected_actionable:
        console.print("[dim]All selected packages are already up to date.[/dim]")
        return 0

    # Confirm
    names = ", ".join(plans[i].package.name for i in selected_actionable)
    console.print(f"\nWill install/upgrade/reinstall: [cyan]{names}[/cyan]")
    confirm = Prompt.ask("Proceed?", choices=["y", "n"], default="y")
    if confirm != "y":
        console.print("[dim]Cancelled.[/dim]")
        return 0

    # Execute
    execute_plans(plans, selected_actionable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
