"""Tests for hooks_installer merge/unmerge logic."""
from __future__ import annotations

import copy

import pytest

from scripts.hooks_installer import merge_hook_config, remove_hook_config


@pytest.fixture
def empty_settings() -> dict:
    return {}


@pytest.fixture
def git_protection_meta() -> dict:
    return {
        "events": ["PreToolUse"],
        "matcher": "Bash",
        "handler": {"type": "command", "command": "bash handler.sh", "timeout_ms": 5000},
    }


@pytest.fixture
def pre_edit_backup_meta() -> dict:
    return {
        "events": ["PreToolUse"],
        "matcher": "Edit",
        "handler": {"type": "command", "command": "bash handler.sh", "timeout_ms": 5000},
    }


@pytest.fixture
def cost_tracker_meta() -> dict:
    return {
        "events": ["Stop"],
        "matcher": "",
        "handler": {"type": "command", "command": "bash handler.sh", "timeout_ms": 5000},
    }


@pytest.fixture
def multi_event_meta() -> dict:
    return {
        "events": ["PreToolUse", "PostToolUse"],
        "matcher": "Bash",
        "handler": {"type": "command", "command": "bash multi.sh"},
    }


class TestMergeHookConfig:
    def test_merge_into_empty(
        self, empty_settings: dict, git_protection_meta: dict
    ) -> None:
        result = merge_hook_config(empty_settings, "git-protection", git_protection_meta)

        assert "hooks" in result
        assert "PreToolUse" in result["hooks"]
        groups = result["hooks"]["PreToolUse"]
        assert len(groups) == 1
        assert groups[0]["matcher"] == "Bash"
        assert len(groups[0]["hooks"]) == 1
        assert groups[0]["hooks"][0]["_hook_name"] == "git-protection"
        assert groups[0]["hooks"][0]["command"] == "bash handler.sh"

    def test_merge_appends_different_matcher(
        self, empty_settings: dict, git_protection_meta: dict, pre_edit_backup_meta: dict
    ) -> None:
        result = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        result = merge_hook_config(result, "pre-edit-backup", pre_edit_backup_meta)

        groups = result["hooks"]["PreToolUse"]
        assert len(groups) == 2
        matchers = {g["matcher"] for g in groups}
        assert matchers == {"Bash", "Edit"}

    def test_merge_appends_same_matcher(
        self, empty_settings: dict, git_protection_meta: dict
    ) -> None:
        """Two hooks with the same matcher share the matcher group."""
        second_meta = {
            "events": ["PreToolUse"],
            "matcher": "Bash",
            "handler": {"type": "command", "command": "bash second.sh"},
        }
        result = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        result = merge_hook_config(result, "second-hook", second_meta)

        groups = result["hooks"]["PreToolUse"]
        assert len(groups) == 1
        assert len(groups[0]["hooks"]) == 2

    def test_merge_different_events(
        self, empty_settings: dict, git_protection_meta: dict, cost_tracker_meta: dict
    ) -> None:
        result = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        result = merge_hook_config(result, "cost-tracker", cost_tracker_meta)

        assert "PreToolUse" in result["hooks"]
        assert "Stop" in result["hooks"]

    def test_merge_multi_event_hook(
        self, empty_settings: dict, multi_event_meta: dict
    ) -> None:
        result = merge_hook_config(empty_settings, "multi-hook", multi_event_meta)

        assert "PreToolUse" in result["hooks"]
        assert "PostToolUse" in result["hooks"]
        for event in ("PreToolUse", "PostToolUse"):
            assert len(result["hooks"][event]) == 1
            assert result["hooks"][event][0]["hooks"][0]["_hook_name"] == "multi-hook"

    def test_merge_idempotent(
        self, empty_settings: dict, git_protection_meta: dict
    ) -> None:
        """Merging the same hook twice does not duplicate entries."""
        result = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        result = merge_hook_config(result, "git-protection", git_protection_meta)

        groups = result["hooks"]["PreToolUse"]
        assert len(groups) == 1
        assert len(groups[0]["hooks"]) == 1

    def test_merge_preserves_existing_settings(
        self, git_protection_meta: dict
    ) -> None:
        settings = {"model": "opus", "permissions": {"allow": ["Read"]}}
        result = merge_hook_config(settings, "git-protection", git_protection_meta)

        assert result["model"] == "opus"
        assert result["permissions"]["allow"] == ["Read"]
        assert "hooks" in result


class TestRemoveHookConfig:
    def test_remove_single_hook(
        self, empty_settings: dict, git_protection_meta: dict
    ) -> None:
        merged = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        result = remove_hook_config(merged, "git-protection")

        assert "hooks" not in result

    def test_remove_leaves_other_hooks(
        self, empty_settings: dict, git_protection_meta: dict, pre_edit_backup_meta: dict
    ) -> None:
        merged = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        merged = merge_hook_config(merged, "pre-edit-backup", pre_edit_backup_meta)
        result = remove_hook_config(merged, "git-protection")

        assert "hooks" in result
        groups = result["hooks"]["PreToolUse"]
        assert len(groups) == 1
        assert groups[0]["matcher"] == "Edit"

    def test_remove_nonexistent_no_error(self, empty_settings: dict) -> None:
        result = remove_hook_config(empty_settings, "nonexistent")
        assert result == {}

    def test_remove_from_settings_without_hooks(self) -> None:
        settings = {"model": "opus"}
        result = remove_hook_config(settings, "git-protection")
        assert result == {"model": "opus"}

    def test_remove_shared_matcher_keeps_other(
        self, empty_settings: dict, git_protection_meta: dict
    ) -> None:
        """Removing one hook from a shared matcher group keeps the other."""
        second_meta = {
            "events": ["PreToolUse"],
            "matcher": "Bash",
            "handler": {"type": "command", "command": "bash second.sh"},
        }
        merged = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        merged = merge_hook_config(merged, "second-hook", second_meta)
        result = remove_hook_config(merged, "git-protection")

        groups = result["hooks"]["PreToolUse"]
        assert len(groups) == 1
        assert len(groups[0]["hooks"]) == 1
        assert groups[0]["hooks"][0]["_hook_name"] == "second-hook"


class TestRoundTrip:
    def test_install_uninstall_restores_empty(
        self, empty_settings: dict, git_protection_meta: dict
    ) -> None:
        original = copy.deepcopy(empty_settings)
        merged = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        result = remove_hook_config(merged, "git-protection")
        assert result == original

    def test_install_uninstall_restores_with_other_settings(
        self, git_protection_meta: dict
    ) -> None:
        original = {"model": "opus", "permissions": {"allow": ["Read"]}}
        settings = copy.deepcopy(original)
        merged = merge_hook_config(settings, "git-protection", git_protection_meta)
        result = remove_hook_config(merged, "git-protection")
        assert result == original

    def test_install_multiple_uninstall_all(
        self,
        empty_settings: dict,
        git_protection_meta: dict,
        pre_edit_backup_meta: dict,
        cost_tracker_meta: dict,
    ) -> None:
        original = copy.deepcopy(empty_settings)
        merged = merge_hook_config(empty_settings, "git-protection", git_protection_meta)
        merged = merge_hook_config(merged, "pre-edit-backup", pre_edit_backup_meta)
        merged = merge_hook_config(merged, "cost-tracker", cost_tracker_meta)

        result = remove_hook_config(merged, "git-protection")
        result = remove_hook_config(result, "pre-edit-backup")
        result = remove_hook_config(result, "cost-tracker")
        assert result == original
