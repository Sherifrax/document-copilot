from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class MessageCitation(Base):
    __tablename__ = "message_citations"
    __table_args__ = (
        UniqueConstraint("message_id", "citation_index"),
        CheckConstraint("citation_index > 0", name="citation_index_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE")
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="RESTRICT"), index=True
    )
    citation_index: Mapped[int]
    excerpt: Mapped[str] = mapped_column(Text)
