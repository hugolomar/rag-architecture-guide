"""Qdrant storage writer adapter implementing ChunkStorageWriterPort.

In accordance with FR-009, ADR 0006, and contracts/qdrant-collection.json,
initializes hybrid collections with named dense and sparse vectors, creates
governance payload indexes, and persists vectorized chunks with full metadata.
"""

import uuid
from collections.abc import Sequence

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.domain.models import VectorizedChunk
from src.domain.ports.storage import ChunkStorageWriterPort

# Deterministic namespace for chunk point UUID generation
CHUNK_UUID_NAMESPACE = uuid.UUID("a2c7e0f1-4b82-4f31-897b-9c8e1a4d5e2f")


class QdrantStorageAdapter(ChunkStorageWriterPort):
    """Outbound adapter for persisting governed chunks to Qdrant."""

    def __init__(
        self,
        vector_size: int,
        host: str = "localhost",
        port: int = 6333,
        client: QdrantClient | None = None,
    ) -> None:
        """Initialize with target vector dimensionality and either client or connection parameters.

        Args:
            vector_size: Dimensionality of dense vectors to be stored in collections.
            host: Qdrant service host.
            port: Qdrant REST port.
            client: Optional injected QdrantClient (useful for testing or in-memory mode).
        """
        self.vector_size = vector_size
        if client is not None:
            self.client = client
        else:
            self.client = QdrantClient(host=host, port=port)

    def ensure_collection(self, collection_name: str) -> None:
        """Create collection and payload indexes matching contracts/qdrant-collection.json.

        Args:
            collection_name: Target Qdrant collection name.
        """
        collections = self.client.get_collections().collections
        existing_names = {col.name for col in collections}

        if collection_name not in existing_names:
            # Configure named dense and sparse vectors per contract
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False),
                        modifier=models.Modifier.IDF,
                    )
                },
            )

        # Create payload keyword indexes for pre-filtering (zero-trust trimming)
        indexed_fields = ["doc_id", "allowed_groups", "status", "department", "classification"]
        for field in indexed_fields:
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                # Index may already exist; safe to continue
                pass

    def upsert_chunks(self, collection_name: str, chunks: Sequence[VectorizedChunk]) -> int:
        """Persist a batch of vectorized chunks into Qdrant.

        Args:
            collection_name: Target collection name.
            chunks: Sequence of VectorizedChunk instances.

        Returns:
            Number of points successfully upserted.
        """
        if not chunks:
            return 0

        points: list[models.PointStruct] = []
        for vchunk in chunks:
            chunk = vchunk.chunk

            # Generate deterministic UUID from chunk_id for idempotency
            point_id = str(uuid.uuid5(CHUNK_UUID_NAMESPACE, chunk.chunk_id))

            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "allowed_groups": [g.value for g in chunk.allowed_groups],
                "status": chunk.status.value,
                "department": chunk.department.value,
                "classification": chunk.classification.value,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "is_tabular": chunk.is_tabular,
            }

            vectors = {
                "dense": vchunk.dense_vector,
                "sparse": models.SparseVector(
                    indices=vchunk.sparse_indices,
                    values=vchunk.sparse_values,
                ),
            }

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vectors,
                    payload=payload,
                )
            )

        # Batch upsert in batches of 50
        batch_size = 50
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True,
            )
            total_upserted += len(batch)

        return total_upserted

