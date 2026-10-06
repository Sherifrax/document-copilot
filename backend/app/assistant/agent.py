"""PydanticAI document-agent construction and output validation."""

from pathlib import Path
from typing import cast

from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIChatModelSettings,
    OpenAIModelName,
)
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import UsageLimits

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.assistant.tools import read_chunk, read_surrounding_chunks, search_filings
from app.grounding.validator import GroundingError, GroundingValidator

INSTRUCTIONS = (Path(__file__).with_name("instructions.md")).read_text(encoding="utf-8")
DOCUMENT_AGENT_USAGE_LIMITS = UsageLimits(
    request_limit=7,
    tool_calls_limit=6,
    input_tokens_limit=80_000,
    output_tokens_limit=4_000,
)


def prepare_search_tool(
    ctx: RunContext[DocumentAgentDeps], definition: ToolDefinition
) -> ToolDefinition | None:
    """Stop repeated retrieval once the agent has citable evidence."""
    return None if ctx.deps.evidence.passages else definition


def prepare_inspection_tool(
    ctx: RunContext[DocumentAgentDeps], definition: ToolDefinition
) -> ToolDefinition | None:
    """Reserve inspection tools for future controlled workflows."""
    return None


def create_document_agent(model_name: str, api_key: str) -> Agent[DocumentAgentDeps, GroundedAnswer]:
    """Create the production agent without relying on SDK environment reads."""
    model = OpenAIChatModel(
        cast(OpenAIModelName, model_name),
        provider=OpenAIProvider(api_key=api_key),
    )
    model_settings = OpenAIChatModelSettings(
        max_tokens=2_000,
        parallel_tool_calls=True,
    )
    if model_name.startswith("gpt-5"):
        model_settings["openai_reasoning_effort"] = "minimal"

    agent = Agent(
        model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=INSTRUCTIONS,
        model_settings=model_settings,
        retries=1,
        tools=(
            Tool(search_filings, prepare=prepare_search_tool),
            Tool(read_chunk, prepare=prepare_inspection_tool),
            Tool(read_surrounding_chunks, prepare=prepare_inspection_tool),
        ),
    )

    @agent.output_validator
    def validate_grounded_output(
        ctx: RunContext[DocumentAgentDeps], output: GroundedAnswer
    ) -> GroundedAnswer:
        try:
            GroundingValidator().validate(output, ctx.deps.evidence)
        except GroundingError as error:
            raise ModelRetry(str(error)) from error
        return output

    return agent
