from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.database.models import DocumentChunk
from ingest.chunking import PreparedChunk
from ingest.chunks import insert_batch, missing_chunks, validate_embedding_response


def prepared_chunk(content_hash: str = "expected") -> PreparedChunk:
    return PreparedChunk(
        document_id=uuid4(),
        chunk_index=3,
        content="Apple revenue content",
        page_number=None,
        section="Item 7. Management's Discussion and Analysis",
        token_count=4,
        metadata={"content_sha256": content_hash},
    )


def test_validate_embedding_response_orders_by_index() -> None:
    response = SimpleNamespace(
        data=[
            SimpleNamespace(index=1, embedding=[0.3, 0.4]),
            SimpleNamespace(index=0, embedding=[0.1, 0.2]),
        ]
    )

    assert validate_embedding_response(response, 2, 2) == [
        [0.1, 0.2],
        [0.3, 0.4],
    ]


def test_validate_embedding_response_rejects_wrong_dimensions() -> None:
    response = SimpleNamespace(
        data=[SimpleNamespace(index=0, embedding=[0.1])]
    )

    with pytest.raises(ValueError, match="1536-dimension"):
        validate_embedding_response(response, 1, 1536)


def test_missing_chunks_skips_matching_hash() -> None:
    prepared = prepared_chunk()
    stored = DocumentChunk(
        document_id=prepared.document_id,
        chunk_index=prepared.chunk_index,
        content=prepared.content,
        page_number=None,
        section=prepared.section,
        token_count=prepared.token_count,
        chunk_metadata={"content_sha256": "expected"},
        embedding=[0.0] * 1536,
    )

    assert missing_chunks([prepared], {prepared.chunk_index: stored}) == []


def test_missing_chunks_rejects_changed_content() -> None:
    prepared = prepared_chunk()
    stored = DocumentChunk(
        document_id=prepared.document_id,
        chunk_index=prepared.chunk_index,
        content="old content",
        page_number=None,
        section=prepared.section,
        token_count=2,
        chunk_metadata={"content_sha256": "old"},
        embedding=[0.0] * 1536,
    )

    with pytest.raises(ValueError, match="different content"):
        missing_chunks([prepared], {prepared.chunk_index: stored})


def test_insert_batch_calls_openai_and_commits(monkeypatch) -> None:
    chunk = prepared_chunk()
    captured: dict[str, object] = {}

    class Embeddings:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])],
                usage=SimpleNamespace(total_tokens=4),
            )

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[DocumentChunk] = []
            self.committed = False

        def add(self, document_chunk: DocumentChunk) -> None:
            self.added.append(document_chunk)

        def commit(self) -> None:
            self.committed = True

    from ingest import chunks

    monkeypatch.setattr(chunks.settings, "openai_embedding_dimensions", 2)
    client = SimpleNamespace(embeddings=Embeddings())
    session = FakeSession()

    assert insert_batch(session, client, [chunk]) == 4
    assert captured["input"] == [chunk.content]
    assert captured["dimensions"] == 2
    assert session.committed
    assert len(session.added) == 1
    assert session.added[0].embedding == [0.1, 0.2]
