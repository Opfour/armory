#!/usr/bin/env python3
"""Build the skill-router index from eval history.

Reads ``evals/history.jsonl`` (produced by ``scripts/run_evals.py``) and
produces ``dist/router_index.json`` — a task-signature-keyed map of
packages with their historical pass rates. The skill-router agent
consults this index to rank packages by observed outcomes rather than
static description matching.

Output shape::

    {
      "metadata": {
        "built_at": "2026-04-10T12:34:56Z",
        "source_entries": 1234,
        "unique_signatures": 87,
        "unique_packages": 43
      },
      "index": {
        "<task_signature>": [
          {"package_path": "skills/foo", "pass_rate": 0.83, "sample_count": 42},
          {"package_path": "agents/bar", "pass_rate": 0.72, "sample_count": 18}
        ]
      }
    }

Usage::

    uv run python scripts/build_router_index.py
    uv run python scripts/build_router_index.py --history evals/history.jsonl \\
        --output dist/router_index.json --min-samples 3

Entries with ``sample_count`` below ``--min-samples`` are excluded from
per-signature ranked lists to reduce noise from one-off results.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def read_history(history_path: Path) -> list[dict]:
    """Read and parse a JSONL history log.

    Args:
        history_path: Path to ``evals/history.jsonl``.

    Returns:
        List of parsed entries. Empty list if the file is missing or empty.

    Raises:
        json.JSONDecodeError: If any line fails to parse as JSON.
    """
    if not history_path.exists():
        return []
    entries: list[dict] = []
    for line_num, raw_line in enumerate(
        history_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise json.JSONDecodeError(
                f"Invalid JSON in {history_path}:{line_num}: {exc.msg}",
                exc.doc,
                exc.pos,
            ) from exc
    return entries


def aggregate(
    entries: list[dict],
    min_samples: int = 1,
) -> dict[str, list[dict]]:
    """Aggregate history entries into per-signature package rankings.

    Args:
        entries: Parsed history log entries.
        min_samples: Minimum observations required for a (signature,
            package) pair to appear in the output. Pairs below this
            threshold are dropped to reduce noise.

    Returns:
        Map of ``task_signature -> [{"package_path", "pass_rate",
        "sample_count"}, ...]`` with each list sorted by descending
        pass rate, then descending sample count as tiebreaker.
    """
    counts: dict[tuple[str, str], list[int]] = {}
    for entry in entries:
        sig = str(entry.get("task_signature", ""))
        pkg = str(entry.get("package_path", ""))
        if not sig or not pkg:
            continue
        key = (sig, pkg)
        bucket = counts.setdefault(key, [0, 0])
        bucket[1] += 1
        if entry.get("oracle_verdict") == "pass":
            bucket[0] += 1

    by_signature: dict[str, list[dict]] = {}
    for (sig, pkg), (passed, total) in counts.items():
        if total < min_samples:
            continue
        by_signature.setdefault(sig, []).append(
            {
                "package_path": pkg,
                "pass_rate": passed / total,
                "sample_count": total,
            }
        )

    for sig in by_signature:
        by_signature[sig].sort(
            key=lambda item: (item["pass_rate"], item["sample_count"]),
            reverse=True,
        )

    return by_signature


def build_index(
    entries: list[dict],
    min_samples: int = 1,
) -> dict:
    """Build the full router index payload.

    Args:
        entries: Parsed history log entries.
        min_samples: Minimum sample threshold for inclusion.

    Returns:
        A dict with ``metadata`` and ``index`` keys ready to serialize.
    """
    by_signature = aggregate(entries, min_samples=min_samples)
    unique_packages = {
        item["package_path"]
        for items in by_signature.values()
        for item in items
    }
    return {
        "metadata": {
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_entries": len(entries),
            "unique_signatures": len(by_signature),
            "unique_packages": len(unique_packages),
            "min_samples": min_samples,
        },
        "index": by_signature,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the skill-router index from eval history",
    )
    parser.add_argument(
        "--history",
        default="evals/history.jsonl",
        help="Path to the append-only eval history log",
    )
    parser.add_argument(
        "--output",
        default="dist/router_index.json",
        help="Path to write the router index JSON",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=1,
        help="Minimum observations per (signature, package) pair",
    )
    args = parser.parse_args()

    history_path = _REPO_ROOT / args.history
    entries = read_history(history_path)
    if not entries:
        print(f"No history entries found at {args.history}", file=sys.stderr)
        print("Index will be built with zero entries.", file=sys.stderr)

    payload = build_index(entries, min_samples=args.min_samples)

    output_path = _REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    meta = payload["metadata"]
    print(f"Router index written to {args.output}")
    print(
        f"  Source entries: {meta['source_entries']}, "
        f"Signatures: {meta['unique_signatures']}, "
        f"Packages: {meta['unique_packages']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
