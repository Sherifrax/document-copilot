from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, MetaData, Table, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base

# Supabase owns this table; keep it outside the application's migration metadata.
auth_users = Table(
    "users", MetaData(), Column("id", Uuid, primary_key=True), schema="auth"
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        ForeignKey(auth_users.c.id, ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
