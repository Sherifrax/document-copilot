"""Turn normalized SEC Markdown into retrieval-ready Docling chunks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import UUID

import tiktoken
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

from app.database.models import SourceDocument

MAX_CHUNK_TOKENS = 512
HEADING_TOKEN_RESERVE = 32
PIPELINE_VERSION = 1
SEC_ITEM_HEADING = re.compile(
    r"^Item\s+(?:1|1A|1B|1C|2|3|4|5|6|7|7A|8|9|9A|9B|9C|10|11|12|13|14|15|16)"
    r"\.?(?:\s+.+)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PreparedChunk:
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int | None
    section: str | None
    token_count: int
    metadata: dict[str, Any]


def normalize_sec_headings(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#") and SEC_ITEM_HEADING.fullmatch(stripped):
            lines.append(f"## {stripped}")
        else:
            lines.append(line)
    return "\n".join(lines)


def openai_tokenizer(max_tokens: int = MAX_CHUNK_TOKENS) -> OpenAITokenizer:
    return OpenAITokenizer(
        tokenizer=tiktoken.get_encoding("cl100k_base"),
        max_tokens=max_tokens,
    )


def split_oversized_chunk(
    content: str,
    headings: list[str],
    max_tokens: int,
) -> list[str]:
    encoding = tiktoken.get_encoding("cl100k_base")
    if len(encoding.encode(content)) <= max_tokens:
        return [content]

    heading_prefix = "\n".join(headings)
    body = content
    if heading_prefix and content.startswith(heading_prefix):
        body = content[len(heading_prefix) :].lstrip("\n")
        prefix_tokens = encoding.encode(f"{heading_prefix}\n")
    else:
        prefix_tokens = []

    available_tokens = max_tokens - len(prefix_tokens)
    if available_tokens <= 0:
        raise ValueError("Section headings exceed the chunk token limit")

    body_tokens = encoding.encode(body)
    return [
        encoding.decode(prefix_tokens + body_tokens[start : start + available_tokens])
        for start in range(0, len(body_tokens), available_tokens)
    ]


def prepare_chunks(
    document: SourceDocument,
    markdown_path: Path,
    *,
    max_tokens: int = MAX_CHUNK_TOKENS,
) -> list[PreparedChunk]:
    markdown = normalize_sec_headings(markdown_path.read_text(encoding="utf-8"))
    dl_doc = DocumentConverter().convert_string(
        markdown,
        format=InputFormat.MD,
        name=markdown_path.name,
    ).document
    chunk_target_tokens = max_tokens - HEADING_TOKEN_RESERVE
    if chunk_target_tokens <= 0:
        raise ValueError("max_tokens must exceed the heading token reserve")
    tokenizer = openai_tokenizer(chunk_target_tokens)
    chunker = HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,
        repeat_table_header=True,
    )

    prepared = []
    for source_chunk_index, chunk in enumerate(chunker.chunk(dl_doc)):
        content = chunker.contextualize(chunk).strip()
        if not content:
            raise ValueError(
                f"Docling produced an empty chunk at index {source_chunk_index}"
            )

        serialized_meta = chunk.meta.model_dump(mode="json")
        headings = list(chunk.meta.headings or [])
        captions = list(serialized_meta.get("captions") or [])
        pages = [
            provenance.page_no
            for item in chunk.meta.doc_items
            for provenance in item.prov
        ]
        content_parts = split_oversized_chunk(content, headings, max_tokens)
        for split_part, part_content in enumerate(content_parts):
            prepared.append(
                PreparedChunk(
                    document_id=document.id,
                    chunk_index=len(prepared),
                    content=part_content,
                    page_number=min(pages) if pages else None,
                    section=headings[-1] if headings else None,
                    token_count=tokenizer.count_tokens(part_content),
                    metadata={
                        "ticker": document.ticker,
                        "company_name": document.company_name,
                        "filing_type": document.filing_type,
                        "filing_date": document.filing_date.isoformat(),
                        "fiscal_year": document.fiscal_year,
                        "accession_number": document.accession_number,
                        "headings": headings,
                        "captions": captions,
                        "doc_items": [
                            {"ref": item.self_ref, "label": item.label.value}
                            for item in chunk.meta.doc_items
                        ],
                        "source_docling_chunk_index": source_chunk_index,
                        "split_part": split_part,
                        "split_parts": len(content_parts),
                        "content_sha256": hashlib.sha256(
                            part_content.encode()
                        ).hexdigest(),
                        "pipeline_version": PIPELINE_VERSION,
                        "chunker": "docling.HybridChunker",
                        "docling_version": version("docling"),
                        "max_tokens": max_tokens,
                        "chunk_target_tokens": chunk_target_tokens,
                        "overlap_tokens": 0,
                    },
                )
            )

    return prepared
