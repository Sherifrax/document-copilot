"""Plan, pilot, and run Docling chunk ingestion for the SEC corpus."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from openai import OpenAI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DocumentChunk, SourceDocument
from ingest.chunking import PreparedChunk, prepare_chunks
from ingest.common import database_url, markdown_paths_by_accession

EMBEDDING_BATCH_SIZE = 64
PILOT_ACCESSION = "0000320193-24-000123"
PILOT_TEXT = "the following table shows net sales by category"


def source_documents(session: Session) -> list[SourceDocument]:
    return list(
        session.scalars(
            select(SourceDocument).order_by(
                SourceDocument.ticker, SourceDocument.fiscal_year
            )
        )
    )


def validate_embedding_response(
    response: Any,
    expected_count: int,
    expected_dimensions: int,
) -> list[list[float]]:
    ordered = sorted(response.data, key=lambda item: item.index)
    if len(ordered) != expected_count:
        raise ValueError(
            f"Expected {expected_count} embeddings, received {len(ordered)}"
        )

    embeddings = [item.embedding for item in ordered]
    if any(len(embedding) != expected_dimensions for embedding in embeddings):
        raise ValueError(
            f"Embedding response did not contain {expected_dimensions}-dimension vectors"
        )
    return embeddings


def existing_chunks(
    session: Session, document_id: object
) -> dict[int, DocumentChunk]:
    return {
        chunk.chunk_index: chunk
        for chunk in session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
    }


def missing_chunks(
    prepared: Sequence[PreparedChunk], existing: dict[int, DocumentChunk]
) -> list[PreparedChunk]:
    missing = []
    for chunk in prepared:
        stored = existing.get(chunk.chunk_index)
        if stored is None:
            missing.append(chunk)
            continue

        stored_hash = stored.chunk_metadata.get("content_sha256")
        expected_hash = chunk.metadata["content_sha256"]
        if stored_hash != expected_hash:
            raise ValueError(
                f"Chunk {chunk.document_id}/{chunk.chunk_index} was generated with "
                "different content; rebuild it explicitly before continuing"
            )
    return missing


def insert_batch(
    session: Session,
    client: OpenAI,
    chunks: Sequence[PreparedChunk],
) -> int:
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=[chunk.content for chunk in chunks],
        dimensions=settings.openai_embedding_dimensions,
        encoding_format="float",
    )
    embeddings = validate_embedding_response(
        response,
        expected_count=len(chunks),
        expected_dimensions=settings.openai_embedding_dimensions,
    )

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        session.add(
            DocumentChunk(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section=chunk.section,
                token_count=chunk.token_count,
                chunk_metadata={
                    **chunk.metadata,
                    "embedding_model": settings.openai_embedding_model,
                    "embedding_dimensions": settings.openai_embedding_dimensions,
                },
                embedding=embedding,
            )
        )
    session.commit()
    return response.usage.total_tokens


def prepare_document_chunks(document: SourceDocument) -> list[PreparedChunk]:
    paths = markdown_paths_by_accession()
    try:
        markdown_path = paths[document.accession_number]
    except KeyError as error:
        raise ValueError(
            f"No Markdown manifest entry for {document.accession_number}"
        ) from error
    return prepare_chunks(document, markdown_path)


def plan(session: Session) -> None:
    total_chunks = 0
    total_tokens = 0
    documents = source_documents(session)
    for document in documents:
        chunks = prepare_document_chunks(document)
        tokens = sum(chunk.token_count for chunk in chunks)
        total_chunks += len(chunks)
        total_tokens += tokens
        print(
            f"{document.ticker} {document.fiscal_year}: "
            f"{len(chunks)} chunks, {tokens} tokens"
        )

    print(
        f"Plan: {len(documents)} documents, {total_chunks} chunks, "
        f"{total_tokens} tokens; no API calls or writes"
    )


def pilot(session: Session, client: OpenAI) -> None:
    document = session.scalar(
        select(SourceDocument).where(
            SourceDocument.accession_number == PILOT_ACCESSION
        )
    )
    if document is None:
        raise ValueError(f"Pilot source document {PILOT_ACCESSION} is not in the database")

    chunks = prepare_document_chunks(document)
    selected = next(
        (chunk for chunk in chunks if PILOT_TEXT in chunk.content.lower()),
        None,
    )
    if selected is None:
        raise ValueError(f"Could not find the Apple revenue pilot passage: {PILOT_TEXT}")

    missing = missing_chunks([selected], existing_chunks(session, document.id))
    if not missing:
        print(f"Pilot chunk {selected.chunk_index} is already present; no API call made")
        return

    used_tokens = insert_batch(session, client, missing)
    print(
        f"Pilot inserted Apple chunk {selected.chunk_index}: "
        f"{selected.token_count} chunk tokens, {used_tokens} API tokens"
    )


def run(session: Session, client: OpenAI) -> None:
    inserted = 0
    skipped = 0
    api_tokens = 0

    for document in source_documents(session):
        prepared = prepare_document_chunks(document)
        missing = missing_chunks(prepared, existing_chunks(session, document.id))
        skipped += len(prepared) - len(missing)

        for start in range(0, len(missing), EMBEDDING_BATCH_SIZE):
            batch = missing[start : start + EMBEDDING_BATCH_SIZE]
            api_tokens += insert_batch(session, client, batch)
            inserted += len(batch)
            print(
                f"{document.ticker} {document.fiscal_year}: "
                f"inserted {inserted}, skipped {skipped} total"
            )

    print(
        f"Complete: inserted {inserted}, skipped {skipped}, "
        f"API tokens {api_tokens}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="Chunk and count locally without API calls or writes")
    commands.add_parser("pilot", help="Embed and insert one Apple revenue chunk")
    run_parser = commands.add_parser("run", help="Embed and insert all missing chunks")
    run_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the full paid embedding run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "run" and not args.confirm:
        raise SystemExit("The full run requires --confirm")

    engine = create_engine(database_url(settings.database_url))
    with Session(engine) as session:
        if args.command == "plan":
            plan(session)
        else:
            client = OpenAI(api_key=settings.openai_api_key)
            if args.command == "pilot":
                pilot(session, client)
            else:
                run(session, client)
    engine.dispose()


if __name__ == "__main__":
    main()
