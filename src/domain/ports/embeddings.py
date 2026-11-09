"""Behavioral port definition for embedding and vectorization adapters.

In accordance with Constitution Article 4, all cross-boundary contracts
must inherit from abc.ABC and declare abstract methods.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.domain.models import GovernedChunk, VectorizedChunk


class EmbedderPort(ABC):
    """Abstract behavioral port for generating dual vector representations.

    Implementations provide semantic dense embeddings and exact written-token
    sparse lexical vectors without leaking third-party SDK dependencies into
    the domain core.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of dense vectors produced by this embedder.

        Returns:
            Integer vector dimensionality matching the active model output.

        Raises:
            NotImplementedError: If not implemented by the adapter.
        """
        raise NotImplementedError

    @abstractmethod
    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        """Generate dense semantic vectors for a batch of texts.

        Args:
            texts: List of input strings to embed.

        Returns:
            List of dense float vectors matching input order.

        Raises:
            NotImplementedError: If not implemented by the adapter.
        """
        raise NotImplementedError

    @abstractmethod
    def embed_sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        """Generate sparse BM25 token indices and weights for a batch of texts.

        Args:
            texts: List of input strings to vectorize.

        Returns:
            List of tuples (indices, values) representing BM25 token weights.

        Raises:
            NotImplementedError: If not implemented by the adapter.
        """
        raise NotImplementedError

    @abstractmethod
    def vectorize_chunks(self, chunks: Sequence[GovernedChunk]) -> list[VectorizedChunk]:
        """Convert governed text chunks into enriched VectorizedChunk instances.

        Args:
            chunks: Sequence of GovernedChunk models to vectorize.

        Returns:
            List of VectorizedChunk instances with dense and sparse representations.

        Raises:
            NotImplementedError: If not implemented by the adapter.
        """
        raise NotImplementedError

