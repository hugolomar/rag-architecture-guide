"""Integration tests for Qdrant hybrid retrieval adapter.

Verifies hybrid search scoring, pre-inference security trimming by caller
groups, and deterministic exclusion of archived documents against embedded
in-memory Qdrant.
"""

import pytest
from qdrant_client import QdrantClient

from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.retrieval import RetrievalPort

pytestmark = pytest.mark.integration

VECTOR_SIZE = 4
COLLECTION_NAME = "test_retrieval_collection"


class MockEmbedder(EmbedderPort):
    """Deterministic in-memory embedder double for integration tests."""

    @property
    def dimension(self) -> int:
        return VECTOR_SIZE

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        return [([1], [1.0]) for _ in texts]

    def vectorize_chunks(self, chunks: object) -> list[VectorizedChunk]:
        return []


@pytest.fixture
def populated_qdrant() -> QdrantClient:
    """Initialize in-memory Qdrant populated with test chunks across departments and lifecycles."""
    client = QdrantClient(":memory:")
    writer = QdrantStorageAdapter(client=client, vector_size=VECTOR_SIZE)
    writer.ensure_collection(COLLECTION_NAME)

    # 1. Engineering Active
    chunk_eng = VectorizedChunk(
        chunk=GovernedChunk(
            chunk_id="DOC-ENG-001#c0",
            doc_id="DOC-ENG-001",
            allowed_groups=[IdPGroup.ENGINEERING_CORE, IdPGroup.ALL_EMPLOYEES],
            status=LifecycleStatus.CURRENT,
            department=Department.ENGINEERING,
            classification=Classification.INTERNAL,
            chunk_index=0,
            text="Docker deployment procedures and container standards.",
        ),
        dense_vector=[1.0, 0.0, 0.0, 0.0],
        sparse_indices=[1, 2],
        sparse_values=[1.0, 1.0],
    )

    # 2. HR Confidential Active
    chunk_hr = VectorizedChunk(
        chunk=GovernedChunk(
            chunk_id="DOC-HR-001#c0",
            doc_id="DOC-HR-001",
            allowed_groups=[IdPGroup.PEOPLE_TEAM],
            status=LifecycleStatus.CURRENT,
            department=Department.HR,
            classification=Classification.RESTRICTED,
            chunk_index=0,
            text="Confidential executive compensation and bonus structures.",
        ),
        dense_vector=[1.0, 0.0, 0.0, 0.0],
        sparse_indices=[1, 2],
        sparse_values=[1.0, 1.0],
    )

    # 3. Engineering Archived
    chunk_archived = VectorizedChunk(
        chunk=GovernedChunk(
            chunk_id="DOC-ENG-OLD#c0",
            doc_id="DOC-ENG-OLD",
            allowed_groups=[IdPGroup.ENGINEERING_CORE],
            status=LifecycleStatus.ARCHIVED,
            department=Department.ENGINEERING,
            classification=Classification.INTERNAL,
            chunk_index=0,
            text="Obsolete Docker deployment guidelines from 2018.",
        ),
        dense_vector=[1.0, 0.0, 0.0, 0.0],
        sparse_indices=[1, 2],
        sparse_values=[1.0, 1.0],
    )

    writer.upsert_chunks(COLLECTION_NAME, [chunk_eng, chunk_hr, chunk_archived])
    return client


# ==========================================
# RETRIEVAL CONFORMANCE & SECURITY TRIMMING
# ==========================================


def test_retrieval_adapter_inherits_from_port(populated_qdrant: QdrantClient) -> None:
    """Verify that QdrantRetrievalAdapter satisfies RetrievalPort."""
    from src.adapters.retrieval.qdrant_retrieval import QdrantRetrievalAdapter

    adapter = QdrantRetrievalAdapter(
        client=populated_qdrant,
        embedder=MockEmbedder(),
        collection_name=COLLECTION_NAME,
    )
    assert isinstance(adapter, RetrievalPort)


def test_security_trimming_isolates_restricted_documents(populated_qdrant: QdrantClient) -> None:
    """Verify that callers with engineering groups cannot retrieve HR confidential documents."""
    from src.adapters.retrieval.qdrant_retrieval import QdrantRetrievalAdapter

    adapter = QdrantRetrievalAdapter(
        client=populated_qdrant,
        embedder=MockEmbedder(),
        collection_name=COLLECTION_NAME,
    )

    # Caller has engineering-core only
    results = adapter.retrieve(
        query="compensation or deployment",
        caller_groups={"engineering-core"},
        top_k=5,
    )

    retrieved_doc_ids = {r.doc_id for r in results}
    assert "DOC-ENG-001" in retrieved_doc_ids
    assert "DOC-HR-001" not in retrieved_doc_ids


def test_lifecycle_filter_excludes_archived_documents(populated_qdrant: QdrantClient) -> None:
    """Verify that archived documents are completely excluded even if query matches text."""
    from src.adapters.retrieval.qdrant_retrieval import QdrantRetrievalAdapter

    adapter = QdrantRetrievalAdapter(
        client=populated_qdrant,
        embedder=MockEmbedder(),
        collection_name=COLLECTION_NAME,
    )

    results = adapter.retrieve(
        query="Obsolete Docker deployment guidelines from 2018",
        caller_groups={"engineering-core"},
        top_k=5,
    )

    retrieved_doc_ids = {r.doc_id for r in results}
    assert "DOC-ENG-OLD" not in retrieved_doc_ids
