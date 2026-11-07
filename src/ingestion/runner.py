"""Batch Ingestion Pipeline CLI and Orchestrator.

Implements the end-to-end data plane vertical slice with strict OpenTelemetry
lifecycle management, structured JSON logging, and exit code contracts.
"""

from pathlib import Path
import sys

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.adapters.telemetry.otel_emitter import TelemetryManager
from src.domain.manifest import load_and_validate_manifest
from src.domain.models import GovernedChunk, VectorizedChunk
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.storage import ChunkStorageWriterPort
from src.ingestion.chunker import TablePreservingChunker
from src.ingestion.config import IngestionConfig
from src.ingestion.parser import parse_markdown_document


def run_ingestion_pipeline(
    config: IngestionConfig | None = None,
    embedder: EmbedderPort | None = None,
    storage: ChunkStorageWriterPort | None = None,
    telemetry: TelemetryManager | None = None,
) -> dict[str, int]:
    """Execute the observable batch document ingestion workflow.

    Args:
        config: Pipeline runtime configuration (defaults to environment settings).
        embedder: Optional injected EmbedderPort adapter.
        storage: Optional injected ChunkStorageWriterPort adapter.
        telemetry: Optional injected TelemetryManager.

    Returns:
        Summary dict containing counts of processed documents, chunks, and points.
    """
    if config is None:
        config = IngestionConfig()

    if telemetry is None:
        telemetry = TelemetryManager(
            service_name=config.otel_service_name,
            log_level=config.log_level,
        )

    manifest_path = Path(config.rag_manifest_path)
    raw_dir = Path(config.rag_data_dir)

    with telemetry.start_stage_span("run") as root_span:
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
            chunker = TablePreservingChunker()
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
        if embedder is None:
            embedder = FastEmbedAdapter()

        with telemetry.start_stage_span("embeddings.compute") as span:
            if hasattr(embedder, "vectorize_chunks"):
                vectorized_chunks: list[VectorizedChunk] = embedder.vectorize_chunks(all_chunks)
            else:
                texts = [c.text for c in all_chunks]
                dense_vectors = embedder.embed_dense(texts)
                sparse_vectors = embedder.embed_sparse(texts)
                vectorized_chunks = [
                    VectorizedChunk(
                        chunk=chunk,
                        dense_vector=dense,
                        sparse_indices=sparse[0],
                        sparse_values=sparse[1],
                    )
                    for chunk, dense, sparse in zip(all_chunks, dense_vectors, sparse_vectors)
                ]
            span.set_attribute("vectorized_count", len(vectorized_chunks))
            telemetry.log(
                "INFO",
                f"Computed dual vectors (BGE dense + BM25 sparse) for {len(vectorized_chunks)} chunks",
                stage="embed",
            )

        # 5. Storage Persistence (FR-009)
        if storage is None:
            storage = QdrantStorageAdapter(host=config.qdrant_host, port=config.qdrant_port)

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


def main() -> int:
    """CLI Entrypoint with explicit exit codes and guaranteed telemetry flush."""
    config = IngestionConfig()
    telemetry = TelemetryManager(
        service_name=config.otel_service_name,
        log_level=config.log_level,
    )

    exit_code = 0
    try:
        run_ingestion_pipeline(config=config, telemetry=telemetry)
        exit_code = 0
    except ValueError as exc:
        # Schema / manifest validation failure (Exit Code 1)
        telemetry.log("ERROR", f"Manifest schema validation failure: {exc}", stage="manifest")
        exit_code = 1
    except FileNotFoundError as exc:
        # Corpus file mismatch / missing file (Exit Code 2)
        telemetry.log("ERROR", f"Corpus file mismatch or missing file: {exc}", stage="parse")
        exit_code = 2
    except ConnectionError as exc:
        # Vector store connection / operation failure (Exit Code 3)
        telemetry.log("ERROR", f"Vector store storage failure: {exc}", stage="storage")
        exit_code = 3
    except Exception as exc:
        # Generic failure
        telemetry.log("ERROR", f"Unexpected batch ingestion failure: {exc}", stage="general")
        exit_code = 3
    finally:
        try:
            telemetry.flush_and_shutdown()
        except Exception as flush_exc:
            print(f"Failed to flush telemetry: {flush_exc}", file=sys.stderr)
            if exit_code == 0:
                exit_code = 4

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
