"""Backward-compatibility aliases for legacy imports.

This module re-exports document entities from src.domain.documents to preserve
compatibility with imports from Stage A. New code should import directly from
src.domain or src.domain.documents.
"""

from src.domain.documents import (
    CanonicalDocument,
    GovernedChunk,
    ManifestRecord,
    VectorizedChunk,
)

__all__ = [
    "CanonicalDocument",
    "GovernedChunk",
    "ManifestRecord",
    "VectorizedChunk",
]
