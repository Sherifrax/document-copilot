"""Fail-closed validation for model-produced answers and citations."""

import re

from app.assistant.deps import EvidenceRegistry
from app.assistant.outputs import Citation, GroundedAnswer, ValidatedGroundedAnswer

CITATION_MARKER = re.compile(r"\[(\d+)\]")


class GroundingError(ValueError):
    """Raised when an answer cites evidence it did not retrieve or support."""


def normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def source_excerpt(content: str, limit: int = 500) -> str:
    """Create a bounded excerpt that is guaranteed to come from the chunk."""
    return content[:limit].strip()


class GroundingValidator:
    """Validate citation identity, excerpts, and inline citation coverage."""

    def validate(
        self, output: GroundedAnswer, evidence: EvidenceRegistry
    ) -> ValidatedGroundedAnswer:
        if output.insufficient_evidence:
            normalized_answer = normalize_text(output.answer)
            if not any(
                phrase in normalized_answer
                for phrase in (
                    "not enough evidence",
                    "insufficient evidence",
                    "does not contain enough evidence",
                )
            ):
                raise GroundingError(
                    "An insufficient-evidence answer must clearly state the limitation"
                )
            return ValidatedGroundedAnswer(
                answer=output.answer.strip(),
                citations=(),
                cited_passages=(),
                insufficient_evidence=True,
            )
        if not output.citations:
            raise GroundingError("A grounded answer must include citations")

        expected_indices = list(range(1, len(output.citations) + 1))
        actual_indices = [citation.index for citation in output.citations]
        if actual_indices != expected_indices:
            raise GroundingError("Citation indices must be unique and sequential")

        markers = [int(index) for index in CITATION_MARKER.findall(output.answer)]
        if not set(markers).issubset(expected_indices):
            raise GroundingError("Inline citation markers must reference citation records")

        cited_passages = []
        validated_citations = []
        for citation in output.citations:
            passage = evidence.passages.get(citation.chunk_id)
            if passage is None:
                raise GroundingError(
                    f"Citation {citation.index} references an unretrieved chunk"
                )
            excerpt = citation.excerpt
            if normalize_text(excerpt) not in normalize_text(passage.content):
                excerpt = source_excerpt(passage.content)
            validated_citations.append(
                Citation(
                    index=citation.index,
                    chunk_id=citation.chunk_id,
                    excerpt=excerpt,
                )
            )
            cited_passages.append(passage)

        return ValidatedGroundedAnswer(
            answer=output.answer.strip(),
            citations=tuple(validated_citations),
            cited_passages=tuple(cited_passages),
            insufficient_evidence=False,
        )
