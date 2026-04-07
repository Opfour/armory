#!/usr/bin/env python3
"""Assertion checker library for eval case verification.

Provides structured assertion functions that evaluate agent outputs
against expected patterns. Used by run_evals.py (the ground-truth oracle)
to produce pass/fail verdicts from cases.yaml assertion definitions.

Assertion types:
  contains       — substring match
  not_contains   — absence check
  matches_regex  — regex pattern match
  output_format  — structural format validation
  calls_tool     — tool invocation detection
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class AssertionResult:
    """Result of a single assertion check."""

    assertion_type: str
    target: str
    passed: bool
    weight: float
    detail: str


def check_contains(output: str, target: str) -> bool:
    """Check if output contains the target substring (case-insensitive)."""
    return target.lower() in output.lower()


def check_not_contains(output: str, target: str) -> bool:
    """Check that output does NOT contain the target substring (case-insensitive)."""
    return target.lower() not in output.lower()


def check_matches_regex(output: str, target: str) -> bool:
    """Check if output matches the target regex pattern."""
    return bool(re.search(target, output, re.MULTILINE | re.IGNORECASE))


def check_output_format(output: str, target: str) -> bool:
    """Validate output matches a structural format descriptor.

    Supported formats:
      json            — valid JSON
      markdown_table  — contains pipe-delimited table rows
      numbered_list   — contains numbered list items (1. 2. 3.)
      yaml            — valid YAML (basic heuristic: key-value pairs)
      code_block      — contains fenced code blocks (```)
    """
    match target:
        case "json":
            try:
                json.loads(output)
                return True
            except (json.JSONDecodeError, ValueError):
                return False
        case "markdown_table":
            return bool(re.search(r"\|.*\|.*\n\|[-\s|:]+\|", output))
        case "numbered_list":
            return bool(re.search(r"^\s*\d+\.\s+\S", output, re.MULTILINE))
        case "yaml":
            return bool(re.search(r"^\w[\w\s]*:\s+\S", output, re.MULTILINE))
        case "code_block":
            return output.count("```") >= 2
        case _:
            msg = f"Unknown output format: {target}"
            raise ValueError(msg)


def check_calls_tool(output: str, target: str) -> bool:
    """Check if a tool invocation appears in the output.

    Detects tool usage through multiple signals since ``claude -p``
    text output does not include structured tool call metadata.
    Checks for: XML tool blocks, invoke patterns, plain-text references,
    and tool-specific output signatures.
    """
    # Structured tool use pattern (from Claude output)
    if re.search(rf"<tool_use>.*?{re.escape(target)}.*?</tool_use>", output, re.DOTALL):
        return True
    # Tool name in invoke blocks
    if re.search(rf'invoke name="{re.escape(target)}"', output):
        return True
    # Plain-text reference to using the tool
    if re.search(rf"\b(used?|invoke[ds]?|call(?:ed|ing)?|ran|running)\s+(?:the\s+)?{re.escape(target)}\b", output, re.IGNORECASE):
        return True

    # Tool-specific output signatures (heuristic for text output mode)
    tool_signatures: dict[str, str] = {
        "Read": r"(?:read|reading|contents of)\s+[`'\"]?[\w/.-]+\.\w+",
        "Grep": r"(?:search|grep|found \d+ match|rg )",
        "Glob": r"(?:glob|matching files|found \d+ files)",
        "Bash": r"(?:```(?:bash|sh|zsh)|^\$\s|\bran\b.*\bcommand\b)",
        "Write": r"(?:(?:writ(?:ten|e|ing)|wrote)\s+(?:to\s+|the\s+|file\s+|a\s+)*[`'\"]?[\w/.-]+\.\w+|created?\s+(?:the\s+)?(?:a\s+)?file)",
        "Edit": r"(?:edit(?:ed|ing)\s+(?:the\s+|a\s+)?(?:file\s+)?[`'\"]?[\w/.-]+\.\w+|modif(?:ied|ying)\s+(?:the\s+)?file)",
        "WebSearch": r"(?:search(?:ed|ing)\s+(?:the\s+)?web|web search|found.*online)",
        "WebFetch": r"(?:fetch(?:ed|ing)\s+(?:from\s+)?https?://|retrieved.*URL)",
        "Agent": r"(?:spawn(?:ed|ing)\s+(?:a\s+)?(?:sub)?agent|delegat(?:ed|ing)\s+to)",
    }
    if target in tool_signatures:
        return bool(re.search(tool_signatures[target], output, re.IGNORECASE | re.MULTILINE))

    return False


# Dispatch table mapping assertion type strings to checker functions
CHECKERS: dict[str, Callable[[str, str], bool]] = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "matches_regex": check_matches_regex,
    "output_format": check_output_format,
    "calls_tool": check_calls_tool,
}


def run_assertion(output: str, assertion: dict) -> AssertionResult:
    """Execute a single assertion against the output.

    Args:
        output: The agent's full output text.
        assertion: Dict with 'type', 'target', and optional 'weight' keys.

    Returns:
        AssertionResult with pass/fail verdict and detail.
    """
    a_type = assertion["type"]
    target = assertion["target"]
    weight = assertion.get("weight", 1.0)

    checker = CHECKERS.get(a_type)
    if checker is None:
        return AssertionResult(
            assertion_type=a_type,
            target=target,
            passed=False,
            weight=weight,
            detail=f"Unknown assertion type: {a_type}",
        )

    try:
        passed = checker(output, target)
    except Exception as e:
        return AssertionResult(
            assertion_type=a_type,
            target=target,
            passed=False,
            weight=weight,
            detail=f"Assertion raised error: {e}",
        )

    detail = "passed" if passed else f"failed: {a_type}('{target}') not satisfied"
    return AssertionResult(
        assertion_type=a_type,
        target=target,
        passed=passed,
        weight=weight,
        detail=detail,
    )


def run_all_assertions(output: str, assertions: list[dict]) -> tuple[bool, float, list[AssertionResult]]:
    """Execute all assertions against the output.

    Args:
        output: The agent's full output text.
        assertions: List of assertion dicts from cases.yaml.

    Returns:
        Tuple of (all_passed, weighted_score, results).
        weighted_score is between 0.0 and 1.0.
    """
    if not assertions:
        return True, 1.0, []

    results = [run_assertion(output, a) for a in assertions]
    total_weight = sum(r.weight for r in results)
    if total_weight == 0:
        return True, 1.0, results

    weighted_score = sum(r.weight for r in results if r.passed) / total_weight
    all_passed = all(r.passed for r in results)
    return all_passed, weighted_score, results
