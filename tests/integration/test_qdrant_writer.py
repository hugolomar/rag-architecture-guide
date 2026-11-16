"""Integration tests for Qdrant storage adapter (FR-009, User Story 2, Article 11).

Verifies collection creation matching contracts/qdrant-collection.json,
dual vector persistence (named dense and sparse vectors), and payload filtering.
Uses Qdrant's embedded in-memory engine (:memory:) per Article 11 (real engine in RAM).
"""

import pytest
from qdrant_client import QdrantClient

from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.storage import ChunkStorageWriterPort

pytestmark = pytest.mark.integration

VECTOR_SIZE = 1024


# ==============================================================================
# Port Contract Conformance Tests (Article 3)
# ==============================================================================


def test_qdrant_adapter_inherits_from_port() -> None:
    """Verify that QdrantStorageAdapter strictly satisfies ChunkStorageWriterPort (Article 3)."""
    # Qdrant :memory: runs the real native engine in RAM, satisfying Article 11 without Docker
    client = QdrantClient(":memory:")
    adapter = QdrantStorageAdapter(client=client, vector_size=VECTOR_SIZE)
    assert isinstance(adapter, ChunkStorageWriterPort)


# ==============================================================================
# Collection Setup, Dual-Vector Upsert, & Payload Retrieval Tests
# ==============================================================================


def test_qdrant_adapter_ensure_collection_and_upsert() -> None:
    """Verify collection initialization, named dual-vector upsert, and payload retrieval."""
    client = QdrantClient(":memory:")
    adapter = QdrantStorageAdapter(client=client, vector_size=VECTOR_SIZE)
    collection_name = "test_governed_docs"

    # 1. Initialize collection (calling twice verifies idempotency)
    adapter.ensure_collection(collection_name)
    adapter.ensure_collection(collection_name)
    collection_info = client.get_collection(collection_name)
    assert collection_info.config.params.vectors is not None
    assert isinstance(collection_info.config.params.vectors, dict)
    assert "dense" in collection_info.config.params.vectors

    # 2. Build vectorized chunks
    chunk1 = GovernedChunk(
        chunk_id="DOC-ENG-001#c0",
        doc_id="DOC-ENG-001",
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        status=LifecycleStatus.CURRENT,
        department=Department.ENGINEERING,
        classification=Classification.INTERNAL,
        chunk_index=0,
        text="Docker bridge networking explanation.",
        is_tabular=False,
    )
    vchunk1 = VectorizedChunk(
        chunk=chunk1,
        dense_vector=[0.1] * VECTOR_SIZE,
        sparse_indices=[12, 45, 88],
        sparse_values=[1.2, 0.8, 2.5],
    )

    chunk2 = GovernedChunk(
        chunk_id="DOC-HR-001#c0",
        doc_id="DOC-HR-001",
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        status=LifecycleStatus.DEPRECATED,
        department=Department.HR,
        classification=Classification.INTERNAL,
        chunk_index=0,
        text="Deprecated remote work policy.",
        is_tabular=False,
    )
    vchunk2 = VectorizedChunk(
        chunk=chunk2,
        dense_vector=[0.2] * VECTOR_SIZE,
        sparse_indices=[3, 7],
        sparse_values=[0.5, 1.1],
    )

    # 3. Upsert
    persisted_count = adapter.upsert_chunks(collection_name, [vchunk1, vchunk2])
    assert persisted_count == 2
    assert adapter.upsert_chunks(collection_name, []) == 0

    # 4. Scroll and verify payload and dual vectors
    points, _ = client.scroll(
        collection_name=collection_name, limit=10, with_vectors=True, with_payload=True
    )
    assert len(points) == 2

    point_map = {p.payload["chunk_id"]: p for p in points if p.payload and "chunk_id" in p.payload}
    assert set(point_map.keys()) == {"DOC-ENG-001#c0", "DOC-HR-001#c0"}

    # Verify point 1 (Engineering - current)
    p1 = point_map["DOC-ENG-001#c0"]
    assert p1.payload is not None
    assert p1.payload["allowed_groups"] == ["engineering-core"]
    assert p1.payload["status"] == "current"
    assert isinstance(p1.vector, dict)
    dense_vec1 = p1.vector["dense"]
    assert isinstance(dense_vec1, list)
    assert len(dense_vec1) == VECTOR_SIZE
    sparse_vec1 = p1.vector["sparse"]
    assert hasattr(sparse_vec1, "indices")
    assert hasattr(sparse_vec1, "values")
    assert len(sparse_vec1.indices) == 3
    assert len(sparse_vec1.indices) == len(sparse_vec1.values)

    # Verify point 2 (HR - deprecated)
    p2 = point_map["DOC-HR-001#c0"]
    assert p2.payload is not None
    assert p2.payload["allowed_groups"] == ["all-employees"]
    assert p2.payload["status"] == "deprecated"
    assert isinstance(p2.vector, dict)
    dense_vec2 = p2.vector["dense"]
    assert isinstance(dense_vec2, list)
    assert len(dense_vec2) == VECTOR_SIZE
    sparse_vec2 = p2.vector["sparse"]
    assert hasattr(sparse_vec2, "indices")
    assert hasattr(sparse_vec2, "values")
    assert len(sparse_vec2.indices) == 2
    assert len(sparse_vec2.indices) == len(sparse_vec2.values)
