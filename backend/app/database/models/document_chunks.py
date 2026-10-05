from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        CheckConstraint("chunk_index >= 0", name="chunk_index_nonnegative"),
        CheckConstraint("token_count >= 0", name="token_count_nonnegative"),
        Index(
            "ix_document_chunks_search_vector", "search_vector", postgresql_using="gin"
        ),
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(Text)
    token_count: Mapped[int]
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english'::regconfig, content)", persisted=True)
    )
