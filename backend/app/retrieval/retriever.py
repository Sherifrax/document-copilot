"""Query-to-passage orchestration for hybrid filing retrieval."""

import asyncio
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.retrieval.fusion import FusedCandidate, RankedCandidate, fuse_candidates
from app.retrieval.models import RetrievalFilters, SearchHit, SourcePassage
from app.retrieval.queries import (
    fetch_neighbor_passages,
    fetch_passages,
    lexical_candidates,
    semantic_candidates,
)


class ChunkNotFoundError(LookupError):
    """Raised when a requested corpus chunk does not exist."""


class DocumentRetriever:
    """Retrieve ranked SEC filing passages without depending on an LLM agent."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        openai_client: AsyncOpenAI,
        *,
        embedding_model: str,
        embedding_dimensions: int,
        candidate_limit: int = 50,
        rrf_k: int = 60,
    ) -> None:
        if candidate_limit <= 0 or rrf_k <= 0 or embedding_dimensions <= 0:
            raise ValueError("retrieval configuration values must be positive")
        self._session_factory = session_factory
        self._openai = openai_client
        self._embedding_model = embedding_model
        self._embedding_dimensions = embedding_dimensions
        self._candidate_limit = candidate_limit
        self._rrf_k = rrf_k

    async def _embed(self, query: str) -> list[float]:
        response = await self._openai.embeddings.create(
            input=query,
            model=self._embedding_model,
            dimensions=self._embedding_dimensions,
        )
        if len(response.data) != 1:
            raise ValueError("OpenAI returned an unexpected embedding count")
        embedding = response.data[0].embedding
        if len(embedding) != self._embedding_dimensions:
            raise ValueError(
                f"OpenAI returned {len(embedding)} dimensions; "
                f"expected {self._embedding_dimensions}"
            )
        return embedding

    async def _semantic(
        self, query: str, filters: RetrievalFilters
    ) -> list[RankedCandidate]:
        embedding = await self._embed(query)
        async with self._session_factory() as session:
            return await semantic_candidates(
                session, embedding, filters, self._candidate_limit
            )

    async def _lexical(
        self, query: str, filters: RetrievalFilters
    ) -> list[RankedCandidate]:
        async with self._session_factory() as session:
            return await lexical_candidates(
                session, query, filters, self._candidate_limit
            )

    async def _hydrate(
        self,
        candidates: list[FusedCandidate],
        neighbor_window: int,
    ) -> list[SearchHit]:
        async with self._session_factory() as session:
            passages = await fetch_passages(
                session, [candidate.chunk_id for candidate in candidates]
            )
            ordered_passages = [passages[candidate.chunk_id] for candidate in candidates]
            neighbors = await fetch_neighbor_passages(
                session,
                ordered_passages,
                before=neighbor_window,
                after=neighbor_window,
            )

        neighbors_by_document: dict[UUID, list[SourcePassage]] = {}
        for passage in neighbors:
            neighbors_by_document.setdefault(passage.document_id, []).append(passage)

        return [
            SearchHit(
                passage=passages[candidate.chunk_id],
                neighboring_passages=tuple(
                    passage
                    for passage in neighbors_by_document.get(
                        passages[candidate.chunk_id].document_id, []
                    )
                    if passage.chunk_id != candidate.chunk_id
                    and abs(
                        passage.chunk_index
                        - passages[candidate.chunk_id].chunk_index
                    )
                    <= neighbor_window
                ),
                rrf_score=candidate.rrf_score,
                semantic_rank=candidate.semantic_rank,
                lexical_rank=candidate.lexical_rank,
                semantic_score=candidate.semantic_score,
                lexical_score=candidate.lexical_score,
            )
            for candidate in candidates
        ]

    async def search(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        limit: int = 10,
        neighbor_window: int = 1,
    ) -> list[SearchHit]:
        """Embed, search both indexes, fuse results, and attach context."""
        query = query.strip()
        if not query:
            raise ValueError("query must not be blank")
        if limit <= 0:
            raise ValueError("limit must be positive")
        if neighbor_window < 0:
            raise ValueError("neighbor_window must be nonnegative")
        filters = filters or RetrievalFilters()

        semantic, lexical = await asyncio.gather(
            self._semantic(query, filters),
            self._lexical(query, filters),
        )
        fused = fuse_candidates(
            semantic,
            lexical,
            rrf_k=self._rrf_k,
            limit=limit,
        )
        if not fused:
            return []
        return await self._hydrate(fused, neighbor_window)

    async def read_chunk(self, chunk_id: UUID) -> SourcePassage:
        """Load one citable chunk by its stable identifier."""
        async with self._session_factory() as session:
            passages = await fetch_passages(session, [chunk_id])
        if chunk_id not in passages:
            raise ChunkNotFoundError(f"Chunk {chunk_id} was not found")
        return passages[chunk_id]

    async def read_surrounding_chunks(
        self,
        chunk_id: UUID,
        *,
        before: int = 1,
        after: int = 1,
    ) -> list[SourcePassage]:
        """Load a chunk and its ordered neighbors from the same filing."""
        if before < 0 or after < 0:
            raise ValueError("before and after must be nonnegative")
        passage = await self.read_chunk(chunk_id)
        async with self._session_factory() as session:
            return await fetch_neighbor_passages(
                session, [passage], before=before, after=after
            )
