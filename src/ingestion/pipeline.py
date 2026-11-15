"""Batch Ingestion Pipeline Orchestrator.

Implements the end-to-end data plane vertical slice with strict OpenTelemetry
lifecycle management and domain port contracts.
"""

from pathlib import Path

from src.adapters.telemetry.otel_emitter import TelemetryManager
from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.storage import ChunkStorageWriterPort
from src.ingestion.chunker import DocumentChunker
from src.ingestion.config import IngestionConfig
from src.ingestion.manifest_loader import load_and_validate_manifest
from src.ingestion.parser import parse_markdown_document


def run_ingestion_pipeline(
    config: IngestionConfig,
    embedder: EmbedderPort,
    storage: ChunkStorageWriterPort,
    chunker: DocumentChunker,
    telemetry: TelemetryManager | None = None,
) -> dict[str, int]:
    """Execute the observable batch document ingestion workflow.

    Args:
        config: Pipeline runtime configuration.
        embedder: Injected EmbedderPort adapter for dual vector computation.
        storage: Injected ChunkStorageWriterPort adapter for collection persistence.
        chunker: Injected DocumentChunker strategy for document splitting.
        telemetry: Optional injected TelemetryManager (defaults to instance from config).

    Returns:
        Summary dict containing counts of processed documents, chunks, and points.
    """
    if telemetry is None:
        telemetry = TelemetryManager(
            service_name=config.otel_service_name,
            log_level=config.log_level,
        )

    manifest_path = Path(config.rag_manifest_path)
    raw_dir = Path(config.rag_data_dir)

    with telemetry.start_stage_span("run"):
        telemetry.log("INFO", "Initiating governed document ingestion batch", stage="init")

        # 1. Manifest Validation & Lifecycle Filter (FR-001, FR-002, FR-003, FR-004)
        with telemetry.start_stage_span("manifest.validate") as span:
            active_records, archived_records = load_and_validate_manifest(manifest_path, raw_dir)
            span.set_attribute("total_records", len(active_records) + len(archived_records))
            span.set_attribute("active_records", len(active_records))
            span.set_attribute("archived_records", len(archived_records))

            telemetry.log(
                "INFO",
                f"Manifest validated successfully: {len(active_records)} active, {len(archived_records)} archived",
                stage="manifest",
                active_count=len(active_records),
                archived_count=len(archived_records),
            )
            telemetry.record_documents_rejected(len(archived_records))

        # 2. Markdown Parsing (FR-005)
        canonical_docs = []
        with telemetry.start_stage_span("document.parse") as span:
            for record in active_records:
                file_path = raw_dir / record.relative_path
                doc = parse_markdown_document(file_path, record)
                canonical_docs.append(doc)
            span.set_attribute("parsed_count", len(canonical_docs))
            telemetry.log(
                "INFO",
                f"Parsed {len(canonical_docs)} Markdown documents with metadata",
                stage="parse",
                doc_count=len(canonical_docs),
            )
            telemetry.record_documents_processed(len(canonical_docs))

        # 3. Structure-Preserving Chunking (FR-006, FR-007)
        all_chunks: list[GovernedChunk] = []
        with telemetry.start_stage_span("document.chunk") as span:
            for doc in canonical_docs:
                chunks = chunker.chunk_document(doc)
                all_chunks.extend(chunks)
            span.set_attribute("chunks_count", len(all_chunks))
            telemetry.log(
                "INFO",
                f"Generated {len(all_chunks)} governed chunks (tables preserved)",
                stage="chunk",
            )
            telemetry.record_chunks_created(len(all_chunks))

        # 4. Dual Embedding (FR-008)
        with telemetry.start_stage_span("embeddings.compute") as span:
            vectorized_chunks: list[VectorizedChunk] = embedder.vectorize_chunks(all_chunks)
            span.set_attribute("vectorized_count", len(vectorized_chunks))
            telemetry.log(
                "INFO",
                f"Computed dual vectors (BGE dense + BM25 sparse) for {len(vectorized_chunks)} chunks",
                stage="embed",
            )

        # 5. Storage Persistence (FR-009)
        with telemetry.start_stage_span("storage.upsert") as span:
            storage.ensure_collection(config.qdrant_collection_name)
            total_upserted = storage.upsert_chunks(config.qdrant_collection_name, vectorized_chunks)
            span.set_attribute("points_upserted", total_upserted)
            telemetry.log(
                "INFO",
                f"Upserted {total_upserted} points into Qdrant collection '{config.qdrant_collection_name}'",
                stage="storage",
                chunks_indexed=total_upserted,
            )

        telemetry.log("INFO", "Batch ingestion workflow completed successfully", stage="complete")

    return {
        "active_documents": len(canonical_docs),
        "archived_documents": len(archived_records),
        "chunks_generated": len(all_chunks),
        "points_indexed": total_upserted,
    }
