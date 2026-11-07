"""Integration test for FastEmbed vectorization adapter (Article 14, FR-008).

Verifies 1024-dimensional dense semantic embeddings and sparse BM25 token
indices and weights using FastEmbed.
"""

import math
import pytest
from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.domain.ports.embeddings import EmbedderPort


def test_fastembed_inherits_from_embedder_port() -> None:
    """Verify that FastEmbedAdapter strictly satisfies the EmbedderPort contract."""
    adapter = FastEmbedAdapter()
    assert isinstance(adapter, EmbedderPort)


@pytest.mark.integration
def test_dense_embeddings_generation() -> None:
    """Verify that dense embeddings produce finite 1024-dimensional vectors."""
    adapter = FastEmbedAdapter()
    texts = [
        "Docker bridge networking connects containers on the same daemon host.",
        "Security incident response SLA requires acknowledgment within 15 minutes.",
    ]
    dense_vectors = adapter.embed_dense(texts)

    assert len(dense_vectors) == 2
    for vec in dense_vectors:
        assert len(vec) == 1024, f"Expected 1024 dimensions, got {len(vec)}"
        assert all(math.isfinite(val) for val in vec), "Found non-finite float in dense vector"


@pytest.mark.integration
def test_sparse_bm25_embeddings_generation() -> None:
    """Verify that sparse BM25 produces non-empty token indices and positive weights."""
    adapter = FastEmbedAdapter()
    texts = ["flag --log-driver=awslogs and error code 404"]
    sparse_vectors = adapter.embed_sparse(texts)

    assert len(sparse_vectors) == 1
    indices, values = sparse_vectors[0]
    assert len(indices) > 0
    assert len(indices) == len(values)
    assert all(val > 0.0 for val in values), "BM25 token weights must be positive"

