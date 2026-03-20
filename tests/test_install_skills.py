"""Tests for scripts/install.py (package installer)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.install import (
    BODY_ONLY_TYPES,
    InstallAction,
    InstallPlan,
    PackageInfo,
    build_install_plans,
    copy_package,
    discover_packages,
    filter_by_profile,
    get_installed_version,
    install_body_only,
    install_utility,
    is_newer,
    parse_selection,
    parse_version,
    resolve_profile_packages,
)
from scripts.package_types import TYPES, PackageType, should_exclude


def _skill_type() -> PackageType:
    return TYPES["skill"]


def _agent_type() -> PackageType:
    return TYPES["agent"]


def _rule_type() -> PackageType:
    return TYPES["rule"]


def _command_type() -> PackageType:
    return TYPES["command"]


def _utility_type() -> PackageType:
    return TYPES["utility"]


class TestParseVersion:
    """Tests for semver parsing."""

    def test_valid_version(self) -> None:
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_zero_version(self) -> None:
        assert parse_version("0.0.0") == (0, 0, 0)

    def test_large_numbers(self) -> None:
        assert parse_version("10.20.30") == (10, 20, 30)

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError):
            parse_version("1.0")


class TestIsNewer:
    """Tests for version comparison."""

    def test_newer_major(self) -> None:
        assert is_newer("2.0.0", "1.0.0") is True

    def test_newer_minor(self) -> None:
        assert is_newer("1.1.0", "1.0.0") is True

    def test_newer_patch(self) -> None:
        assert is_newer("1.0.1", "1.0.0") is True

    def test_same_version(self) -> None:
        assert is_newer("1.0.0", "1.0.0") is False

    def test_older_version(self) -> None:
        assert is_newer("1.0.0", "2.0.0") is False


class TestExtractVersion:
    """Tests for version extraction from frontmatter (via shared module)."""

    def test_metadata_version(self) -> None:
        from scripts.frontmatter import extract_version
        assert extract_version({"metadata": {"version": "2.0.0"}}) == "2.0.0"

    def test_legacy_top_level(self) -> None:
        from scripts.frontmatter import extract_version
        assert extract_version({"version": "1.0.0"}) == "1.0.0"

    def test_metadata_takes_precedence(self) -> None:
        from scripts.frontmatter import extract_version
        assert extract_version({"version": "1.0.0", "metadata": {"version": "2.0.0"}}) == "2.0.0"

    def test_no_version_returns_empty(self) -> None:
        from scripts.frontmatter import extract_version
        assert extract_version({}) == ""


class TestParseSelection:
    """Tests for user input parsing."""

    def test_single_number(self) -> None:
        assert parse_selection("3", 10) == [2]

    def test_comma_separated(self) -> None:
        assert parse_selection("1,3,5", 10) == [0, 2, 4]

    def test_range(self) -> None:
        assert parse_selection("2-5", 10) == [1, 2, 3, 4]

    def test_mixed(self) -> None:
        assert parse_selection("1,3-5,8", 10) == [0, 2, 3, 4, 7]

    def test_all(self) -> None:
        assert parse_selection("all", 5) == [0, 1, 2, 3, 4]

    def test_quit(self) -> None:
        assert parse_selection("q", 10) == []

    def test_out_of_bounds(self) -> None:
        with pytest.raises(ValueError, match="out of bounds"):
            parse_selection("11", 10)

    def test_invalid_range(self) -> None:
        with pytest.raises(ValueError, match="out of bounds"):
            parse_selection("0-5", 10)

    def test_deduplication(self) -> None:
        assert parse_selection("1,1,1", 10) == [0]


class TestShouldExclude:
    """Tests for file exclusion during copy."""

    def test_pycache_excluded(self, tmp_path: Path) -> None:
        path = tmp_path / "__pycache__" / "mod.pyc"
        assert should_exclude(path, tmp_path) is True

    def test_ds_store_excluded(self, tmp_path: Path) -> None:
        path = tmp_path / ".DS_Store"
        assert should_exclude(path, tmp_path) is True

    def test_normal_file_included(self, tmp_path: Path) -> None:
        path = tmp_path / "SKILL.md"
        assert should_exclude(path, tmp_path) is False

    def test_evals_excluded(self, tmp_path: Path) -> None:
        path = tmp_path / "evals" / "test.json"
        assert should_exclude(path, tmp_path) is True


class TestGetInstalledVersion:
    """Tests for detecting installed package versions."""

    def test_not_installed(self, tmp_path: Path) -> None:
        assert get_installed_version(tmp_path, "missing-skill", _skill_type()) is None

    def test_installed_with_version(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\nmetadata:\n  version: 1.2.3\n---\n"
        )
        assert get_installed_version(tmp_path, "test-skill", _skill_type()) == "1.2.3"

    def test_installed_with_legacy_version(self, tmp_path: Path) -> None:
        """Legacy top-level version still detected."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\nversion: 1.2.3\ndescription: test\n---\n"
        )
        assert get_installed_version(tmp_path, "test-skill", _skill_type()) == "1.2.3"

    def test_installed_without_version(self, tmp_path: Path) -> None:
        """Missing version field treated as 0.0.0."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: test\n---\n"
        )
        assert get_installed_version(tmp_path, "test-skill", _skill_type()) == "0.0.0"

    def test_installed_with_bad_frontmatter(self, tmp_path: Path) -> None:
        """Invalid frontmatter treated as 0.0.0."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# No frontmatter\nJust content.")
        assert get_installed_version(tmp_path, "test-skill", _skill_type()) == "0.0.0"

    def test_rule_body_only_not_installed(self, tmp_path: Path) -> None:
        assert get_installed_version(tmp_path, "my-rule", _rule_type()) is None

    def test_rule_body_only_installed(self, tmp_path: Path) -> None:
        """Rules are installed as single .md files."""
        (tmp_path / "my-rule.md").write_text(
            "---\nname: my-rule\nmetadata:\n  version: 1.0.0\n---\nBody content."
        )
        assert get_installed_version(tmp_path, "my-rule", _rule_type()) == "1.0.0"

    def test_agent_installed(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / "my-agent"
        agent_dir.mkdir()
        (agent_dir / "AGENT.md").write_text(
            "---\nname: my-agent\ndescription: test\nmetadata:\n  version: 2.0.0\n---\n"
        )
        assert get_installed_version(tmp_path, "my-agent", _agent_type()) == "2.0.0"


class TestBuildInstallPlans:
    """Tests for install plan generation."""

    def _make_pkg(
        self, name: str, version: str, tmp_path: Path,
        pkg_type: PackageType | None = None,
    ) -> PackageInfo:
        pt = pkg_type or _skill_type()
        source = tmp_path / "repo" / name
        source.mkdir(parents=True, exist_ok=True)
        return PackageInfo(
            name=name, version=version, description="",
            source_path=source, pkg_type=pt,
        )

    def test_new_install(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / "claude"
        (claude_dir / "skills").mkdir(parents=True)
        pkgs = [self._make_pkg("new-skill", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir)
        assert len(plans) == 1
        assert plans[0].action == InstallAction.INSTALL
        assert plans[0].installed_version is None

    def test_upgrade(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / "claude"
        skill_dir = claude_dir / "skills" / "old-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: old-skill\ndescription: test\nmetadata:\n  version: 0.9.0\n---\n"
        )
        pkgs = [self._make_pkg("old-skill", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir)
        assert plans[0].action == InstallAction.UPGRADE
        assert plans[0].installed_version == "0.9.0"

    def test_skip_same_version(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / "claude"
        skill_dir = claude_dir / "skills" / "current-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: current-skill\ndescription: test\nmetadata:\n  version: 1.0.0\n---\n"
        )
        pkgs = [self._make_pkg("current-skill", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir)
        assert plans[0].action == InstallAction.SKIP

    def test_reinstall_same_version(self, tmp_path: Path) -> None:
        """With reinstall=True, same-version packages get REINSTALL action."""
        claude_dir = tmp_path / "claude"
        skill_dir = claude_dir / "skills" / "current-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: current-skill\ndescription: test\nmetadata:\n  version: 1.0.0\n---\n"
        )
        pkgs = [self._make_pkg("current-skill", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir, reinstall=True)
        assert plans[0].action == InstallAction.REINSTALL
        assert plans[0].installed_version == "1.0.0"

    def test_reinstall_does_not_affect_new_installs(self, tmp_path: Path) -> None:
        """New packages stay as INSTALL even with reinstall=True."""
        claude_dir = tmp_path / "claude"
        (claude_dir / "skills").mkdir(parents=True)
        pkgs = [self._make_pkg("brand-new", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir, reinstall=True)
        assert plans[0].action == InstallAction.INSTALL

    def test_reinstall_does_not_affect_upgrades(self, tmp_path: Path) -> None:
        """Upgradeable packages stay as UPGRADE even with reinstall=True."""
        claude_dir = tmp_path / "claude"
        skill_dir = claude_dir / "skills" / "old-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: old-skill\ndescription: test\nmetadata:\n  version: 0.9.0\n---\n"
        )
        pkgs = [self._make_pkg("old-skill", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir, reinstall=True)
        assert plans[0].action == InstallAction.UPGRADE

    def test_skip_symlink(self, tmp_path: Path) -> None:
        """Symlinked packages are skipped entirely."""
        claude_dir = tmp_path / "claude"
        (claude_dir / "skills").mkdir(parents=True)
        (claude_dir / "skills" / "linked-skill").symlink_to(tmp_path)
        pkgs = [self._make_pkg("linked-skill", "1.0.0", tmp_path)]
        plans = build_install_plans(pkgs, claude_dir)
        assert len(plans) == 0

    def test_multi_type_plans(self, tmp_path: Path) -> None:
        """Plans span multiple package types."""
        claude_dir = tmp_path / "claude"
        (claude_dir / "skills").mkdir(parents=True)
        (claude_dir / "agents").mkdir(parents=True)
        pkgs = [
            self._make_pkg("my-skill", "1.0.0", tmp_path, _skill_type()),
            self._make_pkg("my-agent", "1.0.0", tmp_path, _agent_type()),
        ]
        plans = build_install_plans(pkgs, claude_dir)
        assert len(plans) == 2
        assert plans[0].target_path == claude_dir / "skills" / "my-skill"
        assert plans[1].target_path == claude_dir / "agents" / "my-agent"

    def test_rule_target_is_file(self, tmp_path: Path) -> None:
        """Rule packages target a .md file, not a directory."""
        claude_dir = tmp_path / "claude"
        (claude_dir / "rules").mkdir(parents=True)
        pkgs = [self._make_pkg("my-rule", "1.0.0", tmp_path, _rule_type())]
        plans = build_install_plans(pkgs, claude_dir)
        assert plans[0].target_path == claude_dir / "rules" / "my-rule.md"


class TestCopyPackage:
    """Tests for package copying."""

    def test_copies_files(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: test\ndescription: t\nmetadata:\n  version: 1.0.0\n---\n")
        (source / "refs").mkdir()
        (source / "refs" / "data.txt").write_text("data")

        target = tmp_path / "target"
        count = copy_package(source, target)

        assert count == 2
        assert (target / "SKILL.md").exists()
        assert (target / "refs" / "data.txt").exists()

    def test_excludes_pycache(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: test\ndescription: t\nmetadata:\n  version: 1.0.0\n---\n")
        (source / "__pycache__").mkdir()
        (source / "__pycache__" / "mod.pyc").write_text("bytecode")

        target = tmp_path / "target"
        count = copy_package(source, target)

        assert count == 1
        assert not (target / "__pycache__").exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Upgrade scenario: existing target is removed first."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: test\ndescription: t\nmetadata:\n  version: 2.0.0\n---\n")

        target = tmp_path / "target"
        target.mkdir()
        (target / "old_file.txt").write_text("old")

        copy_package(source, target)

        assert not (target / "old_file.txt").exists()
        assert (target / "SKILL.md").exists()


class TestInstallBodyOnly:
    """Tests for body-only installation (rules, commands)."""

    def test_extracts_body(self, tmp_path: Path) -> None:
        source = tmp_path / "my-rule"
        source.mkdir()
        (source / "RULE.md").write_text(
            "---\nname: my-rule\ndescription: test\nmetadata:\n  version: 1.0.0\n---\nBody content here."
        )
        target = tmp_path / "output" / "my-rule.md"
        count = install_body_only(source, target, _rule_type())
        assert count == 1
        assert target.exists()
        assert target.read_text() == "Body content here."

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        source = tmp_path / "my-cmd"
        source.mkdir()
        (source / "COMMAND.md").write_text(
            "---\nname: my-cmd\n---\nCommand body."
        )
        target = tmp_path / "deep" / "nested" / "my-cmd.md"
        install_body_only(source, target, _command_type())
        assert target.exists()


class TestInstallUtility:
    """Tests for utility installation with chmod."""

    def test_sets_executable(self, tmp_path: Path) -> None:
        source = tmp_path / "my-util"
        source.mkdir()
        (source / "UTILITY.md").write_text(
            "---\nname: my-util\ndescription: test\nutility:\n  entry_point: run.sh\nmetadata:\n  version: 1.0.0\n---\n"
        )
        (source / "run.sh").write_text("#!/bin/bash\necho hi")

        target = tmp_path / "target"
        install_utility(source, target, _utility_type())

        ep = target / "run.sh"
        assert ep.exists()
        assert ep.stat().st_mode & 0o111  # executable bits set


class TestDiscoverPackages:
    """Tests for multi-type discovery."""

    def test_discover_from_manifest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Discovers skills and agents from manifest.yaml."""
        import scripts.install as mod

        # Create source dirs
        (tmp_path / "skills" / "s1").mkdir(parents=True)
        (tmp_path / "agents" / "a1").mkdir(parents=True)

        manifest = {
            "packages": {
                "skills": [
                    {"name": "s1", "version": "1.0.0", "description": "skill", "path": "skills/s1"},
                ],
                "agents": [
                    {"name": "a1", "version": "2.0.0", "description": "agent", "path": "agents/a1"},
                ],
            },
        }
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))

        monkeypatch.setattr(mod, "MANIFEST_PATH", manifest_path)
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        monkeypatch.setattr("scripts.package_types.REPO_ROOT", tmp_path)

        pkgs = discover_packages()
        assert len(pkgs) == 2
        assert pkgs[0].name == "s1"
        assert pkgs[0].pkg_type.key == "skill"
        assert pkgs[1].name == "a1"
        assert pkgs[1].pkg_type.key == "agent"

    def test_discover_single_type(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Filtering to a single type returns only that type."""
        import scripts.install as mod

        (tmp_path / "skills" / "s1").mkdir(parents=True)
        (tmp_path / "agents" / "a1").mkdir(parents=True)

        manifest = {
            "packages": {
                "skills": [
                    {"name": "s1", "version": "1.0.0", "description": "skill", "path": "skills/s1"},
                ],
                "agents": [
                    {"name": "a1", "version": "2.0.0", "description": "agent", "path": "agents/a1"},
                ],
            },
        }
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))

        monkeypatch.setattr(mod, "MANIFEST_PATH", manifest_path)
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        monkeypatch.setattr("scripts.package_types.REPO_ROOT", tmp_path)

        pkgs = discover_packages(_skill_type())
        assert len(pkgs) == 1
        assert pkgs[0].pkg_type.key == "skill"

    def test_discover_from_legacy_manifest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to skills.yaml when manifest.yaml missing."""
        import scripts.install as mod

        (tmp_path / "skills" / "s1").mkdir(parents=True)

        legacy = {
            "skills": [
                {"name": "s1", "version": "1.0.0", "description": "skill", "path": "skills/s1"},
            ],
        }
        legacy_path = tmp_path / "skills.yaml"
        legacy_path.write_text(yaml.dump(legacy))

        monkeypatch.setattr(mod, "MANIFEST_PATH", tmp_path / "nonexistent.yaml")
        monkeypatch.setattr(mod, "LEGACY_MANIFEST_PATH", legacy_path)
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        monkeypatch.setattr("scripts.package_types.REPO_ROOT", tmp_path)

        pkgs = discover_packages()
        assert len(pkgs) == 1
        assert pkgs[0].pkg_type.key == "skill"

    def test_discover_from_definition_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to scanning definition files when no manifest."""
        import scripts.install as mod
        import scripts.package_types as pt_mod

        skill_dir = tmp_path / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: a skill\nmetadata:\n  version: 1.0.0\n---\nBody."
        )

        monkeypatch.setattr(mod, "MANIFEST_PATH", tmp_path / "nonexistent.yaml")
        monkeypatch.setattr(mod, "LEGACY_MANIFEST_PATH", tmp_path / "also-nonexistent.yaml")
        monkeypatch.setattr(pt_mod, "REPO_ROOT", tmp_path)

        pkgs = discover_packages(_skill_type())
        assert len(pkgs) == 1
        assert pkgs[0].name == "my-skill"

    def test_discover_handles_missing_type_dirs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent type directories are skipped gracefully."""
        import scripts.install as mod
        import scripts.package_types as pt_mod

        monkeypatch.setattr(mod, "MANIFEST_PATH", tmp_path / "nonexistent.yaml")
        monkeypatch.setattr(mod, "LEGACY_MANIFEST_PATH", tmp_path / "also-nonexistent.yaml")
        monkeypatch.setattr(pt_mod, "REPO_ROOT", tmp_path)

        pkgs = discover_packages()
        assert pkgs == []


class TestProfileFiltering:
    """Tests for profile-based package filtering."""

    def test_core_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.install as mod

        profiles = {
            "core": {
                "description": "Essential",
                "packages": {"skills": ["pr-review", "code-refiner"]},
            },
        }
        profiles_path = tmp_path / "profiles.yaml"
        profiles_path.write_text(yaml.dump({"profiles": profiles}))
        monkeypatch.setattr(mod, "PROFILES_PATH", profiles_path)

        all_pkgs = [
            PackageInfo("pr-review", "1.0.0", "", tmp_path, _skill_type()),
            PackageInfo("code-refiner", "1.0.0", "", tmp_path, _skill_type()),
            PackageInfo("other-skill", "1.0.0", "", tmp_path, _skill_type()),
        ]
        filtered = filter_by_profile(all_pkgs, "core")
        assert len(filtered) == 2
        assert {p.name for p in filtered} == {"pr-review", "code-refiner"}

    def test_profile_with_includes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.install as mod

        profiles = {
            "core": {
                "packages": {"skills": ["pr-review"]},
            },
            "developer": {
                "includes": ["core"],
                "packages": {"skills": ["test-harness"]},
            },
        }
        profiles_path = tmp_path / "profiles.yaml"
        profiles_path.write_text(yaml.dump({"profiles": profiles}))
        monkeypatch.setattr(mod, "PROFILES_PATH", profiles_path)

        all_pkgs = [
            PackageInfo("pr-review", "1.0.0", "", tmp_path, _skill_type()),
            PackageInfo("test-harness", "1.0.0", "", tmp_path, _skill_type()),
            PackageInfo("other", "1.0.0", "", tmp_path, _skill_type()),
        ]
        filtered = filter_by_profile(all_pkgs, "developer")
        assert len(filtered) == 2
        assert {p.name for p in filtered} == {"pr-review", "test-harness"}

    def test_full_profile_returns_all(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.install as mod

        profiles = {
            "full": {"description": "Everything", "all": True},
        }
        profiles_path = tmp_path / "profiles.yaml"
        profiles_path.write_text(yaml.dump({"profiles": profiles}))
        monkeypatch.setattr(mod, "PROFILES_PATH", profiles_path)

        all_pkgs = [
            PackageInfo("pr-review", "1.0.0", "", tmp_path, _skill_type()),
            PackageInfo("other", "1.0.0", "", tmp_path, _skill_type()),
        ]
        filtered = filter_by_profile(all_pkgs, "full")
        assert len(filtered) == 2

    def test_unknown_profile_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.install as mod

        profiles_path = tmp_path / "profiles.yaml"
        profiles_path.write_text(yaml.dump({"profiles": {}}))
        monkeypatch.setattr(mod, "PROFILES_PATH", profiles_path)

        with pytest.raises(ValueError, match="Unknown profile"):
            filter_by_profile([], "nonexistent")

    def test_profile_multi_type(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Profile can span multiple package types."""
        import scripts.install as mod

        profiles = {
            "mixed": {
                "packages": {
                    "skills": ["my-skill"],
                    "agents": ["my-agent"],
                },
            },
        }
        profiles_path = tmp_path / "profiles.yaml"
        profiles_path.write_text(yaml.dump({"profiles": profiles}))
        monkeypatch.setattr(mod, "PROFILES_PATH", profiles_path)

        all_pkgs = [
            PackageInfo("my-skill", "1.0.0", "", tmp_path, _skill_type()),
            PackageInfo("my-agent", "1.0.0", "", tmp_path, _agent_type()),
            PackageInfo("extra", "1.0.0", "", tmp_path, _skill_type()),
        ]
        filtered = filter_by_profile(all_pkgs, "mixed")
        assert len(filtered) == 2
        assert {p.name for p in filtered} == {"my-skill", "my-agent"}


class TestResolveProfilePackages:
    """Tests for profile resolution internals."""

    def test_circular_includes_safe(self) -> None:
        """Circular includes do not infinite-loop."""
        profiles = {
            "a": {"includes": ["b"], "packages": {"skills": ["s1"]}},
            "b": {"includes": ["a"], "packages": {"skills": ["s2"]}},
        }
        result = resolve_profile_packages("a", profiles)
        assert "skill" in result
        assert "s1" in result["skill"]
        assert "s2" in result["skill"]

    def test_include_all_propagates(self) -> None:
        """Including an 'all: true' profile propagates to parent."""
        profiles = {
            "full": {"all": True},
            "extended": {"includes": ["full"], "packages": {"skills": ["extra"]}},
        }
        result = resolve_profile_packages("extended", profiles)
        # Empty dict signals "all"
        assert result == {}
