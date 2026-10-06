"""Reciprocal Rank Fusion for semantic and lexical candidates."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RankedCandidate:
    chunk_id: UUID
    score: float


@dataclass(frozen=True)
class FusedCandidate:
    chunk_id: UUID
    rrf_score: float
    semantic_rank: int | None
    lexical_rank: int | None
    semantic_score: float | None
    lexical_score: float | None


def fuse_candidates(
    semantic: list[RankedCandidate],
    lexical: list[RankedCandidate],
    *,
    rrf_k: int = 60,
    limit: int | None = None,
) -> list[FusedCandidate]:
    """Fuse ranked candidates without mixing incomparable raw scores."""
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")

    records: dict[UUID, dict[str, int | float | None]] = {}
    for branch, candidates in (("semantic", semantic), ("lexical", lexical)):
        seen: set[UUID] = set()
        for rank, candidate in enumerate(candidates, start=1):
            if candidate.chunk_id in seen:
                continue
            seen.add(candidate.chunk_id)
            record = records.setdefault(
                candidate.chunk_id,
                {
                    "rrf_score": 0.0,
                    "semantic_rank": None,
                    "lexical_rank": None,
                    "semantic_score": None,
                    "lexical_score": None,
                },
            )
            record["rrf_score"] = float(record["rrf_score"]) + 1 / (rrf_k + rank)
            record[f"{branch}_rank"] = rank
            record[f"{branch}_score"] = candidate.score

    fused = [
        FusedCandidate(chunk_id=chunk_id, **record)  # type: ignore[arg-type]
        for chunk_id, record in records.items()
    ]
    fused.sort(
        key=lambda candidate: (
            -candidate.rrf_score,
            min(
                rank
                for rank in (candidate.semantic_rank, candidate.lexical_rank)
                if rank is not None
            ),
            str(candidate.chunk_id),
        )
    )
    return fused[:limit]
