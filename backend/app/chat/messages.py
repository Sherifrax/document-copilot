"""AI SDK UI message models and conversion helpers."""

from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class CitationData(BaseModel):
    index: int
    chunk_id: UUID = Field(alias="chunkId")
    ticker: str
    company_name: str = Field(alias="companyName")
    filing_type: str = Field(alias="filingType")
    fiscal_year: int = Field(alias="fiscalYear")
    page_number: int | None = Field(alias="pageNumber")
    section: str | None
    source_url: str = Field(alias="sourceUrl")
    excerpt: str


class CitationPart(BaseModel):
    type: Literal["data-citation"]
    data: CitationData


MessagePart = Annotated[TextPart | CitationPart, Field(discriminator="type")]


class UIMessage(BaseModel):
    id: str
    role: Literal["system", "user", "assistant"]
    parts: list[MessagePart]
    metadata: Any | None = None


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    messages: list[UIMessage] = Field(min_length=1)
    trigger: Literal["submit-message"]
    message_id: str | None = Field(default=None, alias="messageId")

    @model_validator(mode="after")
    def validate_new_user_message(self) -> Self:
        message = self.messages[-1]
        if message.role != "user":
            raise ValueError("The final message must have the user role")
        if not message.parts or not user_message_content(message):
            raise ValueError("The final user message must contain non-empty text")
        return self


def user_message_content(message: UIMessage) -> str:
    return "\n".join(
        part.text.strip()
        for part in message.parts
        if isinstance(part, TextPart) and part.text.strip()
    )


def stored_message_to_ui_message(row: dict[str, Any]) -> UIMessage:
    return UIMessage.model_validate(row)
