"""End-to-end integration test for the batch ingestion pipeline.

Verifies complete execution from raw documents to populated Qdrant storage,
enforcing:
- Zero-trust exclusion of archived documents (Articles 7 & 13, SC-002)
- Strict pipeline summary metrics (Article 11, US4)
- Deterministic dual vector persistence (dense BGE + sparse BM25)
"""

import json
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.ingestion.chunker import TablePreservingChunker
from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion_pipeline

pytestmark = pytest.mark.integration


def test_end_to_end_batch_ingestion(tmp_path: Path) -> None:
    """Verify complete batch ingestion cycle with real FastEmbed and in-memory Qdrant."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "corp1.md").write_text(
        "# Remote Policy\n| Dept | Hours |\n|---|---|\n| HR | 40 |\n",
        encoding="utf-8",
    )
    (raw_dir / "corp2.md").write_text(
        "# Deprecated Security Rule\nRule body text.\n",
        encoding="utf-8",
    )
    (raw_dir / "corp3.md").write_text(
        "# Archived Legacy Doc\nShould never be indexed.\n",
        encoding="utf-8",
    )

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
    embedder = FastEmbedAdapter()
    storage = QdrantStorageAdapter(client=client, vector_size=embedder.dimension)
    chunker = TablePreservingChunker()

    results = run_ingestion_pipeline(
        config=config,
        embedder=embedder,
        storage=storage,
        chunker=chunker,
    )

    assert results["active_documents"] == 2
    assert results["archived_documents"] == 1
    assert results["points_indexed"] >= 2
    assert results["chunks_generated"] == results["points_indexed"]

    # Verify SC-002: Exactly 0% archived documents indexed
    points, _ = client.scroll(
        collection_name="e2e_governed_docs",
        limit=50,
        with_payload=True,
        with_vectors=True,
    )

    assert len(points) >= 2, "Expected at least 2 points indexed in Qdrant collection"

    # Symmetric set comparison guarantees active docs exist and NO leaked archived docs
    doc_ids_in_store = {p.payload["doc_id"] for p in points if p.payload and "doc_id" in p.payload}
    assert doc_ids_in_store == {"DOC-HR-001", "DOC-SEC-002"}

    for p in points:
        assert p.payload is not None
        assert p.payload["status"] in ("current", "deprecated")
        assert "is_tabular" in p.payload
        assert isinstance(p.vector, dict)
        dense_vec = p.vector["dense"]
        assert isinstance(dense_vec, list)
        assert len(dense_vec) == embedder.dimension
        sparse_vec = p.vector["sparse"]
        assert hasattr(sparse_vec, "indices")
        assert hasattr(sparse_vec, "values")
        assert len(sparse_vec.indices) > 0
        assert len(sparse_vec.indices) == len(sparse_vec.values)
