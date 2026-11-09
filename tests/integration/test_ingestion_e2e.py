"""End-to-end integration test for the ingestion pipeline (Article 16, US4).

Executes the complete batch pipeline from raw documents to populated Qdrant
storage, asserting on document throughput, dual vectors, and zero archived points.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from qdrant_client import QdrantClient

from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.embeddings import EmbedderPort
from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion_pipeline


class FastMockEmbedder(EmbedderPort):
    """Fast mock embedder for deterministic end-to-end testing."""

    def embed_dense(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * 1024 for _ in texts]

    def embed_sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        return [([1, 2, 3], [1.0, 2.0, 3.0]) for _ in texts]

    def vectorize_chunks(self, chunks: Sequence[GovernedChunk]) -> list[VectorizedChunk]:
        return [
            VectorizedChunk(
                chunk=c,
                dense_vector=[0.05] * 1024,
                sparse_indices=[1, 2, 3],
                sparse_values=[1.0, 2.0, 3.0],
            )
            for c in chunks
        ]


def test_end_to_end_batch_ingestion(tmp_path: Path) -> None:
    """Verify complete batch ingestion cycle with in-memory Qdrant storage."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "corp1.md").write_text("# Remote Policy\n| Dept | Hours |\n|---|---|\n| HR | 40 |\n", encoding="utf-8")
    (raw_dir / "corp2.md").write_text("# Deprecated Security Rule\nRule body text.\n", encoding="utf-8")
    (raw_dir / "corp3.md").write_text("# Archived Legacy Doc\nShould never be indexed.\n", encoding="utf-8")

    manifest = [
        {
            "doc_id": "DOC-HR-001",
            "relative_path": "corp1.md",
            "department": "HR",
            "allowed_groups": ["all-employees"],
            "classification": "internal",
            "status": "current",
        },
        {
            "doc_id": "DOC-SEC-002",
            "relative_path": "corp2.md",
            "department": "Security",
            "allowed_groups": ["security-oncall"],
            "classification": "restricted",
            "status": "deprecated",
        },
        {
            "doc_id": "DOC-LEG-003",
            "relative_path": "corp3.md",
            "department": "Legal",
            "allowed_groups": ["leadership"],
            "classification": "restricted",
            "status": "archived",
        },
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    config = IngestionConfig(
        RAG_DATA_DIR=raw_dir,
        RAG_MANIFEST_PATH=manifest_path,
        QDRANT_COLLECTION_NAME="e2e_governed_docs",
    )

    client = QdrantClient(":memory:")
    storage = QdrantStorageAdapter(client=client)
    embedder = FastMockEmbedder()

    results = run_ingestion_pipeline(
        config=config,
        embedder=embedder,
        storage=storage,
    )

    assert results["active_documents"] == 2
    assert results["archived_documents"] == 1
    assert results["points_indexed"] >= 2

    # Verify SC-002: Exactly 0% archived documents indexed
    points, _ = client.scroll(
        collection_name="e2e_governed_docs",
        limit=50,
        with_payload=True,
        with_vectors=True,
    )

    doc_ids_in_store = {p.payload["doc_id"] for p in points}
    assert "DOC-HR-001" in doc_ids_in_store
    assert "DOC-SEC-002" in doc_ids_in_store
    assert "DOC-LEG-003" not in doc_ids_in_store, "Archived document leaked into index!"

    for p in points:
        assert p.payload["status"] in ("current", "deprecated")
        assert len(p.vector["dense"]) == 1024
        assert len(p.vector["sparse"].indices) > 0

