"""Integration tests for FastEmbed vectorization adapter.

Verifies dense semantic embeddings, sparse BM25 token indices and weights,
and full GovernedChunk vectorization using FastEmbed.
"""

import math

import pytest

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import GovernedChunk
from src.domain.ports.embeddings import EmbedderPort

pytestmark = pytest.mark.integration


# ==============================================================================
# Port Contract Conformance & Fixture Setup
# ==============================================================================


@pytest.fixture(scope="module")
def embedder() -> FastEmbedAdapter:
    """Initialize FastEmbed adapter once for all tests in this module."""
    adapter = FastEmbedAdapter()
    try:
        # Eagerly probe models to detect missing local weights in offline/sandboxed environments
        _ = adapter.dense_model
        _ = adapter.sparse_model
    except Exception as exc:
        pytest.skip(
            f"FastEmbed models not pre-cached in local cache: {exc}. "
            "Run 'bash scripts/warmup_models.sh' to download models, or execute via Docker."
        )
    return adapter


def test_fastembed_inherits_from_embedder_port() -> None:
    """Verify that FastEmbedAdapter strictly satisfies the EmbedderPort contract."""
    assert isinstance(FastEmbedAdapter(), EmbedderPort)


# ==============================================================================
# Dense & Sparse Vector Embeddings Generation
# ==============================================================================


def test_dense_embeddings_generation(embedder: FastEmbedAdapter) -> None:
    """Verify that dense embeddings produce finite vectors matching declared dimension."""
    texts = [
        "Docker bridge networking connects containers on the same daemon host.",
        "Security incident response SLA requires acknowledgment within 15 minutes.",
    ]
    dense_vectors = embedder.embed_dense(texts)

    assert len(dense_vectors) == 2
    for vec in dense_vectors:
        assert len(vec) == embedder.dimension, (
            f"Expected {embedder.dimension} dimensions, got {len(vec)}"
        )
        assert all(math.isfinite(val) for val in vec), "Found non-finite float in dense vector"


def test_sparse_bm25_embeddings_generation(embedder: FastEmbedAdapter) -> None:
    """Verify that sparse BM25 produces non-empty token indices and positive weights."""
    texts = ["flag --log-driver=awslogs and error code 404"]
    sparse_vectors = embedder.embed_sparse(texts)

    assert len(sparse_vectors) == 1
    indices, values = sparse_vectors[0]
    assert len(indices) > 0
    assert len(indices) == len(values)
    assert all(val > 0.0 for val in values), "BM25 token weights must be positive"


# ==============================================================================
# GovernedChunk Vectorization & Batch Boundary Tests
# ==============================================================================


def test_vectorize_chunks_full_contract(embedder: FastEmbedAdapter) -> None:
    """Verify that vectorize_chunks enriches GovernedChunk into VectorizedChunk with dual vectors."""
    chunk = GovernedChunk(
        chunk_id="DOC-ENG-001#c0",
        doc_id="DOC-ENG-001",
        chunk_index=0,
        text="Docker networking connects containers with bridge driver.",
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        department=Department.ENGINEERING,
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )
    vectorized_chunks = embedder.vectorize_chunks([chunk])

    assert len(vectorized_chunks) == 1
    v_chunk = vectorized_chunks[0]
    assert v_chunk.chunk == chunk
    assert len(v_chunk.dense_vector) == embedder.dimension
    assert len(v_chunk.sparse_indices) > 0
    assert len(v_chunk.sparse_indices) == len(v_chunk.sparse_values)


def test_empty_batch_handling() -> None:
    """Verify graceful empty batch handling across all adapter methods."""
    adapter = FastEmbedAdapter()
    assert adapter.embed_dense([]) == []
    assert adapter.embed_sparse([]) == []
    assert adapter.vectorize_chunks([]) == []
