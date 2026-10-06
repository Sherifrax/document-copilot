"""Load the normalized filing corpus into the source_documents table."""

from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import SourceDocument
from ingest.common import (
    COMPANY_NAMES,
    CORPUS_DIR,
    database_url,
    load_manifest,
)


def load_documents() -> list[SourceDocument]:
    manifest = load_manifest()
    documents = []

    for filing in manifest["filings"]:
        markdown_path = CORPUS_DIR / filing["local_path"]
        report_date = date.fromisoformat(filing["report_date"])
        documents.append(
            SourceDocument(
                ticker=filing["ticker"],
                company_name=COMPANY_NAMES[filing["ticker"]],
                cik=filing["cik"],
                filing_type=filing["form"],
                filing_date=date.fromisoformat(filing["filing_date"]),
                report_date=report_date,
                fiscal_year=report_date.year,
                accession_number=filing["accession_number"],
                source_url=filing["source_url"],
                markdown_content=markdown_path.read_text(encoding="utf-8"),
            )
        )

    return documents


def ingest_documents() -> tuple[int, int]:
    documents = load_documents()
    engine = create_engine(database_url(settings.database_url))

    with Session(engine) as session, session.begin():
        accession_numbers = [document.accession_number for document in documents]
        existing = set(
            session.scalars(
                select(SourceDocument.accession_number).where(
                    SourceDocument.accession_number.in_(accession_numbers)
                )
            )
        )
        new_documents = [
            document
            for document in documents
            if document.accession_number not in existing
        ]
        session.add_all(new_documents)

    engine.dispose()
    return len(new_documents), len(existing)


def main() -> None:
    inserted_count, skipped_count = ingest_documents()
    print(
        f"Inserted {inserted_count} source documents; "
        f"skipped {skipped_count} already present"
    )


if __name__ == "__main__":
    main()
