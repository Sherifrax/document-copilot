from sqlalchemy.dialects import postgresql

from app.retrieval.models import RetrievalFilters
from app.retrieval.queries import lexical_statement, semantic_statement


def compiled_sql(statement: object) -> str:
    return str(
        statement.compile(  # type: ignore[attr-defined]
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )


def test_semantic_statement_uses_cosine_distance_and_filters() -> None:
    statement = semantic_statement(
        [0.1, 0.2],
        RetrievalFilters(
            tickers=("aapl",),
            filing_types=("10-k",),
            fiscal_year_from=2021,
            fiscal_year_to=2025,
        ),
        50,
    )
    sql = compiled_sql(statement)

    assert "document_chunks.embedding <=>" in sql
    assert "ORDER BY distance" in sql
    assert "source_documents.ticker IN" in sql
    assert "source_documents.filing_type IN" in sql
    assert "source_documents.fiscal_year >=" in sql
    assert "source_documents.fiscal_year <=" in sql
    assert statement._limit_clause.value == 50


def test_lexical_statement_uses_generated_vector_and_cover_density_rank() -> None:
    statement = lexical_statement(
        "Apple revenue mix",
        RetrievalFilters(tickers=("AAPL",)),
        25,
    )
    sql = compiled_sql(statement)

    assert "websearch_to_tsquery" in sql
    assert "document_chunks.search_vector @@" in sql
    assert "ts_rank_cd" in sql
    assert "ORDER BY rank DESC" in sql
    assert statement._limit_clause.value == 25


def test_filters_normalize_values_and_validate_years() -> None:
    filters = RetrievalFilters(
        tickers=(" aapl ", "AAPL", "msft"),
        filing_types=("10-k",),
    )

    assert filters.tickers == ("AAPL", "MSFT")
    assert filters.filing_types == ("10-K",)
