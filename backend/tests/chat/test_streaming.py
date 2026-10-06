import asyncio
import json
from datetime import date
from uuid import UUID, uuid4

from postgrest.exceptions import APIError

from app.assistant.outputs import Citation, ValidatedGroundedAnswer
from app.chat.streaming import stream_grounded_reply, stream_stubbed_reply
from app.retrieval.models import SourcePassage

CHUNK_ID = UUID("11111111-1111-1111-1111-111111111111")


def grounded_result() -> ValidatedGroundedAnswer:
    passage = SourcePassage(
        chunk_id=CHUNK_ID,
        document_id=UUID("22222222-2222-2222-2222-222222222222"),
        chunk_index=1,
        content="Services revenue increased.",
        page_number=20,
        section="Item 7",
        token_count=3,
        metadata={},
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date=date(2025, 10, 31),
        report_date=date(2025, 9, 27),
        fiscal_year=2025,
        accession_number="accession",
        source_url="https://www.sec.gov/example",
    )
    return ValidatedGroundedAnswer(
        answer="Services revenue increased. [1]",
        citations=(Citation(index=1, chunk_id=CHUNK_ID, excerpt=passage.content),),
        cited_passages=(passage,),
        insufficient_evidence=False,
    )


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


def test_grounded_stream_emits_citation_and_persists_validated_result() -> None:
    result = grounded_result()
    persisted: list[ValidatedGroundedAnswer] = []

    async def run() -> list[str]:
        async def generate() -> ValidatedGroundedAnswer:
            return result

        async def persist(answer: ValidatedGroundedAnswer) -> None:
            persisted.append(answer)

        return [
            event
            async for event in stream_grounded_reply(uuid4(), generate, persist)
        ]

    events = asyncio.run(run())
    payloads = [
        json.loads(event.removeprefix("data: "))
        for event in events
        if event != "data: [DONE]\n\n"
    ]

    citation_event = next(item for item in payloads if item["type"] == "data-citation")
    assert citation_event["data"]["chunkId"] == str(CHUNK_ID)
    assert citation_event["data"]["ticker"] == "AAPL"
    assert persisted == [result]
    assert payloads[-1]["type"] == "finish"


def test_generation_failure_emits_error_and_does_not_persist() -> None:
    persisted = False

    async def run() -> list[str]:
        async def fail() -> ValidatedGroundedAnswer:
            raise RuntimeError("model failed")

        async def persist(answer: ValidatedGroundedAnswer) -> None:
            nonlocal persisted
            persisted = True

        return [
            event async for event in stream_grounded_reply(uuid4(), fail, persist)
        ]

    events = asyncio.run(run())

    assert any("Unable to generate a grounded response" in event for event in events)
    assert not persisted
    assert events[-1] == "data: [DONE]\n\n"
