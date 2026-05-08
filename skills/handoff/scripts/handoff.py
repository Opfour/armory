#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_LINES = 200
WARNING = "<!-- WARNING: handoff exceeded 200 lines; oldest session changes were truncated. -->"


@dataclass(frozen=True)
class GitState:
    branch: str
    head: str
    modified: int
    untracked: int
    staged: int
    paths: list[str]


def run_git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def git_state(root: Path, allow_missing: bool) -> GitState:
    try:
        branch = run_git(root, ["branch", "--show-current"]) or "detached"
        head = run_git(root, ["rev-parse", "--short", "HEAD"])
        status = run_git(root, ["status", "--porcelain"]).splitlines()
    except RuntimeError:
        if allow_missing:
            return GitState("—", "—", 0, 0, 0, [])
        raise

    modified = 0
    untracked = 0
    staged = 0
    paths: list[str] = []
    for line in status:
        if not line:
            continue
        index = line[0]
        worktree = line[1]
        path = line[3:] if len(line) > 3 else line[2:].strip()
        if line.startswith("??"):
            untracked += 1
        if index not in (" ", "?"):
            staged += 1
        if worktree not in (" ", "?") or index == "M":
            modified += 1
        paths.append(path)
    return GitState(branch, head, modified, untracked, staged, paths[:5])


def read_marker(root: Path, name: str) -> str | None:
    path = root / ".docs" / name
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def project_name(root: Path) -> str:
    return root.resolve().name


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def session_id() -> str:
    return (
        os.environ.get("HANDOFF_SESSION_ID")
        or os.environ.get("AI_SESSION_MODEL")
        or "agent session"
    )


def default_validation(root: Path) -> tuple[str, str, str]:
    marker = read_marker(root, "handoff.last-validation")
    if marker:
        first = marker.splitlines()[0]
        return first, marker, f"{first} @ {timestamp()}"
    return (
        "not recorded this session",
        "not recorded this session",
        f"not recorded this session @ {timestamp()}",
    )


def parse_session_marker(root: Path) -> dict[str, list[str]]:
    marker = read_marker(root, "handoff.session")
    sections: dict[str, list[str]] = {
        "changed": [],
        "decisions": [],
        "blockers": [],
        "refs": [],
    }
    if not marker:
        return sections
    current: str | None = None
    for raw in marker.splitlines():
        line = raw.strip()
        key = line.lower().rstrip(":")
        if key in sections:
            current = key
            continue
        if current and line:
            sections[current].append(line)
    return sections


def parse_existing_handoff(root: Path) -> dict[str, list[str]]:
    path = root / ".docs" / "handoff.md"
    if not path.exists():
        return {
            "changed": [],
            "decisions": [],
            "blockers": [],
            "refs": [],
            "validation": [],
        }

    sections: dict[str, list[str]] = {
        "changed": [],
        "decisions": [],
        "blockers": [],
        "refs": [],
        "validation": [],
    }
    active: str | None = None
    heading_map = {
        "what changed this session": "changed",
        "what was built": "changed",
        "current state": "changed",
        "immediate next actions": "blockers",
        "recommended resume path": "blockers",
        "open questions": "blockers",
        "open questions for next session": "blockers",
        "blockers / open questions": "blockers",
        "test status": "validation",
        "lint and type verification commands": "validation",
        "reference": "refs",
        "refs": "refs",
    }

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            key = line.lstrip("# ").strip().lower()
            active = heading_map.get(key)
            continue
        if not active or not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith(
            (
                "- ",
                "1. ",
                "2. ",
                "3. ",
                "4. ",
                "|",
                "`",
                "uv run",
                "npm ",
                "pnpm ",
                "yarn ",
                "bun ",
                "go ",
                "cargo ",
            )
        ):
            sections[active].append(stripped)
    validation = sections["validation"]
    command_lines = [
        item
        for item in validation
        if item.strip("`").startswith(
            ("uv run", "npm ", "pnpm ", "yarn ", "bun ", "go ", "cargo ")
        )
    ]
    sections["validation"] = command_lines[:6] or validation[:12]
    return {key: values[:12] for key, values in sections.items()}


def render(root: Path, init: bool) -> list[str]:
    state = git_state(root, allow_missing=init)
    tests, lint, verified = default_validation(root)
    session = parse_session_marker(root)
    existing = (
        parse_existing_handoff(root) if not init else parse_existing_handoff(root)
    )
    if tests == "not recorded this session" and existing["validation"]:
        validation_summary = next(
            (
                item.strip("`")
                for item in existing["validation"]
                if item.startswith("`uv run")
            ),
            next(
                (
                    item
                    for item in existing["validation"]
                    if item.startswith(
                        ("uv run", "npm ", "pnpm ", "yarn ", "bun ", "go ", "cargo ")
                    )
                ),
                existing["validation"][0],
            ),
        )
        tests = validation_summary
        lint = validation_summary
        verified = f"{validation_summary} @ {timestamp()}"
    paths = ", ".join(state.paths) if state.paths else "—"
    today = datetime.now().date().isoformat()

    changed = (
        session["changed"]
        or existing["changed"]
        or [
            "No session changes recorded yet."
            if init
            else f"Working tree snapshot captured for {paths}."
        ]
    )
    decisions = (
        session["decisions"]
        or existing["decisions"]
        or [
            f"**Handoff scaffold established** ({today}) — Use `.docs/handoff.md` as the transient session-state runbook; promote durable facts to the proper authority surface."
        ]
    )
    blockers = (
        session["blockers"]
        or existing["blockers"]
        or [
            "No blockers recorded."
            if init
            else "Review current working tree and session context before continuing."
        ]
    )
    refs = session["refs"] or existing["refs"]

    lines = [
        f"# Handoff — {project_name(root)}",
        "",
        f"**Last touched:** {timestamp()} · **branch:** `{state.branch}` · **HEAD:** `{state.head}` · **session:** {session_id()}",
        "",
        "> Authority: this file owns *transient session state*. Persistent facts live in `~/.claude/projects/<project>/memory/`. Static setup lives in `CLAUDE.md`. Strategic",
        "roadmap lives in `~/.claude/plans/<plan>.md`. Committed history lives in `git log`.",
        "",
        "## Status",
        f"- Working tree: {state.modified} modified, {state.untracked} untracked, {state.staged} staged (`{paths}`)",
        f"- Tests: {tests} → {tests}",
        f"- Lint/type: {lint}",
        f"- Last verified: {verified}",
        "",
        "## What changed this session",
        *[f"- {item.lstrip('- ')}" for item in changed],
        "",
        "## Decisions",
        *[
            f"{idx}. {item.lstrip('0123456789. ')}"
            for idx, item in enumerate(decisions, 1)
        ],
        "",
        "## Blockers / open questions",
        *[
            item if item.startswith("- [ ]") else f"- [ ] {item.lstrip('- ')}"
            for item in blockers
        ],
        "",
        "## Resume checklist",
        "1. Run `git status` and confirm the tree matches the Status section.",
        "2. Re-run the last recorded validation command or establish one if not recorded.",
        "3. Open the first changed path listed above and inspect where work stopped.",
        "4. Resolve the top blocker or make the next recorded decision.",
        "",
        "## Refs",
        "- Plan: `—`",
        "- Related PRs: —",
        "- Memory: `—`",
        f"- Conversation: {refs[0] if refs else '—'}",
    ]
    return enforce_limit(lines)


def enforce_limit(lines: list[str]) -> list[str]:
    if len(lines) <= MAX_LINES:
        return lines
    changed_start = lines.index("## What changed this session") + 1
    changed_end = lines.index("", changed_start)
    while len(lines) > MAX_LINES and changed_end - changed_start > 1:
        del lines[changed_start]
        changed_end -= 1
    if WARNING not in lines:
        lines.insert(changed_start, WARNING)
    while len(lines) > MAX_LINES and changed_end - changed_start > 1:
        del lines[changed_start + 1]
        changed_end -= 1
    return lines[:MAX_LINES]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    output = (
        Path(args.output).resolve() if args.output else root / ".docs" / "handoff.md"
    )
    if args.init and output.exists():
        return 0
    lines = render(root, init=args.init)
    text = "\n".join(lines) + "\n"
    if args.dry_run:
        print(text, end="")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
