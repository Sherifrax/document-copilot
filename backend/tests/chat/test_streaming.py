import asyncio
from uuid import uuid4

from postgrest.exceptions import APIError

from app.chat.streaming import stream_stubbed_reply


def test_cancelled_stream_does_not_persist() -> None:
    persisted = False

    async def run() -> None:
        nonlocal persisted

        async def persist() -> None:
            nonlocal persisted
            persisted = True

        stream = stream_stubbed_reply(uuid4(), persist, delay_seconds=0)
        await anext(stream)
        await stream.aclose()

    asyncio.run(run())

    assert persisted is False


def test_persistence_failure_emits_error_without_finish() -> None:
    async def run() -> list[str]:
        async def fail_to_persist() -> None:
            raise APIError(
                {"code": "P0001", "message": "failed", "hint": None, "details": None}
            )

        return [
            event
            async for event in stream_stubbed_reply(
                uuid4(), fail_to_persist, delay_seconds=0
            )
        ]

    events = asyncio.run(run())

    assert any('"type":"error"' in event for event in events)
    assert not any('"type":"finish"' in event for event in events)
    assert events[-1] == "data: [DONE]\n\n"
