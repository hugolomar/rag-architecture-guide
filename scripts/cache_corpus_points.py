"""Helper script to pre-compute and cache vectorized corpus points for hermetic evals."""

import json
import logging
from pathlib import Path
import time

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.ingestion.chunker import TablePreservingChunker
from src.ingestion.config import IngestionConfig
from src.ingestion.manifest_loader import load_and_validate_manifest
from src.ingestion.parser import parse_markdown_document

CACHE_FILE = Path("artifacts/corpus_points.json")
logger = logging.getLogger(__name__)


def main() -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_FILE.exists():
        logger.info("Cache file %s already exists.", CACHE_FILE)
        return

    logger.info("Building cached corpus points for evals...")
    t0 = time.time()
    config = IngestionConfig(dense_model_name="BAAI/bge-small-en-v1.5")
    raw_dir = Path(config.rag_data_dir)
    manifest_path = Path(config.rag_manifest_path)
    active_records, _ = load_and_validate_manifest(manifest_path, raw_dir)

    parsed_docs = [parse_markdown_document(raw_dir / m.relative_path, m) for m in active_records]

    chunker = TablePreservingChunker()
    all_chunks = []
    for doc in parsed_docs:
        all_chunks.extend(chunker.chunk_document(doc))

    logger.info("Chunked %d chunks. Embedding with FastEmbed (bge-small + BM25)...", len(all_chunks))
    embedder = FastEmbedAdapter(dense_model_name="BAAI/bge-small-en-v1.5")
    vectorized_chunks = embedder.vectorize_chunks(all_chunks)

    serialized = []
    for idx, vc in enumerate(vectorized_chunks):
        serialized.append({
            "id": idx + 1,
            "dense_vector": vc.dense_vector,
            "sparse_indices": vc.sparse_indices,
            "sparse_values": vc.sparse_values,
            "payload": {
                "chunk_id": vc.chunk.chunk_id,
                "doc_id": vc.chunk.doc_id,
                "text": vc.chunk.text,
                "allowed_groups": [str(g) for g in vc.chunk.allowed_groups],
                "status": str(vc.chunk.status),
                "department": str(vc.chunk.department),
                "classification": str(vc.chunk.classification),
                "chunk_index": vc.chunk.chunk_index,
                "is_tabular": vc.chunk.is_tabular,
            },
        })

    CACHE_FILE.write_text(json.dumps(serialized), encoding="utf-8")
    logger.info("Cached %d points to %s in %.2fs.", len(serialized), CACHE_FILE, time.time() - t0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
