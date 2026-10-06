from types import SimpleNamespace
from uuid import UUID

import pytest

from app.assistant.outputs import GroundedAnswer
from app.chat.messages import TextPart, UIMessage
from app.chat.orchestrator import ChatOrchestrator
from app.grounding.validator import GroundingValidator

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
THREAD_ID = UUID("22222222-2222-2222-2222-222222222222")


class FakeAgent:
    def __init__(self) -> None:
        self.call: dict[str, object] = {}

    async def run(self, prompt: str, **kwargs: object) -> SimpleNamespace:
        self.call = {"prompt": prompt, **kwargs}
        return SimpleNamespace(
            output=GroundedAnswer(
                answer="The corpus does not contain enough evidence.",
                insufficient_evidence=True,
            )
        )


@pytest.mark.anyio
async def test_orchestrator_passes_history_and_validates_output() -> None:
    agent = FakeAgent()
    retriever = SimpleNamespace()
    orchestrator = ChatOrchestrator(
        agent,  # type: ignore[arg-type]
        retriever,  # type: ignore[arg-type]
        GroundingValidator(),
    )
    messages = [
        UIMessage(
            id="user-1",
            role="user",
            parts=[TextPart(type="text", text="Earlier question")],
        ),
        UIMessage(
            id="assistant-1",
            role="assistant",
            parts=[TextPart(type="text", text="Earlier answer")],
        ),
        UIMessage(
            id="user-2",
            role="user",
            parts=[TextPart(type="text", text="Current question")],
        ),
    ]

    result = await orchestrator.answer(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        messages=messages,
    )

    assert result.insufficient_evidence
    assert agent.call["prompt"] == "Current question"
    assert len(agent.call["message_history"]) == 2
    deps = agent.call["deps"]
    assert deps.user_id == USER_ID
    assert deps.thread_id == THREAD_ID


@pytest.mark.anyio
async def test_orchestrator_rejects_unresolved_company_without_agent_call() -> None:
    agent = FakeAgent()
    orchestrator = ChatOrchestrator(
        agent,  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        GroundingValidator(),
    )

    result = await orchestrator.answer(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        messages=[
            UIMessage(
                id="user-1",
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="What was the company's most important revenue change?",
                    )
                ],
            )
        ],
    )

    assert result.insufficient_evidence
    assert "specify which company" in result.answer
    assert agent.call == {}
