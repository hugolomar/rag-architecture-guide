# Note 05: Adapter Swapping and Composition Root Evolution

**Date:** 2026-11-07 · **Status:** architectural guidance

In accordance with Constitution Article 2 (Hexagonal architecture, Composition Roots, and pure dependency injection) and ADR 0003, this note documents how to evaluate, benchmark, or switch infrastructure adapters (vector stores, embedding providers) without touching domain or pipeline orchestration.

---

## 1. Context and Baseline

The current baseline implementation wires:
- **Embeddings:** `FastEmbedAdapter` (`BAAI/bge-large-en-v1.5` dense + `Qdrant/bm25` sparse) per ADR 0005.
- **Storage:** `QdrantStorageAdapter` (hybrid cosine dense + sparse modifier IDF) per ADR 0006.

In accordance with Article 6 (Simplicity and proportionality), the current Composition Root (`src/ingestion/cli.py`) wires these baseline adapters directly, avoiding speculative abstractions for alternative backends that do not yet exist.

---

## 2. Testing and Benchmarking Alternative Adapters

When testing an alternative storage backend (such as PostgreSQL with `pgvector` or ChromaDB) or an alternative embedder (such as HuggingFace TEI or OpenAI):

### In Automated Tests (Unit and Integration)
The orchestrator (`run_ingestion_pipeline` in `src/ingestion/pipeline.py`) accepts any implementation conforming to `EmbedderPort` and `ChunkStorageWriterPort`. Tests can inject mock, in-memory, or alternative test doubles directly without touching production infrastructure:

```python
results = run_ingestion_pipeline(
    config=config,
    embedder=CustomMockEmbedder(),
    storage=PostgresStorageAdapter(connection_string=test_dsn),
)
```

### In Batch CLI Execution
`src/ingestion/cli.py` is the designated Composition Root. To run experimental batches with an alternative adapter:
1. Implement the new adapter in `src/adapters/` inheriting from the appropriate port (`EmbedderPort` or `ChunkStorageWriterPort`).
2. Instantiate the adapter inside `main()` in `src/ingestion/cli.py` and pass it to `run_ingestion_pipeline()`.
3. The domain orchestrator in `src/ingestion/pipeline.py` requires **zero code modifications**.

---

## 3. Transitioning to Multi-Adapter Configuration (Factory Pattern)

If the roadmap evolves to support multiple production backends toggleable via environment variables (e.g. `VECTOR_STORE_TYPE=qdrant|postgres`):

1. **Add Settings to `IngestionConfig` (`src/ingestion/config.py`):**
   ```python
   vector_store_type: str = Field(default="qdrant", alias="VECTOR_STORE_TYPE")
   embedder_type: str = Field(default="fastembed", alias="EMBEDDER_TYPE")
   ```

2. **Implement Factory Functions in the Composition Root (`src/ingestion/cli.py`):**
   ```python
   def build_storage_adapter(config: IngestionConfig) -> ChunkStorageWriterPort:
       if config.vector_store_type == "postgres":
           from src.adapters.storage.postgres_adapter import PostgresStorageAdapter
           return PostgresStorageAdapter(...)
       from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
       return QdrantStorageAdapter(host=config.qdrant_host, port=config.qdrant_port)
   ```

3. **Keep `pipeline.py` Completely Decoupled:**
   The factory and concrete imports remain strictly inside `cli.py`. `pipeline.py` remains completely unaware of which backend is selected, importing only the abstract port.

