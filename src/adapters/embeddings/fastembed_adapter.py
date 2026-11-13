"""FastEmbed vectorization adapter implementing EmbedderPort.

In accordance with Constitution Article 14 and ADR 0005, generates dual representations:
- Dense: BAAI/bge-large-en-v1.5 (1024 dimensions, ONNX runtime)
- Sparse: Qdrant/bm25 (lexical token weights)
"""

from collections.abc import Sequence

from fastembed import SparseTextEmbedding, TextEmbedding

from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.embeddings import EmbedderPort


class FastEmbedAdapter(EmbedderPort):
    """Adapter for generating dense and sparse embeddings via FastEmbed."""

    def __init__(
        self,
        dense_model_name: str = "BAAI/bge-large-en-v1.5",
        sparse_model_name: str = "Qdrant/bm25",
        dimension: int = 1024,
    ) -> None:
        """Initialize the FastEmbed models with lazy loading.

        Args:
            dense_model_name: HuggingFace identifier for dense ONNX embedding model.
            sparse_model_name: Identifier for sparse BM25 model.
            dimension: Dimensionality of dense vectors produced by the configured model.
        """
        self.dense_model_name = dense_model_name
        self.sparse_model_name = sparse_model_name
        self._dimension = dimension
        self._dense_model: TextEmbedding | None = None
        self._sparse_model: SparseTextEmbedding | None = None

    @property
    def dimension(self) -> int:
        """Dimensionality of dense vectors produced by the active dense model."""
        return self._dimension

    @property
    def dense_model(self) -> TextEmbedding:
        """Lazily initialize the dense ONNX model."""
        if self._dense_model is None:
            self._dense_model = TextEmbedding(model_name=self.dense_model_name)
        return self._dense_model

    @property
    def sparse_model(self) -> SparseTextEmbedding:
        """Lazily initialize the sparse BM25 model."""
        if self._sparse_model is None:
            self._sparse_model = SparseTextEmbedding(model_name=self.sparse_model_name)
        return self._sparse_model

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        """Generate 1024-dimensional dense semantic vectors.

        Args:
            texts: List of strings to embed.

        Returns:
            List of float vectors.
        """
        if not texts:
            return []
        embeddings = list(self.dense_model.embed(texts))
        return [emb.tolist() for emb in embeddings]

    def embed_sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        """Generate sparse BM25 token indices and weights.

        Args:
            texts: List of strings to vectorize.

        Returns:
            List of tuples (indices, values).
        """
        if not texts:
            return []
        sparse_embeddings = list(self.sparse_model.embed(texts))
        results: list[tuple[list[int], list[float]]] = []
        for emb in sparse_embeddings:
            results.append((emb.indices.tolist(), emb.values.tolist()))
        return results

    def vectorize_chunks(self, chunks: Sequence[GovernedChunk]) -> list[VectorizedChunk]:
        """Convert governed text chunks into enriched VectorizedChunk instances.

        Args:
            chunks: Sequence of GovernedChunk models to vectorize.

        Returns:
            List of VectorizedChunk instances with dense and sparse representations.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        dense_vectors = self.embed_dense(texts)
        sparse_vectors = self.embed_sparse(texts)

        vectorized: list[VectorizedChunk] = []
        for chunk, dense, (sparse_idx, sparse_val) in zip(chunks, dense_vectors, sparse_vectors):
            vectorized.append(
                VectorizedChunk(
                    chunk=chunk,
                    dense_vector=dense,
                    sparse_indices=sparse_idx,
                    sparse_values=sparse_val,
                )
            )

        return vectorized

