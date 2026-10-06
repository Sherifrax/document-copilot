"""SQL queries for semantic, lexical, and source-passage retrieval."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.fusion import RankedCandidate
from app.retrieval.models import RetrievalFilters, SourcePassage


def _with_filters(statement: Select, filters: RetrievalFilters) -> Select:
    if filters.tickers:
        statement = statement.where(SourceDocument.ticker.in_(filters.tickers))
    if filters.filing_types:
        statement = statement.where(
            SourceDocument.filing_type.in_(filters.filing_types)
        )
    if filters.fiscal_year_from is not None:
        statement = statement.where(
            SourceDocument.fiscal_year >= filters.fiscal_year_from
        )
    if filters.fiscal_year_to is not None:
        statement = statement.where(
            SourceDocument.fiscal_year <= filters.fiscal_year_to
        )
    return statement


def semantic_statement(
    embedding: Sequence[float], filters: RetrievalFilters, limit: int
) -> Select:
    distance = DocumentChunk.embedding.cosine_distance(list(embedding)).label("distance")
    statement = (
        select(DocumentChunk.id.label("chunk_id"), distance)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .order_by(distance)
        .limit(limit)
    )
    return _with_filters(statement, filters)


def lexical_statement(query: str, filters: RetrievalFilters, limit: int) -> Select:
    tsquery = func.websearch_to_tsquery(cast("english", REGCONFIG), query)
    rank = func.ts_rank_cd(DocumentChunk.search_vector, tsquery).label("rank")
    statement = (
        select(DocumentChunk.id.label("chunk_id"), rank)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.search_vector.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(limit)
    )
    return _with_filters(statement, filters)


async def semantic_candidates(
    session: AsyncSession,
    embedding: Sequence[float],
    filters: RetrievalFilters,
    limit: int,
) -> list[RankedCandidate]:
    rows = await session.execute(semantic_statement(embedding, filters, limit))
    return [
        RankedCandidate(chunk_id=row.chunk_id, score=1.0 - float(row.distance))
        for row in rows
    ]


async def lexical_candidates(
    session: AsyncSession,
    query: str,
    filters: RetrievalFilters,
    limit: int,
) -> list[RankedCandidate]:
    rows = await session.execute(lexical_statement(query, filters, limit))
    return [
        RankedCandidate(chunk_id=row.chunk_id, score=float(row.rank)) for row in rows
    ]


def _passage_columns() -> tuple[object, ...]:
    return (
        DocumentChunk.id.label("chunk_id"),
        DocumentChunk.document_id,
        DocumentChunk.chunk_index,
        DocumentChunk.content,
        DocumentChunk.page_number,
        DocumentChunk.section,
        DocumentChunk.token_count,
        DocumentChunk.chunk_metadata.label("metadata"),
        SourceDocument.ticker,
        SourceDocument.company_name,
        SourceDocument.filing_type,
        SourceDocument.filing_date,
        SourceDocument.report_date,
        SourceDocument.fiscal_year,
        SourceDocument.accession_number,
        SourceDocument.source_url,
    )


def _passages_from_rows(rows: object) -> list[SourcePassage]:
    return [SourcePassage.model_validate(row._mapping) for row in rows]  # type: ignore[attr-defined]


async def fetch_passages(
    session: AsyncSession, chunk_ids: Sequence[UUID]
) -> dict[UUID, SourcePassage]:
    if not chunk_ids:
        return {}
    statement = (
        select(*_passage_columns())
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(chunk_ids))
    )
    passages = _passages_from_rows(await session.execute(statement))
    return {passage.chunk_id: passage for passage in passages}


async def fetch_neighbor_passages(
    session: AsyncSession,
    passages: Sequence[SourcePassage],
    *,
    before: int,
    after: int,
) -> list[SourcePassage]:
    if not passages or before + after == 0:
        return []
    ranges = [
        and_(
            DocumentChunk.document_id == passage.document_id,
            DocumentChunk.chunk_index >= passage.chunk_index - before,
            DocumentChunk.chunk_index <= passage.chunk_index + after,
        )
        for passage in passages
    ]
    statement = (
        select(*_passage_columns())
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(or_(*ranges))
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
    )
    return _passages_from_rows(await session.execute(statement))
