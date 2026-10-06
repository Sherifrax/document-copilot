from uuid import UUID

import pytest

from app.retrieval.fusion import RankedCandidate, fuse_candidates

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
C = UUID("00000000-0000-0000-0000-000000000003")


def candidate(chunk_id: UUID, score: float) -> RankedCandidate:
    return RankedCandidate(chunk_id=chunk_id, score=score)


def test_fusion_rewards_candidates_present_in_both_lists() -> None:
    fused = fuse_candidates(
        [candidate(A, 0.9), candidate(B, 0.8)],
        [candidate(B, 12.0), candidate(C, 8.0)],
    )

    assert [item.chunk_id for item in fused] == [B, A, C]
    assert fused[0].rrf_score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[0].semantic_rank == 2
    assert fused[0].lexical_rank == 1
    assert fused[0].semantic_score == 0.8
    assert fused[0].lexical_score == 12.0


def test_fusion_uses_stable_tie_breaking_and_limit() -> None:
    fused = fuse_candidates(
        [candidate(B, 0.7)],
        [candidate(A, 4.0)],
        limit=1,
    )

    assert [item.chunk_id for item in fused] == [A]


def test_fusion_ignores_duplicate_ids_within_one_branch() -> None:
    fused = fuse_candidates(
        [candidate(A, 0.9), candidate(A, 0.1)],
        [],
    )

    assert len(fused) == 1
    assert fused[0].rrf_score == pytest.approx(1 / 61)
    assert fused[0].semantic_rank == 1
    assert fused[0].semantic_score == 0.9


def test_fusion_accepts_one_empty_branch() -> None:
    fused = fuse_candidates([], [candidate(C, 2.0)])

    assert [item.chunk_id for item in fused] == [C]
    assert fused[0].semantic_rank is None
    assert fused[0].lexical_rank == 1


@pytest.mark.parametrize(
    ("rrf_k", "limit"),
    [(0, None), (-1, None), (60, 0), (60, -1)],
)
def test_fusion_rejects_nonpositive_configuration(
    rrf_k: int, limit: int | None
) -> None:
    with pytest.raises(ValueError):
        fuse_candidates([], [], rrf_k=rrf_k, limit=limit)
