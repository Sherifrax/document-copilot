from datetime import date
from uuid import UUID

import pytest

from app.assistant.deps import EvidenceRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingError, GroundingValidator
from app.retrieval.models import SourcePassage

CHUNK_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_CHUNK_ID = UUID("00000000-0000-0000-0000-000000000002")


def passage() -> SourcePassage:
    return SourcePassage(
        chunk_id=CHUNK_ID,
        document_id=UUID("10000000-0000-0000-0000-000000000001"),
        chunk_index=4,
        content="Services net sales increased because of higher advertising revenue.",
        page_number=29,
        section="Item 7",
        token_count=10,
        metadata={},
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        filing_date=date(2025, 10, 31),
        report_date=date(2025, 9, 27),
        fiscal_year=2025,
        accession_number="0000320193-25-000079",
        source_url="https://www.sec.gov/example",
    )


def evidence() -> EvidenceRegistry:
    registry = EvidenceRegistry()
    registry.register(passage())
    return registry


def answer(**changes: object) -> GroundedAnswer:
    values = {
        "answer": "Services net sales increased. [1]",
        "citations": (
            Citation(
                index=1,
                chunk_id=CHUNK_ID,
                excerpt="Services net sales increased",
            ),
        ),
    }
    values.update(changes)
    return GroundedAnswer.model_validate(values)


def test_validates_retrieved_citation_and_excerpt() -> None:
    validated = GroundingValidator().validate(answer(), evidence())

    assert validated.answer == "Services net sales increased. [1]"
    assert validated.cited_passages[0].chunk_id == CHUNK_ID
    assert not validated.insufficient_evidence


def test_rejects_unretrieved_chunk() -> None:
    output = answer(
        citations=(
            Citation(index=1, chunk_id=OTHER_CHUNK_ID, excerpt="Services net sales"),
        )
    )

    with pytest.raises(GroundingError, match="unretrieved"):
        GroundingValidator().validate(output, evidence())


def test_replaces_excerpt_not_present_in_chunk_with_source_text() -> None:
    output = answer(
        citations=(Citation(index=1, chunk_id=CHUNK_ID, excerpt="invented fact"),)
    )

    validated = GroundingValidator().validate(output, evidence())

    assert validated.citations[0].excerpt == passage().content


def test_rejects_inline_marker_without_citation_record() -> None:
    output = answer(answer="Services net sales increased. [2]")

    with pytest.raises(GroundingError, match="reference citation records"):
        GroundingValidator().validate(output, evidence())


def test_accepts_explicit_insufficient_evidence_without_citations() -> None:
    output = GroundedAnswer(
        answer="The corpus does not contain enough evidence to answer this question.",
        insufficient_evidence=True,
    )

    validated = GroundingValidator().validate(output, EvidenceRegistry())

    assert validated.insufficient_evidence
    assert validated.citations == ()
    assert validated.cited_passages == ()


def test_rejects_insufficient_evidence_flag_without_clear_limitation() -> None:
    output = GroundedAnswer(
        answer="Generative AI improved margins.",
        insufficient_evidence=True,
    )

    with pytest.raises(GroundingError, match="clearly state"):
        GroundingValidator().validate(output, EvidenceRegistry())
