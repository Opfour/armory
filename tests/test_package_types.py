"""Tests for the package type registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.package_types import (
    EXCLUDE_NAMES,
    EXCLUDE_SUFFIXES,
    MANIFEST_PATH,
    REPO_ROOT,
    TYPES,
    PackageType,
    detect_type_from_path,
    should_exclude,
)


class TestPackageTypeRegistry:
    """Tests for TYPES registry completeness and correctness."""

    def test_all_seven_types_registered(self) -> None:
        assert len(TYPES) == 7
        expected = {"skill", "agent", "hook", "rule", "command", "utility", "preset"}
        assert set(TYPES.keys()) == expected

    def test_keys_match_dict_keys(self) -> None:
        for key, pkg_type in TYPES.items():
            assert pkg_type.key == key

    def test_unique_dir_names(self) -> None:
        dir_names = [t.dir_name for t in TYPES.values()]
        assert len(dir_names) == len(set(dir_names))

    def test_unique_definition_files(self) -> None:
        files = [t.definition_file for t in TYPES.values()]
        assert len(files) == len(set(files))

    def test_unique_archive_extensions(self) -> None:
        exts = [t.archive_ext for t in TYPES.values()]
        assert len(exts) == len(set(exts))

    def test_unique_manifest_sections(self) -> None:
        sections = [t.manifest_section for t in TYPES.values()]
        assert len(sections) == len(set(sections))

    def test_unique_install_subdirs(self) -> None:
        subdirs = [t.install_subdir for t in TYPES.values()]
        assert len(subdirs) == len(set(subdirs))

    def test_archive_ext_starts_with_dot(self) -> None:
        for pkg_type in TYPES.values():
            assert pkg_type.archive_ext.startswith(".")

    def test_definition_file_ends_with_md(self) -> None:
        for pkg_type in TYPES.values():
            assert pkg_type.definition_file.endswith(".md")

    def test_required_frontmatter_includes_name_and_description(self) -> None:
        for pkg_type in TYPES.values():
            assert "name" in pkg_type.required_frontmatter
            assert "description" in pkg_type.required_frontmatter


class TestPackageTypeDataclass:
    """Tests for the PackageType frozen dataclass."""

    def test_frozen_immutability(self) -> None:
        pkg = TYPES["skill"]
        with pytest.raises(AttributeError):
            pkg.key = "modified"  # type: ignore[misc]

    def test_repo_dir_property(self) -> None:
        pkg = TYPES["skill"]
        assert pkg.repo_dir == REPO_ROOT / "skills"

    def test_repo_dir_is_absolute(self) -> None:
        for pkg_type in TYPES.values():
            assert pkg_type.repo_dir.is_absolute()


class TestDetectTypeFromPath:
    """Tests for detect_type_from_path."""

    def test_detect_skill(self) -> None:
        path = REPO_ROOT / "skills" / "my-skill"
        result = detect_type_from_path(path)
        assert result.key == "skill"

    def test_detect_agent(self) -> None:
        path = REPO_ROOT / "agents" / "my-agent"
        result = detect_type_from_path(path)
        assert result.key == "agent"

    def test_detect_nested_path(self) -> None:
        path = REPO_ROOT / "hooks" / "my-hook" / "subdir"
        result = detect_type_from_path(path)
        assert result.key == "hook"

    def test_unknown_path_raises(self) -> None:
        path = Path("/tmp/unknown-dir/pkg")
        with pytest.raises(ValueError, match="Cannot detect package type"):
            detect_type_from_path(path)

    def test_detect_all_types(self) -> None:
        for key, pkg_type in TYPES.items():
            path = REPO_ROOT / pkg_type.dir_name / "test-pkg"
            result = detect_type_from_path(path)
            assert result.key == key


class TestShouldExclude:
    """Tests for should_exclude."""

    def test_exclude_pycache(self) -> None:
        root = Path("/project")
        assert should_exclude(Path("/project/__pycache__/mod.pyc"), root)

    def test_exclude_node_modules(self) -> None:
        root = Path("/project")
        assert should_exclude(Path("/project/node_modules/pkg/index.js"), root)

    def test_exclude_ds_store(self) -> None:
        root = Path("/project")
        assert should_exclude(Path("/project/.DS_Store"), root)

    def test_exclude_git(self) -> None:
        root = Path("/project")
        assert should_exclude(Path("/project/.git/config"), root)

    def test_exclude_evals(self) -> None:
        root = Path("/project")
        assert should_exclude(Path("/project/evals/test.yaml"), root)

    def test_exclude_pyc_suffix(self) -> None:
        root = Path("/project")
        assert should_exclude(Path("/project/module.pyc"), root)

    def test_include_normal_file(self) -> None:
        root = Path("/project")
        assert not should_exclude(Path("/project/main.py"), root)

    def test_include_nested_normal_file(self) -> None:
        root = Path("/project")
        assert not should_exclude(Path("/project/src/lib/utils.py"), root)

    def test_include_references_dir(self) -> None:
        root = Path("/project")
        assert not should_exclude(Path("/project/references/doc.md"), root)

    def test_include_scripts_dir(self) -> None:
        root = Path("/project")
        assert not should_exclude(Path("/project/scripts/build.py"), root)


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_manifest_path_is_yaml(self) -> None:
        assert MANIFEST_PATH.name == "manifest.yaml"

    def test_exclude_names_is_frozenset(self) -> None:
        assert isinstance(EXCLUDE_NAMES, frozenset)

    def test_exclude_suffixes_is_frozenset(self) -> None:
        assert isinstance(EXCLUDE_SUFFIXES, frozenset)

    def test_repo_root_is_absolute(self) -> None:
        assert REPO_ROOT.is_absolute()
