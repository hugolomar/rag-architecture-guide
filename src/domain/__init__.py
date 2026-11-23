"""Public domain facade re-exporting all canonical models and enums."""

from src.domain.documents import (
    CanonicalDocument,
    ChunkId,
    DocId,
    GovernedChunk,
    ManifestRecord,
    VectorizedChunk,
)
from src.domain.enums import (
    BehaviorEnum,
    Classification,
    Department,
    IdPGroup,
    LifecycleStatus,
)
from src.domain.exceptions import (
    AuthenticationError,
    DomainError,
    GenerationProviderError,
    RetrievalProviderError,
    UpstreamProviderError,
)
from src.domain.queries import (
    CallerContext,
    Citation,
    GenerationResult,
    RetrievedChunk,
)

__all__ = [
    "AuthenticationError",
    "BehaviorEnum",
    "CallerContext",
    "CanonicalDocument",
    "ChunkId",
    "Citation",
    "Classification",
    "Department",
    "DocId",
    "DomainError",
    "GenerationProviderError",
    "GenerationResult",
    "GovernedChunk",
    "IdPGroup",
    "LifecycleStatus",
    "ManifestRecord",
    "RetrievalProviderError",
    "RetrievedChunk",
    "UpstreamProviderError",
    "VectorizedChunk",
]
