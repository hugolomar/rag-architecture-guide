"""Qdrant hybrid retrieval adapter implementing RetrievalPort.

Performs reciprocal rank fusion (RRF) between dense and sparse vector representations
while strictly enforcing deterministic pre-inference security trimming (allowed_groups
intersection) and lifecycle filtering (excluding archived documents).
"""

from typing import Any

from qdrant_client import QdrantClient, models

from src.domain.exceptions import RetrievalProviderError
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.retrieval import RetrievalPort
from src.domain.queries import RetrievedChunk


class QdrantRetrievalAdapter(RetrievalPort):
    """Retrieval adapter executing security-trimmed hybrid search in Qdrant."""

    def __init__(
        self,
        client: QdrantClient,
        embedder: EmbedderPort,
        collection_name: str,
    ) -> None:
        """Initialize the retrieval adapter.

        Args:
            client: Connected QdrantClient instance.
            embedder: Embedding provider conforming to EmbedderPort.
            collection_name: Target collection storing governed chunks.
        """
        self.client = client
        self.embedder = embedder
        self.collection_name = collection_name

    def retrieve(
        self,
        query: str,
        caller_groups: set[str],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        """Retrieve authorized candidate chunks using dense + sparse hybrid search.

        Enforces pre-inference security trimming (allowed_groups and status != archived).

        Args:
            query: Natural language query string.
            caller_groups: Set of verified caller group claims.
            top_k: Maximum number of candidate chunks to return.

        Returns:
            List of authorized RetrievedChunk objects ordered by relevance.
        """
        if not caller_groups:
            return []

        try:
            # Vectorize query using dual dense and sparse channels
            dense_vectors = self.embedder.embed_dense([query])
            dense_vector = dense_vectors[0]
            sparse_batch = self.embedder.embed_sparse([query])
            sparse_indices, sparse_values = sparse_batch[0]

            # Construct deterministic pre-inference security trimming filter
            filter_clause = models.Filter(
                must=[
                    models.FieldCondition(
                        key="allowed_groups",
                        match=models.MatchAny(any=list(caller_groups)),
                    )
                ],
                must_not=[
                    models.FieldCondition(
                        key="status",
                        match=models.MatchValue(value="archived"),
                    )
                ],
            )

            # Build hybrid prefetch queries
            prefetch: list[models.Prefetch] = [
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    filter=filter_clause,
                    limit=top_k * 2,
                )
            ]

            if sparse_indices:
                prefetch.append(
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_indices,
                            values=sparse_values,
                        ),
                        using="sparse",
                        filter=filter_clause,
                        limit=top_k * 2,
                    )
                )

            query_response = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
            )
        except Exception as exc:
            raise RetrievalProviderError(f"Qdrant retrieval query failed: {exc}") from exc

        retrieved: list[RetrievedChunk] = []
        for point in query_response.points:
            payload: dict[str, Any] = point.payload or {}
            chunk_id = str(payload.get("chunk_id", point.id))
            doc_id = str(payload.get("doc_id", ""))
            text = str(payload.get("text", ""))
            score = float(point.score) if point.score is not None else 0.0
            allowed_groups = [str(g) for g in payload.get("allowed_groups", [])]

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text=text,
                    score=score,
                    allowed_groups=allowed_groups,
                )
            )

        return retrieved
