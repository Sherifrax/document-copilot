from datetime import date
from uuid import uuid4

import tiktoken

from app.database.models import SourceDocument
from ingest.chunking import (
    normalize_sec_headings,
    prepare_chunks,
    split_oversized_chunk,
)


def source_document() -> SourceDocument:
    return SourceDocument(
        id=uuid4(),
        ticker="AAPL",
        company_name="Apple Inc.",
        cik="0000320193",
        filing_type="10-K",
        filing_date=date(2024, 11, 1),
        report_date=date(2024, 9, 28),
        fiscal_year=2024,
        accession_number="0000320193-24-000123",
        source_url="https://example.com/aapl.htm",
        markdown_content="unused",
    )


def test_normalize_sec_headings_ignores_toc_links() -> None:
    markdown = """| [Item 1A.](#risk) | Risk Factors |

Item 1. Business

ITEM 1A. Risk Factors

This sentence mentions Item 7. but is not a heading.
"""

    normalized = normalize_sec_headings(markdown)

    assert "| [Item 1A.](#risk) | Risk Factors |" in normalized
    assert "## Item 1. Business" in normalized
    assert "## ITEM 1A. Risk Factors" in normalized
    assert "## This sentence" not in normalized


def test_prepare_chunks_keeps_section_and_metadata(tmp_path) -> None:
    markdown_path = tmp_path / "apple.md"
    markdown_path.write_text(
        """# Apple Inc.

Item 7. Management's Discussion and Analysis

The following table shows net sales by category for 2024, 2023 and 2022.

| Category | 2024 | 2023 |
| --- | ---: | ---: |
| iPhone | 201,183 | 200,583 |
| Services | 96,169 | 85,200 |
""",
        encoding="utf-8",
    )

    chunks = prepare_chunks(source_document(), markdown_path, max_tokens=128)

    assert chunks
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(0 < chunk.token_count <= 128 for chunk in chunks)
    revenue_chunk = next(chunk for chunk in chunks if "net sales by category" in chunk.content)
    assert revenue_chunk.section == "Item 7. Management's Discussion and Analysis"
    assert revenue_chunk.page_number is None
    assert revenue_chunk.metadata["ticker"] == "AAPL"
    assert revenue_chunk.metadata["overlap_tokens"] == 0
    assert len(revenue_chunk.metadata["content_sha256"]) == 64


def test_split_oversized_chunk_repeats_heading_within_hard_limit() -> None:
    parts = split_oversized_chunk(
        "Item 7. Results\n" + "revenue " * 100,
        ["Item 7. Results"],
        max_tokens=32,
    )

    assert len(parts) > 1
    assert all(part.startswith("Item 7. Results\n") for part in parts)
    assert all(len(part) > len("Item 7. Results\n") for part in parts)
    encoding = tiktoken.get_encoding("cl100k_base")
    assert all(len(encoding.encode(part)) <= 32 for part in parts)
