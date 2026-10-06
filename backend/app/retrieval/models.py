"""Typed inputs and outputs for document retrieval."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RetrievalFilters(BaseModel):
    """Optional filing constraints applied to every retrieval branch."""

    model_config = ConfigDict(frozen=True)

    tickers: tuple[str, ...] = ()
    filing_types: tuple[str, ...] = ()
    fiscal_year_from: int | None = Field(default=None, ge=1900)
    fiscal_year_to: int | None = Field(default=None, ge=1900)

    @field_validator("tickers", "filing_types", mode="before")
    @classmethod
    def normalize_values(cls, values: object) -> tuple[str, ...]:
        if values is None:
            return ()
        return tuple(
            dict.fromkeys(str(value).strip().upper() for value in values if str(value).strip())
        )

    @model_validator(mode="after")
    def validate_year_range(self) -> "RetrievalFilters":
        if (
            self.fiscal_year_from is not None
            and self.fiscal_year_to is not None
            and self.fiscal_year_from > self.fiscal_year_to
        ):
            raise ValueError("fiscal_year_from must not exceed fiscal_year_to")
        return self


class SourcePassage(BaseModel):
    """A citable chunk with its filing metadata."""

    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int | None
    section: str | None
    token_count: int
    metadata: dict[str, Any]
    ticker: str
    company_name: str
    filing_type: str
    filing_date: date
    report_date: date
    fiscal_year: int
    accession_number: str
    source_url: str


class SearchHit(BaseModel):
    """A fused search result and the adjacent context used for grounding."""

    model_config = ConfigDict(frozen=True)

    passage: SourcePassage
    neighboring_passages: tuple[SourcePassage, ...]
    rrf_score: float
    semantic_rank: int | None
    lexical_rank: int | None
    semantic_score: float | None
    lexical_score: float | None
