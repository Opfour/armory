"""Tests for the eval history append-only log in scripts.run_evals."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_evals import (
    CaseResult,
    PackageResult,
    _prompt_hash,
    write_history,
)


def _make_package_result(
    package_path: str = "skills/example",
    cases: list[CaseResult] | None = None,
) -> PackageResult:
    case_results = cases or [
        CaseResult(
            case_id="positive_basic",
            prompt="Review this code for quality issues",
            trigger_expected=True,
            oracle_verdict="pass",
            weighted_score=1.0,
            assertion_details=[],
            execution_time_ms=1234,
        ),
    ]
    return PackageResult(
        package_name=Path(package_path).name,
        package_path=package_path,
        total_cases=len(case_results),
        passed=sum(1 for c in case_results if c.oracle_verdict == "pass"),
        failed=sum(1 for c in case_results if c.oracle_verdict == "fail"),
        skipped=sum(1 for c in case_results if c.oracle_verdict == "skipped"),
        aggregate_score=sum(c.weighted_score for c in case_results) / len(case_results),
        case_results=case_results,
    )


class TestPromptHash:
    def test_stable_across_calls(self) -> None:
        assert _prompt_hash("abc") == _prompt_hash("abc")

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert _prompt_hash("abc") != _prompt_hash("abd")

    def test_hash_length_is_sixteen(self) -> None:
        assert len(_prompt_hash("any prompt")) == 16

    def test_hash_is_hex(self) -> None:
        h = _prompt_hash("any prompt")
        int(h, 16)  # raises ValueError if not hex


class TestWriteHistory:
    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        history_path = tmp_path / "nested" / "history.jsonl"
        write_history([_make_package_result()], history_path)
        assert history_path.exists()

    def test_appends_does_not_overwrite(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.jsonl"
        write_history([_make_package_result()], history_path)
        write_history([_make_package_result()], history_path)
        lines = history_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_each_case_is_one_line(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.jsonl"
        cases = [
            CaseResult(
                case_id="c1",
                prompt="Write tests for the parser",
                trigger_expected=True,
                oracle_verdict="pass",
                weighted_score=1.0,
                assertion_details=[],
                execution_time_ms=100,
            ),
            CaseResult(
                case_id="c2",
                prompt="Review this code",
                trigger_expected=True,
                oracle_verdict="fail",
                weighted_score=0.5,
                assertion_details=[],
                execution_time_ms=200,
            ),
        ]
        write_history([_make_package_result(cases=cases)], history_path)
        lines = history_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_schema_fields_present(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.jsonl"
        write_history([_make_package_result()], history_path)
        entry = json.loads(history_path.read_text(encoding="utf-8").strip())
        required = {
            "timestamp",
            "package_path",
            "case_id",
            "task_signature",
            "prompt_hash",
            "trigger_expected",
            "oracle_verdict",
            "weighted_score",
            "execution_time_ms",
        }
        assert required <= set(entry.keys())

    def test_raw_prompt_not_stored(self, tmp_path: Path) -> None:
        """PII protection: history log must not contain the raw prompt text."""
        secret_prompt = "API_KEY=sk-proj-supersecretvalue please review this"
        cases = [
            CaseResult(
                case_id="secret_case",
                prompt=secret_prompt,
                trigger_expected=True,
                oracle_verdict="pass",
                weighted_score=1.0,
                assertion_details=[],
                execution_time_ms=100,
            ),
        ]
        write_history([_make_package_result(cases=cases)], history_path := tmp_path / "h.jsonl")
        contents = history_path.read_text(encoding="utf-8")
        assert "sk-proj-supersecretvalue" not in contents
        assert "API_KEY=" not in contents

    def test_task_signature_populated(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.jsonl"
        write_history([_make_package_result()], history_path)
        entry = json.loads(history_path.read_text(encoding="utf-8").strip())
        # Signature for "Review this code for quality issues" -> sorted stems
        assert "review" in entry["task_signature"].split()
        assert "code" in entry["task_signature"].split()

    def test_jsonl_is_valid_json_per_line(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.jsonl"
        write_history([_make_package_result()], history_path)
        write_history([_make_package_result()], history_path)
        for line in history_path.read_text(encoding="utf-8").strip().split("\n"):
            json.loads(line)  # raises if any line is not valid JSON

    def test_empty_results_produces_empty_file(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.jsonl"
        write_history([], history_path)
        assert history_path.exists()
        assert history_path.read_text(encoding="utf-8") == ""
