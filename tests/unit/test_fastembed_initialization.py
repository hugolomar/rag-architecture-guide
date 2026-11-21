"""Unit tests for defensive initialization of FastEmbed vectorization adapter.

Verifies that model initialization failures in offline or sandboxed environments
raise actionable RuntimeError exceptions with explicit cache guidance.
"""

from unittest.mock import patch

import pytest

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter

pytestmark = pytest.mark.unit


# ==============================================================================
# Defensive Model Initialization & Operational Error Contract Tests
# ==============================================================================


@patch("src.adapters.embeddings.fastembed_adapter.TextEmbedding")
def test_dense_model_initialization_failure_raises_actionable_runtime_error(
    mock_text_embedding: object,
) -> None:
    """Verify that dense model loading errors raise a RuntimeError with cache instructions."""
    mock_text_embedding.side_effect = ConnectionError("Could not reach HuggingFace Hub")  # type: ignore[attr-defined]

    adapter = FastEmbedAdapter(dense_model_name="BAAI/bge-large-en-v1.5")

    with pytest.raises(
        RuntimeError,
        match=r"Failed to initialize dense model 'BAAI/bge-large-en-v1\.5'\..*ensure model weights are pre-cached",
    ):
        _ = adapter.dense_model


@patch("src.adapters.embeddings.fastembed_adapter.SparseTextEmbedding")
def test_sparse_model_initialization_failure_raises_actionable_runtime_error(
    mock_sparse_embedding: object,
) -> None:
    """Verify that sparse model loading errors raise a RuntimeError with cache instructions."""
    mock_sparse_embedding.side_effect = FileNotFoundError("Missing tokenizer.json")  # type: ignore[attr-defined]

    adapter = FastEmbedAdapter(sparse_model_name="Qdrant/bm25")

    with pytest.raises(
        RuntimeError,
        match=r"Failed to initialize sparse model 'Qdrant/bm25'\..*ensure model weights are pre-cached",
    ):
        _ = adapter.sparse_model


@pytest.mark.parametrize(
    ("model_name", "expected_dimension"),
    [
        ("BAAI/bge-small-en-v1.5", 384),
        ("BAAI/bge-small-en", 384),
        ("BAAI/bge-base-en-v1.5", 768),
        ("BAAI/bge-large-en-v1.5", 1024),
    ],
)
def test_fastembed_adapter_resolves_dimensions_from_registry(
    model_name: str,
    expected_dimension: int,
) -> None:
    """Verify that FastEmbedAdapter auto-resolves dimension from model registry."""
    adapter = FastEmbedAdapter(dense_model_name=model_name)
    assert adapter.dimension == expected_dimension


def test_fastembed_adapter_uses_explicit_dimension_override() -> None:
    """Verify that explicit dimension parameter takes precedence over auto-resolution."""
    adapter = FastEmbedAdapter(dense_model_name="BAAI/bge-small-en-v1.5", dimension=512)
    assert adapter.dimension == 512


def test_fastembed_adapter_dimension_property() -> None:
    """Verify that FastEmbedAdapter exposes its configured vector dimension without loading models."""
    adapter = FastEmbedAdapter(dimension=1024)
    assert adapter.dimension == 1024
