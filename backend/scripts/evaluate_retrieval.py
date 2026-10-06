"""Print top passages for the client-brief retrieval questions."""

import asyncio
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import settings
from app.database.postgres import create_postgres_engine, create_session_factory
from app.retrieval.models import RetrievalFilters
from app.retrieval.retriever import DocumentRetriever


@dataclass(frozen=True)
class EvaluationQuery:
    label: str
    query: str
    filters: RetrievalFilters


YEAR_RANGE = {"fiscal_year_from": 2021, "fiscal_year_to": 2025}
QUESTIONS = (
    EvaluationQuery(
        "Apple revenue mix",
        "revenue mix iPhone Services Mac iPad Wearables net sales",
        RetrievalFilters(tickers=("AAPL",), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "Amazon segment profitability",
        "AWS North America International operating income operating margin",
        RetrievalFilters(tickers=("AMZN",), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "NVIDIA Data Center",
        "Data Center demand drivers customer concentration supply constraints",
        RetrievalFilters(tickers=("NVDA",), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "Microsoft cloud capacity",
        "Azure AI infrastructure cloud capacity constraints",
        RetrievalFilters(tickers=("MSFT",), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "Alphabet revenue trends",
        "Google Search YouTube ads Network subscriptions devices Cloud revenue",
        RetrievalFilters(tickers=("GOOGL",), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "Cross-company risk factors",
        "risk factors AI cloud infrastructure export controls supply chain regulation",
        RetrievalFilters(**YEAR_RANGE),
    ),
    EvaluationQuery(
        "Supplier concentration",
        "supplier concentration third-party manufacturing dependence",
        RetrievalFilters(tickers=("AAPL", "NVDA"), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "Infrastructure investment",
        "capital expenditures purchase commitments AI cloud infrastructure investment",
        RetrievalFilters(tickers=("MSFT", "GOOGL", "AMZN", "NVDA"), **YEAR_RANGE),
    ),
    EvaluationQuery(
        "Geographic exposure",
        "geographic revenue exposure by country region",
        RetrievalFilters(**YEAR_RANGE),
    ),
    EvaluationQuery(
        "Generative AI margins",
        "generative AI impact on margins profitability evidence",
        RetrievalFilters(**YEAR_RANGE),
    ),
)


async def main() -> None:
    engine = create_postgres_engine(settings.database_url)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    retriever = DocumentRetriever(
        create_session_factory(engine),
        openai_client,
        embedding_model=settings.openai_embedding_model,
        embedding_dimensions=settings.openai_embedding_dimensions,
    )
    try:
        for evaluation in QUESTIONS:
            hits = await retriever.search(
                evaluation.query,
                filters=evaluation.filters,
                limit=5,
            )
            print(f"\n## {evaluation.label}")
            for rank, hit in enumerate(hits, start=1):
                passage = hit.passage
                location = f"page {passage.page_number}" if passage.page_number else passage.section
                preview = " ".join(passage.content.split())[:240]
                print(
                    f"{rank}. {passage.ticker} {passage.fiscal_year} "
                    f"{passage.filing_type} | {location} | "
                    f"RRF {hit.rrf_score:.6f}\n   {preview}"
                )
    finally:
        await openai_client.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
