"""Run one document-agent turn and return only validated output."""

from uuid import UUID

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
)
from pydantic_ai.messages import TextPart as ModelTextPart

from app.assistant.agent import DOCUMENT_AGENT_USAGE_LIMITS
from app.assistant.deps import DocumentAgentDeps, EvidenceRegistry
from app.assistant.outputs import GroundedAnswer, ValidatedGroundedAnswer
from app.chat.messages import UIMessage, user_message_content
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import DocumentRetriever

CORPUS_COMPANY_TERMS = (
    "aapl",
    "apple",
    "amzn",
    "amazon",
    "googl",
    "alphabet",
    "google",
    "msft",
    "microsoft",
    "nvda",
    "nvidia",
    "these companies",
    "the five companies",
    "each company",
)


def lacks_company_scope(question: str, history: list[UIMessage]) -> bool:
    """Identify an unresolved singular company reference before any paid call."""
    if "the company" not in question.casefold():
        return False
    available_context = " ".join(
        [question, *(user_message_content(message) for message in history)]
    ).casefold()
    return not any(term in available_context for term in CORPUS_COMPANY_TERMS)


def model_message_history(messages: list[UIMessage]) -> list[ModelMessage]:
    """Convert persisted UI text messages into PydanticAI history."""
    history: list[ModelMessage] = []
    for message in messages:
        content = user_message_content(message)
        if not content:
            continue
        if message.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content)]))
        elif message.role == "assistant":
            history.append(ModelResponse(parts=[ModelTextPart(content)]))
    return history


class ChatOrchestrator:
    """Coordinate the agent, retrieval evidence, and grounding validator."""

    def __init__(
        self,
        agent: Agent[DocumentAgentDeps, GroundedAnswer],
        retriever: DocumentRetriever,
        grounding_validator: GroundingValidator,
    ) -> None:
        self._agent = agent
        self._retriever = retriever
        self._grounding_validator = grounding_validator

    async def answer(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        messages: list[UIMessage],
    ) -> ValidatedGroundedAnswer:
        current_message = messages[-1]
        current_question = user_message_content(current_message)
        if lacks_company_scope(current_question, messages[:-1]):
            return self._grounding_validator.validate(
                GroundedAnswer(
                    answer=(
                        "There is not enough evidence to answer until you specify "
                        "which company you mean."
                    ),
                    insufficient_evidence=True,
                ),
                EvidenceRegistry(),
            )
        deps = DocumentAgentDeps(
            user_id=user_id,
            thread_id=thread_id,
            retriever=self._retriever,
        )
        result = await self._agent.run(
            current_question,
            message_history=model_message_history(messages[:-1]),
            deps=deps,
            usage_limits=DOCUMENT_AGENT_USAGE_LIMITS,
        )
        return self._grounding_validator.validate(result.output, deps.evidence)
