"""Import all models so Alembic can discover the complete schema."""

from app.database.models.base import Base
from app.database.models.chat_messages import ChatMessage
from app.database.models.chat_threads import ChatThread
from app.database.models.document_chunks import DocumentChunk
from app.database.models.message_citations import MessageCitation
from app.database.models.source_documents import SourceDocument
from app.database.models.users import User

__all__ = [
    "Base",
    "ChatMessage",
    "ChatThread",
    "DocumentChunk",
    "MessageCitation",
    "SourceDocument",
    "User",
]
