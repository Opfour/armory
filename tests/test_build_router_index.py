"""Tests for scripts.build_router_index."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.build_router_index import (
    aggregate,
    build_index,
    read_history,
)


class TestReadHistory:
    def test_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        assert read_history(tmp_path / "nonexistent.jsonl") == []

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        assert read_history(path) == []

    def test_parses_valid_jsonl(self, tmp_path: Path) -> None:
        path = tmp_path / "h.jsonl"
        path.write_text(
            '{"task_signature": "a", "package_path": "skills/x"}\n'
            '{"task_signature": "b", "package_path": "skills/y"}\n',
            encoding="utf-8",
        )
        result = read_history(path)
        assert len(result) == 2
        assert result[0]["package_path"] == "skills/x"

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "h.jsonl"
        path.write_text(
            '{"a": 1}\n\n{"b": 2}\n\n',
            encoding="utf-8",
        )
        assert len(read_history(path)) == 2

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "h.jsonl"
        path.write_text('{"ok": 1}\nnot-json\n', encoding="utf-8")
        try:
            read_history(path)
        except json.JSONDecodeError as exc:
            assert "h.jsonl:2" in str(exc)
        else:
            raise AssertionError("expected JSONDecodeError")


class TestAggregate:
    def test_empty_entries_produce_empty_map(self) -> None:
        assert aggregate([]) == {}

    def test_pass_rate_computed_per_signature_and_package(self) -> None:
        entries = [
            {
                "task_signature": "code review",
                "package_path": "skills/code-reviewer",
                "oracle_verdict": "pass",
            },
            {
                "task_signature": "code review",
                "package_path": "skills/code-reviewer",
                "oracle_verdict": "pass",
            },
            {
                "task_signature": "code review",
                "package_path": "skills/code-reviewer",
                "oracle_verdict": "fail",
            },
        ]
        result = aggregate(entries)
        packages = result["code review"]
        assert len(packages) == 1
        assert abs(packages[0]["pass_rate"] - 2 / 3) < 1e-9
        assert packages[0]["sample_count"] == 3

    def test_multiple_packages_sorted_by_pass_rate_desc(self) -> None:
        entries = [
            {"task_signature": "s", "package_path": "skills/a", "oracle_verdict": "pass"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "fail"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "pass"},
        ]
        result = aggregate(entries)
        packages = result["s"]
        assert packages[0]["package_path"] == "skills/a"  # 1.0 > 0.5
        assert packages[1]["package_path"] == "skills/b"

    def test_tiebreak_by_sample_count(self) -> None:
        entries = [
            {"task_signature": "s", "package_path": "skills/a", "oracle_verdict": "pass"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "pass"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "pass"},
        ]
        result = aggregate(entries)
        # Both are 100% pass; skills/b has more samples -> ranks first
        assert result["s"][0]["package_path"] == "skills/b"

    def test_min_samples_filters_noise(self) -> None:
        entries = [
            {"task_signature": "s", "package_path": "skills/a", "oracle_verdict": "pass"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "pass"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "pass"},
            {"task_signature": "s", "package_path": "skills/b", "oracle_verdict": "pass"},
        ]
        result = aggregate(entries, min_samples=3)
        assert [p["package_path"] for p in result["s"]] == ["skills/b"]

    def test_missing_fields_skipped(self) -> None:
        entries = [
            {"task_signature": "s", "oracle_verdict": "pass"},  # no package
            {"package_path": "skills/x", "oracle_verdict": "pass"},  # no signature
            {
                "task_signature": "s",
                "package_path": "skills/x",
                "oracle_verdict": "pass",
            },
        ]
        result = aggregate(entries)
        assert result == {
            "s": [
                {
                    "package_path": "skills/x",
                    "pass_rate": 1.0,
                    "sample_count": 1,
                }
            ]
        }

    def test_non_pass_verdict_not_counted_as_pass(self) -> None:
        entries = [
            {"task_signature": "s", "package_path": "skills/x", "oracle_verdict": "skipped"},
            {"task_signature": "s", "package_path": "skills/x", "oracle_verdict": "fail"},
        ]
        result = aggregate(entries)
        assert result["s"][0]["pass_rate"] == 0.0


class TestBuildIndex:
    def test_metadata_includes_counts(self) -> None:
        entries = [
            {"task_signature": "a", "package_path": "skills/x", "oracle_verdict": "pass"},
            {"task_signature": "b", "package_path": "skills/y", "oracle_verdict": "pass"},
            {"task_signature": "b", "package_path": "skills/y", "oracle_verdict": "fail"},
        ]
        payload = build_index(entries)
        assert payload["metadata"]["source_entries"] == 3
        assert payload["metadata"]["unique_signatures"] == 2
        assert payload["metadata"]["unique_packages"] == 2

    def test_index_and_metadata_keys_present(self) -> None:
        payload = build_index([])
        assert "metadata" in payload
        assert "index" in payload
        assert payload["metadata"]["source_entries"] == 0
        assert payload["index"] == {}

    def test_min_samples_reflected_in_metadata(self) -> None:
        payload = build_index([], min_samples=5)
        assert payload["metadata"]["min_samples"] == 5
