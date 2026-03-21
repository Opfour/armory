#!/usr/bin/env python3
"""Search arXiv for academic papers and output structured results."""
from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import arxiv


def _serialize_result(result: arxiv.Result) -> dict[str, object]:
    """Convert an arxiv.Result to a JSON-serializable dict."""
    return {
        "id": result.get_short_id(),
        "title": result.title,
        "authors": [a.name for a in result.authors],
        "abstract": result.summary,
        "published": result.published.isoformat() if result.published else None,
        "updated": result.updated.isoformat() if result.updated else None,
        "primary_category": result.primary_category,
        "categories": result.categories,
        "doi": result.doi,
        "journal_ref": result.journal_ref,
        "pdf_url": result.pdf_url,
        "entry_url": result.entry_id,
    }


def search(
    query: str,
    *,
    max_results: int,
    sort_by: str,
    sort_order: str,
    id_list: list[str] | None = None,
) -> list[dict[str, object]]:
    """Execute an arXiv search and return serialized results."""
    import arxiv

    sort_by_map = {
        "relevance": arxiv.SortCriterion.Relevance,
        "submitted": arxiv.SortCriterion.SubmittedDate,
        "updated": arxiv.SortCriterion.LastUpdatedDate,
    }
    sort_order_map = {
        "descending": arxiv.SortOrder.Descending,
        "ascending": arxiv.SortOrder.Ascending,
    }

    s = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=sort_by_map[sort_by],
        sort_order=sort_order_map[sort_order],
        id_list=id_list or [],
    )

    client = arxiv.Client(page_size=min(max_results, 100), delay_seconds=3.0, num_retries=3)
    return [_serialize_result(r) for r in client.results(s)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search arXiv for academic papers.",
        epilog="Requires: uv run --with arxiv python scripts/arxiv_search.py ...",
    )
    parser.add_argument("query", help="arXiv search query (supports field prefixes: au:, ti:, abs:, cat:)")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results (default: 10)")
    parser.add_argument(
        "--sort-by",
        choices=["relevance", "submitted", "updated"],
        default="relevance",
        help="Sort criterion (default: relevance)",
    )
    parser.add_argument(
        "--sort-order",
        choices=["descending", "ascending"],
        default="descending",
        help="Sort order (default: descending)",
    )
    parser.add_argument("--ids", nargs="*", help="Specific arXiv paper IDs to fetch (e.g., 2301.07041)")
    parser.add_argument("--compact", action="store_true", help="Output one JSON object per line instead of pretty-printing")
    args = parser.parse_args()

    results = search(
        args.query,
        max_results=args.max_results,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
        id_list=args.ids,
    )

    if not results:
        print("No results found.", file=sys.stderr)
        return 1

    if args.compact:
        for r in results:
            print(json.dumps(r))
    else:
        print(json.dumps(results, indent=2))

    print(f"\n{len(results)} result(s) returned.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
