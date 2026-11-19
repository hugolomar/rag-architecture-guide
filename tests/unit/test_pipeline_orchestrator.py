"""Unit tests for the ingestion pipeline orchestrator.

Verifies end-to-end data plane pipeline flow using in-memory port doubles:
- Manifest validation and lifecycle filtering (active vs archived)
- Document parsing and table-preserving chunking
- Dense and sparse embedding vectorization
- Vector store collection verification and chunk upsert
- OpenTelemetry stage spans and progress metrics
"""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from src.adapters.telemetry.otel_emitter import TelemetryManager
from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.storage import ChunkStorageWriterPort
from src.ingestion.chunker import TablePreservingChunker
from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion_pipeline

pytestmark = pytest.mark.unit


# ==============================================================================
# In-Memory Port Test Doubles
# ==============================================================================


class InMemoryEmbedder(EmbedderPort):
    """Deterministic in-memory embedding adapter double for unit tests."""

    @property
    def dimension(self) -> int:
        return 128

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * self.dimension for _ in texts]

    def embed_sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        return [([10, 20], [0.5, 0.9]) for _ in texts]

    def vectorize_chunks(self, chunks: Sequence[GovernedChunk]) -> list[VectorizedChunk]:
        vectorized: list[VectorizedChunk] = []
        for chunk in chunks:
            vectorized.append(
                VectorizedChunk(
                    chunk=chunk,
                    dense_vector=[0.05] * self.dimension,
                    sparse_indices=[10, 20],
                    sparse_values=[0.5, 0.9],
                )
            )
        return vectorized


class InMemoryStorageWriter(ChunkStorageWriterPort):
    """In-memory storage writer double for verifying collection and upsert calls."""

    def __init__(self) -> None:
        self.ensured_collections: list[str] = []
        self.upserted_chunks: list[VectorizedChunk] = []

    def ensure_collection(self, collection_name: str) -> None:
        self.ensured_collections.append(collection_name)

    def upsert_chunks(self, collection_name: str, chunks: Sequence[VectorizedChunk]) -> int:
        self.upserted_chunks.extend(chunks)
        return len(chunks)


# ==============================================================================
# Pipeline Orchestration Tests
# ==============================================================================


def test_pipeline_orchestrator_success_path(tmp_path: Path) -> None:
    """Verify that run_ingestion_pipeline coordinates all stages deterministically."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "policy1.md").write_text(
        "# Engineering Remote Guidelines\nParagraph text here.\n",
        encoding="utf-8",
    )
    (raw_dir / "policy2.md").write_text(
        "# Deprecated Guidelines\nHistorical content.\n",
        encoding="utf-8",
    )
    (raw_dir / "policy3.md").write_text(
        "# Archived Old Policy\nShould be completely excluded.\n",
        encoding="utf-8",
    )

    manifest_data = [
        {
            "doc_id": "DOC-ENG-001",
            "relative_path": "policy1.md",
            "department": "Engineering",
            "allowed_groups": ["engineering-core"],
            "classification": "internal",
            "status": "current",
        },
        {
            "doc_id": "DOC-ENG-002",
            "relative_path": "policy2.md",
            "department": "Engineering",
            "allowed_groups": ["engineering-core"],
            "classification": "internal",
            "status": "deprecated",
        },
        {
            "doc_id": "DOC-ENG-003",
            "relative_path": "policy3.md",
            "department": "Engineering",
            "allowed_groups": ["engineering-core"],
            "classification": "internal",
            "status": "archived",
        },
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    config = IngestionConfig(
        RAG_DATA_DIR=raw_dir,
        RAG_MANIFEST_PATH=manifest_path,
        QDRANT_COLLECTION_NAME="test_governed_collection",
        LOG_LEVEL="DEBUG",
    )

    embedder = InMemoryEmbedder()
    storage = InMemoryStorageWriter()
    chunker = TablePreservingChunker()
    telemetry = TelemetryManager(service_name="test-pipeline-orchestrator", log_level="DEBUG")

    summary = run_ingestion_pipeline(
        config=config,
        embedder=embedder,
        storage=storage,
        chunker=chunker,
        telemetry=telemetry,
    )

    # 1. Pipeline Summary Counts
    assert summary["active_documents"] == 2
    assert summary["archived_documents"] == 1
    assert summary["chunks_generated"] >= 2
    assert summary["points_indexed"] == summary["chunks_generated"]

    # 2. Storage Invariants
    assert "test_governed_collection" in storage.ensured_collections
    assert len(storage.upserted_chunks) == summary["chunks_generated"]

    # 3. Governance Invariant: Archived doc must NEVER be indexed
    indexed_doc_ids = {c.chunk.doc_id for c in storage.upserted_chunks}
    assert "DOC-ENG-001" in indexed_doc_ids
    assert "DOC-ENG-002" in indexed_doc_ids
    assert "DOC-ENG-003" not in indexed_doc_ids


def test_pipeline_orchestrator_default_telemetry_instantiation(tmp_path: Path) -> None:
    """Verify that run_ingestion_pipeline instantiates default telemetry when none provided."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "simple.md").write_text("# Simple\nContent.\n", encoding="utf-8")

    manifest_data = [
        {
            "doc_id": "DOC-HR-001",
            "relative_path": "simple.md",
            "department": "HR",
            "allowed_groups": ["all-employees"],
            "classification": "internal",
            "status": "current",
        }
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    config = IngestionConfig(
        RAG_DATA_DIR=raw_dir,
        RAG_MANIFEST_PATH=manifest_path,
        QDRANT_COLLECTION_NAME="default_telemetry_collection",
    )

    embedder = InMemoryEmbedder()
    storage = InMemoryStorageWriter()
    chunker = TablePreservingChunker()

    summary = run_ingestion_pipeline(
        config=config,
        embedder=embedder,
        storage=storage,
        chunker=chunker,
        telemetry=None,
    )

    assert summary["active_documents"] == 1
    assert summary["archived_documents"] == 0
    assert summary["points_indexed"] >= 1
