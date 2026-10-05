from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(Text, index=True)
    company_name: Mapped[str] = mapped_column(Text)
    cik: Mapped[str] = mapped_column(Text)
    filing_type: Mapped[str] = mapped_column(Text)
    filing_date: Mapped[date]
    report_date: Mapped[date]
    fiscal_year: Mapped[int]
    accession_number: Mapped[str] = mapped_column(Text, unique=True)
    source_url: Mapped[str] = mapped_column(Text)
    markdown_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
