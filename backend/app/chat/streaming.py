"""AI SDK-compatible streaming for the stubbed assistant."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID

import structlog
from httpx import HTTPError
from postgrest.exceptions import APIError

from app.assistant.outputs import ValidatedGroundedAnswer

STUB_REPLY = (
    "This is a stubbed response. Retrieval and generation are not connected yet."
)
STREAM_DELAY_SECONDS = 0.04

PersistTurn = Callable[[], Awaitable[None]]
GenerateAnswer = Callable[[], Awaitable[ValidatedGroundedAnswer]]
PersistGroundedTurn = Callable[[ValidatedGroundedAnswer], Awaitable[None]]


def server_sent_event(payload: dict[str, object] | str) -> str:
    data = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, separators=(",", ":"))
    )
    return f"data: {data}\n\n"


def text_chunks(text: str) -> list[str]:
    words = text.split(" ")
    return [word if index == 0 else f" {word}" for index, word in enumerate(words)]


async def stream_stubbed_reply(
    assistant_message_id: UUID,
    persist_turn: PersistTurn,
    *,
    delay_seconds: float = STREAM_DELAY_SECONDS,
) -> AsyncIterator[str]:
    text_part_id = f"text-{assistant_message_id}"
    yield server_sent_event({"type": "start", "messageId": str(assistant_message_id)})
    yield server_sent_event({"type": "start-step"})
    yield server_sent_event({"type": "text-start", "id": text_part_id})

    for chunk in text_chunks(STUB_REPLY):
        yield server_sent_event(
            {"type": "text-delta", "id": text_part_id, "delta": chunk}
        )
        if delay_seconds:
            await asyncio.sleep(delay_seconds)

    try:
        await persist_turn()
    except (APIError, HTTPError):
        yield server_sent_event(
            {"type": "error", "errorText": "Unable to save the completed response"}
        )
        yield server_sent_event("[DONE]")
        return

    yield server_sent_event({"type": "text-end", "id": text_part_id})
    yield server_sent_event({"type": "finish-step"})
    yield server_sent_event({"type": "finish"})
    yield server_sent_event("[DONE]")


async def stream_grounded_reply(
    assistant_message_id: UUID,
    generate_answer: GenerateAnswer,
    persist_turn: PersistGroundedTurn,
    *,
    delay_seconds: float = 0,
) -> AsyncIterator[str]:
    """Generate and validate first, then stream and persist a grounded answer."""
    yield server_sent_event({"type": "start", "messageId": str(assistant_message_id)})
    yield server_sent_event({"type": "start-step"})

    try:
        result = await generate_answer()
    except Exception:  # noqa: BLE001 - the SSE boundary must terminate every failed run
        structlog.get_logger(__name__).exception("stream_generation_failed")
        yield server_sent_event(
            {"type": "error", "errorText": "Unable to generate a grounded response"}
        )
        yield server_sent_event("[DONE]")
        return

    text_part_id = f"text-{assistant_message_id}"
    yield server_sent_event({"type": "text-start", "id": text_part_id})
    for chunk in text_chunks(result.answer):
        yield server_sent_event(
            {"type": "text-delta", "id": text_part_id, "delta": chunk}
        )
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
    yield server_sent_event({"type": "text-end", "id": text_part_id})

    for citation, passage in zip(
        result.citations, result.cited_passages, strict=True
    ):
        yield server_sent_event(
            {
                "type": "data-citation",
                "data": {
                    "index": citation.index,
                    "chunkId": str(citation.chunk_id),
                    "ticker": passage.ticker,
                    "companyName": passage.company_name,
                    "filingType": passage.filing_type,
                    "fiscalYear": passage.fiscal_year,
                    "pageNumber": passage.page_number,
                    "section": passage.section,
                    "sourceUrl": passage.source_url,
                    "excerpt": citation.excerpt,
                },
            }
        )

    try:
        await persist_turn(result)
    except (APIError, HTTPError):
        structlog.get_logger(__name__).exception("stream_persistence_failed")
        yield server_sent_event(
            {"type": "error", "errorText": "Unable to save the completed response"}
        )
        yield server_sent_event("[DONE]")
        return

    yield server_sent_event({"type": "finish-step"})
    yield server_sent_event({"type": "finish"})
    yield server_sent_event("[DONE]")
