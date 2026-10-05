from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("thread_id", "message_index"),
        CheckConstraint("message_index >= 0", name="message_index_nonnegative"),
        CheckConstraint("role IN ('user', 'assistant')", name="role_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE")
    )
    message_index: Mapped[int]
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    parts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
