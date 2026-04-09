"""Tests for skills.immune.scripts.retrieve."""
from __future__ import annotations

import importlib.util
from pathlib import Path

# The immune retrieve module lives under skills/immune/scripts/retrieve.py.
# Load it directly by path since the skills/ tree is not a package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_RETRIEVE_PATH = _REPO_ROOT / "skills" / "immune" / "scripts" / "retrieve.py"
_spec = importlib.util.spec_from_file_location("immune_retrieve", _RETRIEVE_PATH)
assert _spec is not None and _spec.loader is not None
_retrieve_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_retrieve_mod)

retrieve = _retrieve_mod.retrieve
build_success_map = _retrieve_mod.build_success_map


def _antibody(
    entry_id: str,
    domains: list[str] | None = None,
    trigger_sigs: list[str] | None = None,
    trigger_domains: list[str] | None = None,
    severity: str = "warning",
) -> dict:
    entry: dict = {
        "id": entry_id,
        "domains": domains if domains is not None else ["_global"],
        "pattern": f"test pattern for {entry_id}",
        "severity": severity,
        "correction": "fix it",
    }
    if trigger_sigs is not None or trigger_domains is not None:
        entry["triggers"] = {}
        if trigger_sigs is not None:
            entry["triggers"]["task_signatures"] = trigger_sigs
        if trigger_domains is not None:
            entry["triggers"]["domains"] = trigger_domains
    return entry


class TestUntriggeredBackCompat:
    """Entries without a triggers field must retain v3.0.0 behavior."""

    def test_untriggered_entry_returned(self) -> None:
        entries = [_antibody("AB-1")]
        result = retrieve("anything", entries)
        assert len(result) == 1
        assert result[0]["id"] == "AB-1"

    def test_untriggered_entries_returned_in_stable_order(self) -> None:
        entries = [_antibody(f"AB-{i}") for i in range(5)]
        result = retrieve("some task", entries)
        assert len(result) == 5


class TestDomainFiltering:
    def test_domain_mismatch_filters_out(self) -> None:
        entries = [_antibody("AB-code", domains=["code"])]
        result = retrieve("prompt", entries, active_domains={"fitness"})
        assert result == []

    def test_domain_match_passes(self) -> None:
        entries = [_antibody("AB-code", domains=["code"])]
        result = retrieve("prompt", entries, active_domains={"code"})
        assert len(result) == 1

    def test_global_domain_bypasses_filter(self) -> None:
        entries = [_antibody("AB-global", domains=["_global"])]
        result = retrieve("prompt", entries, active_domains={"fitness"})
        assert len(result) == 1

    def test_no_active_domains_skips_filter(self) -> None:
        entries = [_antibody("AB-code", domains=["code"])]
        result = retrieve("prompt", entries, active_domains=None)
        assert len(result) == 1


class TestTriggerMatching:
    def test_matching_trigger_signature_returned(self) -> None:
        # Signature for "Review this code for quality" -> "code quality review"
        entries = [
            _antibody("AB-1", trigger_sigs=["code quality review"]),
        ]
        result = retrieve("Review this code for quality", entries)
        assert len(result) == 1
        assert result[0]["id"] == "AB-1"

    def test_non_matching_trigger_filtered_out(self) -> None:
        entries = [
            _antibody("AB-fitness", trigger_sigs=["exercise squat workout"]),
        ]
        result = retrieve("Review this code for quality", entries)
        assert result == []

    def test_partial_trigger_match_above_threshold_returned(self) -> None:
        # Prompt "Review this code" -> "code review"
        # Trigger "code review quality" -> 2/3 jaccard overlap
        entries = [
            _antibody("AB-1", trigger_sigs=["code review quality"]),
        ]
        result = retrieve("Review this code", entries)
        assert len(result) == 1

    def test_triggered_entry_outranks_untriggered_on_strong_match(self) -> None:
        entries = [
            _antibody("AB-generic"),
            _antibody("AB-specific", trigger_sigs=["code review"]),
        ]
        result = retrieve("review code", entries)
        assert result[0]["id"] == "AB-specific"
        assert result[1]["id"] == "AB-generic"

    def test_multiple_trigger_signatures_uses_best_match(self) -> None:
        entries = [
            _antibody(
                "AB-1",
                trigger_sigs=["unrelated thing", "code review"],
            ),
        ]
        result = retrieve("review code", entries)
        assert len(result) == 1


class TestTopKCap:
    def test_top_k_caps_returned_count(self) -> None:
        entries = [_antibody(f"AB-{i}") for i in range(20)]
        result = retrieve("prompt", entries, top_k=5)
        assert len(result) == 5

    def test_zero_top_k_returns_empty(self) -> None:
        entries = [_antibody("AB-1")]
        result = retrieve("prompt", entries, top_k=0)
        assert result == []


class TestHistoricalSuccessMultiplier:
    def test_zero_success_rate_demotes_entry(self) -> None:
        entries = [
            _antibody("AB-reliable", trigger_sigs=["code review"]),
            _antibody("AB-broken", trigger_sigs=["code review"]),
        ]
        history = {"AB-broken": 0.0, "AB-reliable": 1.0}
        result = retrieve("review code", entries, historical_success=history)
        # Broken entry filtered out entirely (score 0).
        assert [e["id"] for e in result] == ["AB-reliable"]

    def test_missing_entry_defaults_to_full_weight(self) -> None:
        entries = [_antibody("AB-unknown", trigger_sigs=["code review"])]
        result = retrieve("review code", entries, historical_success={})
        assert len(result) == 1


class TestBuildSuccessMap:
    def test_empty_history_returns_empty_map(self) -> None:
        assert build_success_map([]) == {}

    def test_pass_rate_computed_per_signature(self) -> None:
        history = [
            {"task_signature": "code review", "oracle_verdict": "pass"},
            {"task_signature": "code review", "oracle_verdict": "pass"},
            {"task_signature": "code review", "oracle_verdict": "fail"},
            {"task_signature": "write test", "oracle_verdict": "pass"},
        ]
        result = build_success_map(history)
        assert abs(result["code review"] - 2 / 3) < 1e-9
        assert result["write test"] == 1.0

    def test_missing_signature_field_skipped(self) -> None:
        history = [
            {"oracle_verdict": "pass"},
            {"task_signature": "test", "oracle_verdict": "pass"},
        ]
        result = build_success_map(history)
        assert list(result.keys()) == ["test"]

    def test_non_pass_verdict_counted_as_total_not_pass(self) -> None:
        history = [
            {"task_signature": "s", "oracle_verdict": "skipped"},
            {"task_signature": "s", "oracle_verdict": "fail"},
        ]
        assert build_success_map(history) == {"s": 0.0}
