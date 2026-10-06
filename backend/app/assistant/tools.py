"""Bounded retrieval tools exposed to the document agent."""

from typing import Annotated
from uuid import UUID

from pydantic import Field
from pydantic_ai import ModelRetry, RunContext

from app.assistant.deps import DocumentAgentDeps
from app.retrieval.models import RetrievalFilters, SourcePassage


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    tickers: list[str] | None = None,
    filing_types: list[str] | None = None,
    fiscal_year_from: int | None = None,
    fiscal_year_to: int | None = None,
    limit: Annotated[int, Field(ge=1, le=6)] = 5,
) -> list[SourcePassage]:
    """Search SEC filings for passages relevant to a focused question.

    Args:
        ctx: Agent runtime dependencies.
        query: Focused evidence query, not the entire requested final answer.
        tickers: Optional company ticker symbols to constrain the search.
        filing_types: Optional filing types such as 10-K or 10-Q.
        fiscal_year_from: Optional inclusive first fiscal year.
        fiscal_year_to: Optional inclusive final fiscal year.
        limit: Maximum fused passages to return.
    """
    if not query.strip():
        raise ModelRetry(
            "Provide a non-empty focused evidence query, or return an "
            "insufficient-evidence answer when the user's scope is missing."
        )
    hits = await ctx.deps.retriever.search(
        query.strip(),
        filters=RetrievalFilters(
            tickers=tuple(tickers or ()),
            filing_types=tuple(filing_types or ()),
            fiscal_year_from=fiscal_year_from,
            fiscal_year_to=fiscal_year_to,
        ),
        limit=limit,
        neighbor_window=0,
    )
    ctx.deps.evidence.search_calls += 1
    passages = [hit.passage for hit in hits]
    for passage in passages:
        ctx.deps.evidence.register(passage)
    return passages


async def read_chunk(
    ctx: RunContext[DocumentAgentDeps], chunk_id: UUID
) -> SourcePassage:
    """Read and register one exact filing chunk by ID.

    Args:
        ctx: Agent runtime dependencies.
        chunk_id: Stable chunk identifier returned by a prior search.
    """
    passage = await ctx.deps.retriever.read_chunk(chunk_id)
    ctx.deps.evidence.inspection_calls += 1
    ctx.deps.evidence.register(passage)
    return passage


async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps],
    chunk_id: UUID,
    before: Annotated[int, Field(ge=0, le=3)] = 1,
    after: Annotated[int, Field(ge=0, le=3)] = 1,
) -> list[SourcePassage]:
    """Read and register nearby chunks from the same filing.

    Args:
        ctx: Agent runtime dependencies.
        chunk_id: Stable chunk identifier returned by a prior search.
        before: Number of preceding chunks to read.
        after: Number of following chunks to read.
    """
    passages = await ctx.deps.retriever.read_surrounding_chunks(
        chunk_id, before=before, after=after
    )
    ctx.deps.evidence.inspection_calls += 1
    for passage in passages:
        ctx.deps.evidence.register(passage)
    return passages
