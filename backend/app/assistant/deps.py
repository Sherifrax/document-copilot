"""Request-scoped dependencies supplied to the document agent."""

from dataclasses import dataclass, field
from uuid import UUID

from app.retrieval.models import SearchHit, SourcePassage
from app.retrieval.retriever import DocumentRetriever


@dataclass
class EvidenceRegistry:
    """Passages the current agent run is allowed to cite."""

    passages: dict[UUID, SourcePassage] = field(default_factory=dict)
    search_calls: int = 0
    inspection_calls: int = 0

    def register(self, passage: SourcePassage) -> None:
        self.passages[passage.chunk_id] = passage

    def register_hit(self, hit: SearchHit) -> None:
        self.register(hit.passage)
        for passage in hit.neighboring_passages:
            self.register(passage)

    def register_hits(self, hits: list[SearchHit]) -> None:
        for hit in hits:
            self.register_hit(hit)


@dataclass
class DocumentAgentDeps:
    user_id: UUID
    thread_id: UUID
    retriever: DocumentRetriever
    evidence: EvidenceRegistry = field(default_factory=EvidenceRegistry)
