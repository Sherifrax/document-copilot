import os

import pytest
from openai import AsyncOpenAI

from app.config import settings
from app.database.postgres import create_postgres_engine, create_session_factory
from app.retrieval.models import RetrievalFilters
from app.retrieval.retriever import DocumentRetriever


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.skipif(
    os.environ.get("RUN_RETRIEVAL_INTEGRATION") != "1",
    reason="set RUN_RETRIEVAL_INTEGRATION=1 to query the live corpus",
)
async def test_apple_revenue_mix_returns_citable_passages() -> None:
    engine = create_postgres_engine(settings.database_url)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    retriever = DocumentRetriever(
        create_session_factory(engine),
        openai_client,
        embedding_model=settings.openai_embedding_model,
        embedding_dimensions=settings.openai_embedding_dimensions,
    )
    try:
        hits = await retriever.search(
            "How did revenue mix between iPhone, Services, Mac, iPad, and "
            "Wearables change?",
            filters=RetrievalFilters(
                tickers=("AAPL",),
                filing_types=("10-K",),
                fiscal_year_from=2021,
                fiscal_year_to=2025,
            ),
        )
    finally:
        await openai_client.close()
        await engine.dispose()

    assert hits
    assert all(hit.passage.ticker == "AAPL" for hit in hits)
    assert all(2021 <= hit.passage.fiscal_year <= 2025 for hit in hits)
    assert all(hit.passage.source_url for hit in hits)
    assert any(
        "iphone" in hit.passage.content.lower()
        and "services" in hit.passage.content.lower()
        for hit in hits
    )
