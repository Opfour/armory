"""Tests for scripts.task_signature."""
from __future__ import annotations

from scripts.task_signature import jaccard_similarity, task_signature


class TestTaskSignatureBasics:
    def test_empty_prompt_returns_empty_string(self) -> None:
        assert task_signature("") == ""

    def test_all_stopwords_returns_empty_string(self) -> None:
        assert task_signature("the a an and or you i") == ""

    def test_single_content_word_stems(self) -> None:
        assert task_signature("testing") == "test"

    def test_punctuation_stripped(self) -> None:
        assert task_signature("review code!") == task_signature("review, code.")

    def test_case_insensitive(self) -> None:
        assert task_signature("Review Code") == task_signature("review code")

    def test_word_order_irrelevant(self) -> None:
        assert task_signature("review code") == task_signature("code review")

    def test_stopwords_dropped(self) -> None:
        assert task_signature("please review the code") == task_signature("review code")

    def test_duplicate_tokens_deduped(self) -> None:
        assert task_signature("code code review") == task_signature("code review")

    def test_plural_and_singular_collide(self) -> None:
        assert task_signature("tests") == task_signature("test")

    def test_verb_tenses_collide(self) -> None:
        assert task_signature("reviewing") == task_signature("review")
        assert task_signature("reviewed") == task_signature("review")

    def test_short_tokens_not_over_stemmed(self) -> None:
        # "is" is a stopword anyway, but "bug" is short and content-ful.
        # Must not stem away the final character.
        assert "bug" in task_signature("bug").split()

    def test_alphanumeric_tokens_preserved(self) -> None:
        sig = task_signature("migrate to python3")
        assert "python3" in sig.split()


class TestJaccardSimilarity:
    def test_identical_signatures_return_one(self) -> None:
        assert jaccard_similarity("code review", "code review") == 1.0

    def test_disjoint_signatures_return_zero(self) -> None:
        assert jaccard_similarity("code review", "write docs") == 0.0

    def test_partial_overlap(self) -> None:
        # {"code", "review"} vs {"code", "audit"} -> 1 / 3
        result = jaccard_similarity("code review", "audit code")
        assert abs(result - 1 / 3) < 1e-9

    def test_empty_signature_returns_zero(self) -> None:
        assert jaccard_similarity("", "code") == 0.0
        assert jaccard_similarity("code", "") == 0.0
        assert jaccard_similarity("", "") == 0.0

    def test_symmetric(self) -> None:
        a, b = "code review quality", "review code"
        assert jaccard_similarity(a, b) == jaccard_similarity(b, a)


# Hand-labeled task corpus. Each cluster represents a user intent that
# should group together under nearest-neighbor matching. Phrasing varies
# within a cluster but a shared content word anchors the cluster so the
# token-based approach can discriminate without semantic understanding.
_CLUSTERS: dict[str, list[str]] = {
    "code_review": [
        "Review this code for quality",
        "Do a thorough code review",
        "Can you review the code?",
        "Please review my code carefully",
        "Review the code for issues",
    ],
    "security_scan": [
        "Scan for security vulnerabilities",
        "Run a security scan on the repo",
        "Check for security issues",
        "Perform a security audit",
        "Audit for security holes",
    ],
    "test_generation": [
        "Generate pytest tests for this parser",
        "Add pytest unit tests",
        "Create pytest test cases",
        "Build a pytest test suite",
        "Produce pytest tests for the module",
    ],
    "documentation": [
        "Generate API documentation for this module",
        "Add comprehensive documentation",
        "Create documentation pages",
        "Update the existing documentation",
        "Produce detailed documentation blocks",
    ],
}


class TestClusterCoherence:
    """Verify hand-labeled task clusters group by signature similarity.

    Exit criterion (Phase 0 of Memento-Skills plan): on 20 hand-labeled
    tasks, nearest-neighbor-by-signature clustering should match the
    human labels at least 80% of the time.
    """

    def test_nearest_neighbor_accuracy_meets_threshold(self) -> None:
        labeled_tasks: list[tuple[str, str]] = [
            (cluster, task)
            for cluster, tasks in _CLUSTERS.items()
            for task in tasks
        ]
        signatures: list[tuple[str, str]] = [
            (cluster, task_signature(task)) for cluster, task in labeled_tasks
        ]

        correct = 0
        for i, (cluster_i, sig_i) in enumerate(signatures):
            best_cluster: str | None = None
            best_score = -1.0
            for j, (cluster_j, sig_j) in enumerate(signatures):
                if i == j:
                    continue
                score = jaccard_similarity(sig_i, sig_j)
                if score > best_score:
                    best_score = score
                    best_cluster = cluster_j
            if best_cluster == cluster_i:
                correct += 1

        accuracy = correct / len(signatures)
        assert accuracy >= 0.80, (
            f"Cluster coherence {accuracy:.0%} below 80% threshold. "
            f"Correct: {correct}/{len(signatures)}"
        )
