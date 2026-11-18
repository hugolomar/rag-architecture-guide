"""Behavioral port definition for chunk storage writers.

Abstract port specifying collection initialization and point upsert operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.domain.models import VectorizedChunk


class ChunkStorageWriterPort(ABC):
    """Abstract behavioral port for indexing governed vectorized chunks.

    Architectural Pattern:
        Acts as the write-side Repository port (under Ports & Adapters / DDD)
        abstracting retrieval and vector stores (e.g., Qdrant) from ingestion orchestration.
        Following CQRS (Command Query Responsibility Segregation), this port is
        strictly write-only; read-side similarity search and evidence retrieval are
        segregated into a dedicated retriever port.

    Outbound storage adapters implement this port to persist dual-vector
    points with governance metadata into retrieval stores such as Qdrant.
    """

    @abstractmethod
    def ensure_collection(self, collection_name: str) -> None:
        """Create or verify the existence of the target collection.

        Args:
            collection_name: Unique identifier of the vector collection.

        Raises:
            NotImplementedError: If not implemented by the adapter.
        """
        raise NotImplementedError

    @abstractmethod
    def upsert_chunks(self, collection_name: str, chunks: Sequence[VectorizedChunk]) -> int:
        """Persist a batch of vectorized chunks into the collection.

        Args:
            collection_name: Target collection name.
            chunks: Sequence of VectorizedChunk instances to index.

        Returns:
            Number of points successfully persisted.

        Raises:
            NotImplementedError: If not implemented by the adapter.
        """
        raise NotImplementedError
