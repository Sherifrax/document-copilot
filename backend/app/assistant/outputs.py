"""Structured agent output and its validated representation."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.retrieval.models import SourcePassage


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=1)
    chunk_id: UUID
    excerpt: str = Field(min_length=1)


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str = Field(min_length=1)
    citations: tuple[Citation, ...] = ()
    insufficient_evidence: bool = False

    @model_validator(mode="after")
    def validate_insufficient_evidence(self) -> "GroundedAnswer":
        if self.insufficient_evidence and self.citations:
            raise ValueError("insufficient-evidence answers must not include citations")
        return self


class ValidatedGroundedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: tuple[Citation, ...]
    cited_passages: tuple[SourcePassage, ...]
    insufficient_evidence: bool
