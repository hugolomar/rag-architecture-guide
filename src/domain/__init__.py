"""Public domain facade re-exporting all canonical models and enums."""

from src.domain.documents import (
    CanonicalDocument,
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
from src.domain.queries import (
    CallerContext,
    Citation,
    GenerationResult,
    RetrievedChunk,
)

__all__ = [
    "BehaviorEnum",
    "CallerContext",
    "CanonicalDocument",
    "Citation",
    "Classification",
    "Department",
    "GenerationResult",
    "GovernedChunk",
    "IdPGroup",
    "LifecycleStatus",
    "ManifestRecord",
    "RetrievedChunk",
    "VectorizedChunk",
]
