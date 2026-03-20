#!/usr/bin/env python3
"""Parse project dependency files and print a formatted dependency tree."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path


def parse_pyproject(path: Path) -> dict[str, dict[str, str]]:
    """Parse pyproject.toml and return dependency groups."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    groups: dict[str, dict[str, str]] = {}

    deps = project.get("dependencies", [])
    if deps:
        groups["Dependencies"] = {}
        for dep in deps:
            match = re.match(r"^([a-zA-Z0-9_.-]+)\s*(.*)", dep)
            if match:
                groups["Dependencies"][match.group(1)] = match.group(2).strip() or "*"

    for group_name, group_deps in project.get("optional-dependencies", {}).items():
        key = f"Optional [{group_name}]"
        groups[key] = {}
        for dep in group_deps:
            match = re.match(r"^([a-zA-Z0-9_.-]+)\s*(.*)", dep)
            if match:
                groups[key][match.group(1)] = match.group(2).strip() or "*"

    return groups


def parse_package_json(path: Path) -> dict[str, dict[str, str]]:
    """Parse package.json and return dependency groups."""
    data = json.loads(path.read_text(encoding="utf-8"))
    groups: dict[str, dict[str, str]] = {}

    if data.get("dependencies"):
        groups["Dependencies"] = dict(data["dependencies"])
    if data.get("devDependencies"):
        groups["Dev Dependencies"] = dict(data["devDependencies"])

    return groups


def parse_go_mod(path: Path) -> dict[str, dict[str, str]]:
    """Parse go.mod and return dependency groups."""
    text = path.read_text(encoding="utf-8")
    deps: dict[str, str] = {}

    in_require = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if in_require:
            parts = stripped.split()
            if len(parts) >= 2 and not parts[0].startswith("//"):
                deps[parts[0]] = parts[1]
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 3:
                deps[parts[1]] = parts[2]

    return {"Dependencies": deps} if deps else {}


DETECTORS: list[tuple[str, str, object]] = [
    ("pyproject.toml", "pyproject.toml", parse_pyproject),
    ("package.json", "package.json", parse_package_json),
    ("go.mod", "go.mod", parse_go_mod),
]


def print_tree(project_file: str, groups: dict[str, dict[str, str]], depth: int) -> None:
    """Print formatted dependency tree."""
    print(f"Project: {project_file}")
    if not groups:
        print("  (no dependencies found)")
        return

    for group_name, deps in groups.items():
        if depth < 1:
            break
        print(f"\n{group_name}:")
        for name, version in sorted(deps.items()):
            print(f"  {name} {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print project dependency tree.")
    parser.add_argument("path", nargs="?", default=".", help="Project directory (default: CWD)")
    parser.add_argument("--depth", type=int, default=10, help="Max tree depth (default: 10)")
    args = parser.parse_args()

    project_dir = Path(args.path).resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        return 1

    for filename, label, parser_fn in DETECTORS:
        config_file = project_dir / filename
        if config_file.exists():
            groups = parser_fn(config_file)
            print_tree(label, groups, args.depth)
            return 0

    print(f"Error: no supported config file found in {project_dir}", file=sys.stderr)
    print("Supported: pyproject.toml, package.json, go.mod", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
