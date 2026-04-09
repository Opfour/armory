#!/usr/bin/env python3
"""Task signature function for eval history indexing.

Normalizes task prompts into stable, comparable signatures used by the
eval history log, the router index (Phase 3), and the immune retrieval
layer (Phase 1). Two prompts with the same core intent but different
phrasing yield the same or highly-overlapping signatures.

Algorithm:
    1. Lowercase the prompt.
    2. Tokenize on word boundaries (keeps alphanumerics).
    3. Drop English stopwords and single-character tokens.
    4. Apply lemmatization-lite: strip common English suffixes.
    5. Deduplicate and sort the remaining tokens.
    6. Join with single spaces.

The canonical string can be used directly as a dict key for exact
matching, or compared via :func:`jaccard_similarity` for fuzzy matching.

This is a deliberately simple lexical approach. If Phase 0 exit criteria
require >50% precision and this approach underperforms, the plan calls
for upgrading to sentence-embedding buckets as a drop-in replacement.
"""
from __future__ import annotations

import re

# Small English stopword set. Intentionally minimal: overly aggressive
# filtering removes domain-specific content words like "test", "build",
# "review", "audit", which carry real task semantics.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "this", "that", "these", "those",
        "i", "me", "my", "mine", "you", "your", "yours",
        "we", "us", "our", "ours", "they", "them", "their",
        "is", "am", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "having", "do", "does", "did", "doing",
        "can", "could", "would", "should", "will", "shall", "may",
        "might", "must", "ought",
        "to", "for", "of", "in", "on", "at", "by", "with", "from",
        "as", "into", "onto", "about", "over", "under", "out",
        "and", "or", "but", "if", "then", "than", "so", "not", "no",
        "here", "there", "what", "which", "who", "whom", "whose",
        "when", "where", "how", "why",
        "it", "its", "some", "any", "all", "each", "every", "either",
        "both", "few", "more", "most", "other", "such",
        "please", "thanks", "thank", "just", "also", "very", "really",
    }
)

# Suffix patterns stripped for lemmatization-lite. Ordered longest-first
# so that compound suffixes (e.g., "ingly") match before their shorter
# supersets ("ly", "ing").
_SUFFIXES: tuple[str, ...] = (
    "ingly",
    "edly",
    "ing",
    "ied",
    "ies",
    "ed",
    "ly",
    "es",
    "s",
)

# Minimum stem length after suffix removal. Prevents over-stemming short
# tokens like "is" -> "i" or "pies" -> "p".
_MIN_STEM_LEN = 3

_WORD_RE = re.compile(r"[a-z0-9]+")


def _stem(token: str) -> str:
    """Strip one common English suffix if it leaves a valid stem.

    Args:
        token: Lowercase token with no whitespace or punctuation.

    Returns:
        The stemmed token, or the original token if no suffix matches
        or stripping would leave a token shorter than ``_MIN_STEM_LEN``.
    """
    if len(token) < _MIN_STEM_LEN + 1:
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= _MIN_STEM_LEN:
            return token[: -len(suffix)]
    return token


def task_signature(prompt: str) -> str:
    """Compute a stable keyword signature for a task prompt.

    Produces a canonical space-joined, sorted, deduplicated keyword
    string. Two prompts sharing the same content words (after stopword
    removal and lemmatization-lite) produce identical signatures.

    Args:
        prompt: The raw task prompt text.

    Returns:
        Canonical signature string. Empty string when the prompt is
        empty or contains only stopwords and single-character tokens.

    Examples:
        >>> task_signature("Review this code for quality")
        'code quality review'
        >>> task_signature("Can you review the code quality?")
        'code quality review'
        >>> task_signature("")
        ''
    """
    if not prompt:
        return ""
    lowered = prompt.lower()
    raw_tokens = _WORD_RE.findall(lowered)
    kept: set[str] = set()
    for tok in raw_tokens:
        if tok in _STOPWORDS:
            continue
        if len(tok) < 2:
            continue
        kept.add(_stem(tok))
    if not kept:
        return ""
    return " ".join(sorted(kept))


def jaccard_similarity(sig_a: str, sig_b: str) -> float:
    """Compute Jaccard similarity between two task signatures.

    Used for fuzzy cluster matching when exact signature equality is
    too strict. Returns 0.0 if either signature is empty.

    Args:
        sig_a: First signature string, as produced by :func:`task_signature`.
        sig_b: Second signature string, as produced by :func:`task_signature`.

    Returns:
        Similarity in ``[0.0, 1.0]`` where 1.0 means identical token
        sets and 0.0 means disjoint token sets.
    """
    tokens_a = set(sig_a.split())
    tokens_b = set(sig_b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)
