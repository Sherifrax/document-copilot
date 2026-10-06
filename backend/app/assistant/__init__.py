"""PydanticAI document assistant contracts."""

from app.assistant.deps import DocumentAgentDeps, EvidenceRegistry
from app.assistant.outputs import Citation, GroundedAnswer, ValidatedGroundedAnswer

__all__ = [
    "Citation",
    "DocumentAgentDeps",
    "EvidenceRegistry",
    "GroundedAnswer",
    "ValidatedGroundedAnswer",
]
