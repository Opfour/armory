#!/usr/bin/env python3
"""Hook package installer — merges hook config into Claude Code settings.json."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.frontmatter import parse_frontmatter


def install_hook(hook_dir: Path, claude_dir: Path) -> None:
    """Install a hook package.

    1. Copy handler files to claude_dir/hooks/{name}/
    2. Read HOOK.md frontmatter for event/matcher/handler config
    3. Merge hook entry into settings.json
    """
    hook_md = hook_dir / "HOOK.md"
    content = hook_md.read_text(encoding="utf-8")
    meta = parse_frontmatter(content)

    name = meta["name"]
    hook_config = meta["hook"]

    # Copy handler files
    target_dir = claude_dir / "hooks" / name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for src_file in sorted(hook_dir.iterdir()):
        if src_file.is_file() and src_file.name not in ("HOOK.md",):
            shutil.copy2(src_file, target_dir / src_file.name)

    # Merge into settings.json
    settings_path = claude_dir / "settings.json"
    settings: dict[str, Any] = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))

    settings = merge_hook_config(settings, name, hook_config)
    settings_path.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )


def uninstall_hook(name: str, claude_dir: Path) -> None:
    """Remove hook from settings.json and delete handler files."""
    # Remove handler files
    target_dir = claude_dir / "hooks" / name
    if target_dir.exists():
        shutil.rmtree(target_dir)

    # Remove from settings.json
    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings = remove_hook_config(settings, name)
    settings_path.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )


def merge_hook_config(
    settings: dict[str, Any], hook_name: str, hook_meta: dict[str, Any]
) -> dict[str, Any]:
    """Add hook configuration to settings dict. Returns modified settings.

    Structure in settings.json:
    {
      "hooks": {
        "PreToolUse": [
          {"matcher": "Bash", "hooks": [{"type": "command", "command": "..."}]}
        ]
      }
    }

    Each hook package gets its own matcher entry tagged with _hook_name for
    tracking which package owns it.
    """
    hooks_section = settings.setdefault("hooks", {})
    events = hook_meta.get("events", [])
    matcher = hook_meta.get("matcher", "")
    handler = hook_meta.get("handler", {})

    hook_entry = dict(handler)
    hook_entry["_hook_name"] = hook_name

    for event in events:
        event_list: list[dict[str, Any]] = hooks_section.setdefault(event, [])

        # Find existing matcher group or create one
        matcher_group = None
        for group in event_list:
            if group.get("matcher") == matcher:
                matcher_group = group
                break

        if matcher_group is None:
            matcher_group = {"matcher": matcher, "hooks": []}
            event_list.append(matcher_group)

        # Remove any existing entry from this hook package, then append
        matcher_group["hooks"] = [
            h for h in matcher_group["hooks"] if h.get("_hook_name") != hook_name
        ]
        matcher_group["hooks"].append(hook_entry)

    return settings


def remove_hook_config(settings: dict[str, Any], hook_name: str) -> dict[str, Any]:
    """Remove a hook's entries from settings dict."""
    hooks_section = settings.get("hooks")
    if not isinstance(hooks_section, dict):
        return settings

    events_to_delete: list[str] = []

    for event, event_list in hooks_section.items():
        if not isinstance(event_list, list):
            continue

        groups_to_delete: list[int] = []
        for i, group in enumerate(event_list):
            if not isinstance(group, dict):
                continue
            hooks_list = group.get("hooks", [])
            group["hooks"] = [
                h for h in hooks_list if h.get("_hook_name") != hook_name
            ]
            if not group["hooks"]:
                groups_to_delete.append(i)

        for idx in reversed(groups_to_delete):
            event_list.pop(idx)

        if not event_list:
            events_to_delete.append(event)

    for event in events_to_delete:
        del hooks_section[event]

    if not hooks_section:
        del settings["hooks"]

    return settings
