from datetime import date
from types import SimpleNamespace
from typing import Self
from uuid import UUID

import pytest

from app.retrieval import retriever as retriever_module
from app.retrieval.fusion import RankedCandidate
from app.retrieval.models import RetrievalFilters, SourcePassage
from app.retrieval.retriever import ChunkNotFoundError, DocumentRetriever

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
C = UUID("00000000-0000-0000-0000-000000000003")
DOCUMENT = UUID("10000000-0000-0000-0000-000000000001")


class FakeSession:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class FakeSessionFactory:
    def __call__(self) -> FakeSession:
        return FakeSession()


class FakeEmbeddings:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.kwargs: dict[str, object] = {}

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=self.embedding)]
        )


def source_passage(chunk_id: UUID, chunk_index: int) -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
        document_id=DOCUMENT,
        chunk_index=chunk_index,
        content=f"Passage {chunk_index}",
        page_number=12,
        section="Item 7",
        token_count=10,
        metadata={"ticker": "AAPL"},
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date=date(2025, 10, 31),
        report_date=date(2025, 9, 27),
        fiscal_year=2025,
        accession_number="0000320193-25-000079",
        source_url="https://www.sec.gov/example",
    )


def make_retriever(embedding: list[float] | None = None) -> tuple[DocumentRetriever, FakeEmbeddings]:
    embeddings = FakeEmbeddings(embedding or [0.1, 0.2])
    client = SimpleNamespace(embeddings=embeddings)
    retriever = DocumentRetriever(
        FakeSessionFactory(),  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
        embedding_model="text-embedding-3-small",
        embedding_dimensions=2,
    )
    return retriever, embeddings


@pytest.mark.anyio
async def test_search_fuses_and_attaches_ordered_neighbors(monkeypatch) -> None:
    filters = RetrievalFilters(tickers=("AAPL",))
    calls: dict[str, object] = {}

    async def fake_semantic(session, embedding, received_filters, limit):
        calls["semantic"] = (embedding, received_filters, limit)
        return [RankedCandidate(A, 0.9), RankedCandidate(B, 0.8)]

    async def fake_lexical(session, query, received_filters, limit):
        calls["lexical"] = (query, received_filters, limit)
        return [RankedCandidate(B, 8.0)]

    passages = {A: source_passage(A, 4), B: source_passage(B, 5)}

    async def fake_fetch_passages(session, chunk_ids):
        return {chunk_id: passages[chunk_id] for chunk_id in chunk_ids}

    async def fake_fetch_neighbors(session, selected, *, before, after):
        assert before == after == 1
        return [source_passage(C, 3), passages[A], passages[B]]

    monkeypatch.setattr(retriever_module, "semantic_candidates", fake_semantic)
    monkeypatch.setattr(retriever_module, "lexical_candidates", fake_lexical)
    monkeypatch.setattr(retriever_module, "fetch_passages", fake_fetch_passages)
    monkeypatch.setattr(
        retriever_module, "fetch_neighbor_passages", fake_fetch_neighbors
    )
    retriever, embeddings = make_retriever()

    hits = await retriever.search("  revenue mix  ", filters=filters)

    assert [hit.passage.chunk_id for hit in hits] == [B, A]
    assert [item.chunk_index for item in hits[0].neighboring_passages] == [4]
    assert [item.chunk_index for item in hits[1].neighboring_passages] == [3, 5]
    assert calls["semantic"] == ([0.1, 0.2], filters, 50)
    assert calls["lexical"] == ("revenue mix", filters, 50)
    assert embeddings.kwargs == {
        "input": "revenue mix",
        "model": "text-embedding-3-small",
        "dimensions": 2,
    }


@pytest.mark.anyio
async def test_search_returns_empty_when_both_branches_are_empty(monkeypatch) -> None:
    async def empty(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_module, "semantic_candidates", empty)
    monkeypatch.setattr(retriever_module, "lexical_candidates", empty)
    retriever, _ = make_retriever()

    assert await retriever.search("unknown evidence") == []


@pytest.mark.anyio
async def test_search_rejects_wrong_embedding_dimensions(monkeypatch) -> None:
    async def empty(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_module, "lexical_candidates", empty)
    retriever, _ = make_retriever([0.1])

    with pytest.raises(ValueError, match="expected 2"):
        await retriever.search("revenue")


@pytest.mark.anyio
async def test_read_chunk_raises_for_unknown_id(monkeypatch) -> None:
    async def empty(session, chunk_ids):
        return {}

    monkeypatch.setattr(retriever_module, "fetch_passages", empty)
    retriever, _ = make_retriever()

    with pytest.raises(ChunkNotFoundError, match=str(A)):
        await retriever.read_chunk(A)


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["", "   "])
async def test_search_rejects_blank_queries(query: str) -> None:
    retriever, _ = make_retriever()

    with pytest.raises(ValueError, match="must not be blank"):
        await retriever.search(query)
