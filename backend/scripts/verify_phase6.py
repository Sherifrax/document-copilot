"""Run the three live acceptance checks required to finish Phase 6."""

import asyncio
from argparse import ArgumentParser
from uuid import UUID

from openai import AsyncOpenAI

from app.assistant.agent import create_document_agent
from app.chat.messages import TextPart, UIMessage
from app.chat.orchestrator import ChatOrchestrator
from app.config import settings
from app.database.postgres import create_postgres_engine, create_session_factory
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import DocumentRetriever

CASES = (
    (
        "cited-answer",
        (
            "Across Apple's 2021–2025 10-Ks, how did the revenue mix between "
            "iPhone, Services, Mac, iPad, and Wearables change?"
        ),
    ),
    (
        "under-specified",
        "What was the company's most important revenue change?",
    ),
    (
        "ai-margin-boundary",
        (
            "Do the filings prove that generative AI improved margins for any of "
            "these companies? State what evidence exists and do not infer beyond "
            "the filings."
        ),
    ),
)


async def main(case_label: str) -> None:
    engine = create_postgres_engine(settings.database_url)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    retriever = DocumentRetriever(
        create_session_factory(engine),
        openai_client,
        embedding_model=settings.openai_embedding_model,
        embedding_dimensions=settings.openai_embedding_dimensions,
    )
    orchestrator = ChatOrchestrator(
        create_document_agent(settings.openai_chat_model, settings.openai_api_key),
        retriever,
        GroundingValidator(),
    )
    try:
        selected_cases = [case for case in CASES if case[0] == case_label]
        for index, (label, question) in enumerate(selected_cases, start=1):
            result = await orchestrator.answer(
                user_id=UUID(int=index),
                thread_id=UUID(int=index + 10),
                messages=[
                    UIMessage(
                        id=f"verification-{index}",
                        role="user",
                        parts=[TextPart(type="text", text=question)],
                    )
                ],
            )
            print(f"\n## {label}")
            print(f"insufficient_evidence={result.insufficient_evidence}")
            print(result.answer)
            for citation, passage in zip(
                result.citations, result.cited_passages, strict=True
            ):
                print(
                    f"[{citation.index}] {passage.ticker} {passage.fiscal_year} "
                    f"{passage.filing_type} | page={passage.page_number} | "
                    f"section={passage.section} | accession={passage.accession_number}"
                )
    finally:
        await openai_client.close()
        await engine.dispose()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("case", choices=[case[0] for case in CASES])
    arguments = parser.parse_args()
    asyncio.run(main(arguments.case))
