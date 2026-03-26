---
name: arxiv-search
type: utility
description: 'Searches arXiv for academic papers by keyword, author, title, or category
  and outputs structured JSON with full metadata (title, authors, abstract, dates,
  categories, DOI, PDF URL). Supports field-prefixed queries (au:, ti:, abs:, cat:),
  sorting by relevance/date, result limits, and direct ID lookup. Use this utility
  when you need to discover research papers, build a reading list, gather references
  for a literature review, fetch paper metadata by arXiv ID, or survey recent publications
  in a research area. Complements research-critique (per-paper analysis) and literature-review
  (multi-paper synthesis).

  '
metadata:
  version: 1.0.0
  complements: [literature-review, research-critique]
  category: review
  tags: [arxiv, academic, papers, search]
  difficulty: beginner
utility: {runtime: python, entry_point: scripts/arxiv_search.py, executable: true}
---
# arxiv-search

Search arXiv and retrieve structured paper metadata.

## Dependencies

```bash
uv pip install arxiv
```

## Usage

```bash
# Keyword search
uv run --with arxiv python scripts/arxiv_search.py "transformer attention mechanisms"

# Author search
uv run --with arxiv python scripts/arxiv_search.py "au:vaswani AND ti:attention"

# Category-scoped search with date sorting
uv run --with arxiv python scripts/arxiv_search.py "cat:cs.CL AND abs:retrieval augmented" \
  --sort-by submitted --max-results 20

# Fetch specific papers by ID
uv run --with arxiv python scripts/arxiv_search.py "" --ids 2301.07041 1706.03762

# Compact output (one JSON per line, for piping)
uv run --with arxiv python scripts/arxiv_search.py "large language models" --compact
```

## Query Syntax

arXiv supports field-prefixed boolean queries:

| Prefix | Field | Example |
|--------|-------|---------|
| `ti:` | Title | `ti:attention mechanism` |
| `au:` | Author | `au:vaswani` |
| `abs:` | Abstract | `abs:retrieval augmented generation` |
| `cat:` | Category | `cat:cs.CL` |
| `all:` | All fields | `all:transformer` |

Combine with `AND`, `OR`, `ANDNOT`:
```
au:bengio AND ti:representation learning ANDNOT cat:cs.CV
```

## Output Format

```json
[
  {
    "id": "2301.07041v1",
    "title": "Paper Title",
    "authors": ["Author One", "Author Two"],
    "abstract": "Full abstract text...",
    "published": "2023-01-17T18:59:00+00:00",
    "updated": "2023-03-10T12:00:00+00:00",
    "primary_category": "cs.CL",
    "categories": ["cs.CL", "cs.AI"],
    "doi": "10.1234/example",
    "journal_ref": "Nature 2023",
    "pdf_url": "http://arxiv.org/pdf/2301.07041v1",
    "entry_url": "http://arxiv.org/abs/2301.07041v1"
  }
]
```

## Rate Limiting

The script enforces a 3-second delay between API requests and retries up to 3 times on failure, respecting arXiv's usage policies. Page size is capped at 100 results per request.

## Limitations

- arXiv API only — does not search Semantic Scholar, PubMed, or other databases.
- No full-text search; queries match metadata fields (title, abstract, author, category).
- Public API tier with no authentication — subject to arXiv rate limits.
- PDF download is not performed; use the `pdf_url` field to retrieve papers separately.
