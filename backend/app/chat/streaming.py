"""AI SDK-compatible streaming for the stubbed assistant."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID

from httpx import HTTPError
from postgrest.exceptions import APIError

STUB_REPLY = (
    "This is a stubbed response. Retrieval and generation are not connected yet."
)
STREAM_DELAY_SECONDS = 0.04

PersistTurn = Callable[[], Awaitable[None]]


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
