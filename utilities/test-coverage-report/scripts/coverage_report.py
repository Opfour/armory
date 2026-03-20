#!/usr/bin/env python3
"""Summarize test coverage for recently changed files based on git diff."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SOURCE_EXTENSIONS = {".py", ".ts", ".js", ".go"}
SKIP_PATTERNS = {"__init__", "conftest", "setup", "config"}


def get_changed_files(repo: Path, base: str) -> list[Path]:
    """Get list of changed source files from git diff."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    files: list[Path] = []
    for line in result.stdout.strip().splitlines():
        p = Path(line)
        if p.suffix in SOURCE_EXTENSIONS and not any(s in p.stem for s in SKIP_PATTERNS):
            files.append(p)
    return files


def find_test_file(source: Path, repo: Path) -> Path | None:
    """Search for a test file corresponding to the given source file."""
    stem = source.stem
    suffix = source.suffix
    parent = source.parent

    candidates: list[Path] = []

    if suffix == ".py":
        candidates = [
            parent / f"test_{stem}.py",
            Path("tests") / parent / f"test_{stem}.py",
            Path("test") / parent / f"test_{stem}.py",
            Path("tests") / f"test_{stem}.py",
        ]
    elif suffix in {".ts", ".js"}:
        candidates = [
            parent / f"{stem}.test{suffix}",
            parent / f"{stem}.spec{suffix}",
            parent / "__tests__" / f"{stem}.test{suffix}",
        ]
    elif suffix == ".go":
        candidates = [parent / f"{stem}_test.go"]

    for candidate in candidates:
        if (repo / candidate).exists():
            return candidate

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Test coverage report for changed files.")
    parser.add_argument("path", nargs="?", default=".", help="Repository path (default: CWD)")
    parser.add_argument("--base", default="HEAD~1", help="Git base ref (default: HEAD~1)")
    args = parser.parse_args()

    repo = Path(args.path).resolve()
    if not (repo / ".git").exists():
        print(f"Error: {repo} is not a git repository", file=sys.stderr)
        return 1

    changed = get_changed_files(repo, args.base)
    if not changed:
        print("No changed source files found.")
        return 0

    print("Changed files test coverage:\n")
    print(f"{'File':<40} {'Has Tests':<12} {'Test File'}")
    print("-" * 80)

    missing = 0
    for source in sorted(changed):
        test_file = find_test_file(source, repo)
        if test_file:
            print(f"{str(source):<40} {'yes':<12} {test_file}")
        else:
            print(f"{str(source):<40} {'NO':<12} -")
            missing += 1

    covered = len(changed) - missing
    pct = (covered / len(changed)) * 100 if changed else 100
    print(f"\nSummary: {covered}/{len(changed)} files have tests ({pct:.1f}%)")

    if missing:
        print(f"FAIL: {missing} file(s) missing tests")
        return 1

    print("PASS: all changed files have tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
