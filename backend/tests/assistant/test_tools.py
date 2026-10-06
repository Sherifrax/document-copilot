from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic_ai import ModelRetry

from app.assistant.deps import DocumentAgentDeps
from app.assistant.tools import read_chunk, read_surrounding_chunks, search_filings
from app.retrieval.models import SearchHit, SourcePassage

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
THREAD_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000003")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000004")
NEIGHBOR_ID = UUID("00000000-0000-0000-0000-000000000005")


def passage(chunk_id: UUID, chunk_index: int) -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
        document_id=DOCUMENT_ID,
        chunk_index=chunk_index,
        content=f"Evidence {chunk_index}",
        page_number=10,
        section="Item 7",
        token_count=2,
        metadata={},
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date=date(2025, 10, 31),
        report_date=date(2025, 9, 27),
        fiscal_year=2025,
        accession_number="accession",
        source_url="https://www.sec.gov/example",
    )


class FakeRetriever:
    def __init__(self) -> None:
        self.search_call: tuple[object, ...] | None = None

    async def search(self, query, *, filters, limit, neighbor_window):
        self.search_call = (query, filters, limit, neighbor_window)
        return [
            SearchHit(
                passage=passage(CHUNK_ID, 4),
                neighboring_passages=(passage(NEIGHBOR_ID, 5),),
                rrf_score=0.03,
                semantic_rank=1,
                lexical_rank=1,
                semantic_score=0.8,
                lexical_score=2.0,
            )
        ]

    async def read_chunk(self, chunk_id):
        return passage(chunk_id, 4)

    async def read_surrounding_chunks(self, chunk_id, *, before, after):
        assert chunk_id == CHUNK_ID
        assert (before, after) == (2, 1)
        return [passage(CHUNK_ID, 4), passage(NEIGHBOR_ID, 5)]


def context() -> tuple[SimpleNamespace, DocumentAgentDeps, FakeRetriever]:
    retriever = FakeRetriever()
    deps = DocumentAgentDeps(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        retriever=retriever,  # type: ignore[arg-type]
    )
    return SimpleNamespace(deps=deps), deps, retriever


@pytest.mark.anyio
async def test_search_forwards_filters_and_registers_all_returned_evidence() -> None:
    ctx, deps, retriever = context()

    hits = await search_filings(
        ctx,  # type: ignore[arg-type]
        "revenue mix",
        tickers=["aapl"],
        filing_types=["10-k"],
        fiscal_year_from=2021,
        fiscal_year_to=2025,
        limit=5,
    )

    assert len(hits) == 1
    assert hits[0].chunk_id == CHUNK_ID
    query, filters, limit, neighbor_window = retriever.search_call
    assert query == "revenue mix"
    assert filters.tickers == ("AAPL",)
    assert filters.filing_types == ("10-K",)
    assert filters.fiscal_year_from == 2021
    assert filters.fiscal_year_to == 2025
    assert limit == 5
    assert neighbor_window == 0
    assert set(deps.evidence.passages) == {CHUNK_ID}


@pytest.mark.anyio
async def test_read_tools_register_returned_passages() -> None:
    ctx, deps, _ = context()

    await read_chunk(ctx, CHUNK_ID)  # type: ignore[arg-type]
    await read_surrounding_chunks(  # type: ignore[arg-type]
        ctx, CHUNK_ID, before=2, after=1
    )

    assert set(deps.evidence.passages) == {CHUNK_ID, NEIGHBOR_ID}


@pytest.mark.anyio
async def test_search_retries_blank_model_query() -> None:
    ctx, _, _ = context()

    with pytest.raises(ModelRetry, match="non-empty focused evidence query"):
        await search_filings(ctx, "   ")  # type: ignore[arg-type]
