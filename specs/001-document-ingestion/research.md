# Research & Technical Decisions: Governed Document Ingestion Pipeline

**Feature**: `001-document-ingestion`  
**Date**: 2026-11-05  
**Status**: Completed  

---

## 1. Table-Preserving Markdown Chunking

### Decision
Define an abstract strategy contract `DocumentChunker` and implement a default Markdown structure-aware chunker (`TablePreservingChunker`) that identifies Markdown tables (`| ... |`) and treats each complete table as an indivisible structural block. If a table fits within the target chunk token window (e.g., 500-800 tokens), it is stored as a single chunk with its preceding heading. If an oversized table exceeds the chunk limit, the chunker splits along row boundaries while automatically prepending the table column headers to every continuation chunk.

### Rationale
- Standard character-based or recursive token splitters break tables across arbitrary character limits, separating numerical cells and row items from their column headers.
- Quantitative policies (such as salary bands, SLA response times, and expense limits) lose all relational meaning when a row is detached from its header.
- Prepending headers on oversized table splits ensures that every chunk remains semantically interpretable both for dense embedding models and BM25 token matching.
- Defining `DocumentChunker` as an abstract strategy contract decouples the batch orchestrator (`pipeline.py`) from concrete chunking heuristics, allowing seamless experimentation with alternative chunkers or overlap parameters via dependency injection without code modifications to the ingestion pipeline.

### Alternatives Considered
- **LangChain `MarkdownHeaderTextSplitter`**: Splits by headers only; does not guarantee table integrity or handle table rows specially.
- **Unstructured / Pandoc parser**: Heavy external dependency requiring C/C++ system libraries; violates architectural simplicity and proportionality by inflating the container footprint for basic markdown parsing.
- **Fixed-size text chunking (e.g. 500 chars)**: Severely degrades retrieval on tabular data.

---

## 2. FastEmbed Dense and Sparse Vector Generation

### Decision
Use `fastembed` (version >= 0.4.0) with:
1. **Dense Model**: `BAAI/bge-large-en-v1.5` (1024 dimensions, ONNX runtime) for semantic embeddings.
2. **Sparse Model**: FastEmbed's native sparse BM25 generator (`Qdrant/bm25`) for exact written-token recall.

Vector computation is executed in Python inside `src/adapters/embeddings/fastembed_adapter.py`, which implements the abstract `EmbedderPort`.

### Rationale
- FastEmbed runs lightweight ONNX models on CPU without requiring PyTorch, CUDA, or heavy ML dependencies, aligning with local and CI container constraints.
- FastEmbed includes built-in BM25 sparse vector generation, satisfying dual semantic and exact-token retrieval within a single lightweight library dependency.
- Both dense and sparse vectors can be generated in parallel or pipeline sequence before storage upsert.

### Alternatives Considered
- **Sentence-Transformers + rank_bm25**: Requires PyTorch (1.5GB+ download in Docker) and maintaining two separate libraries for vectorization.
- **Hosted API Embeddings (OpenAI / Voyage)**: Leaks enterprise document content outside boundaries; introduces network latency and external credentials.

---

## 3. Qdrant Storage & Hybrid Collection Architecture

### Decision
Configure a single Qdrant collection (named `governed_docs` or configurable via environment variable `QDRANT_COLLECTION_NAME`) with **Named Vectors**:
- Vector `"dense"`: size 1024, distance `Cosine`.
- Sparse Vector `"sparse"`: index type `sparse`, with modifier `idf`.
- Payload Schema:
  - `doc_id` (keyword, indexed)
  - `allowed_groups` (keyword array, indexed)
  - `status` (keyword, indexed)
  - `department` (keyword)
  - `classification` (keyword)
  - `relative_path` (keyword)
  - `text` (text)

Points are upserted via `qdrant_client.QdrantClient.upsert(collection_name=..., points=...)` in batches (e.g., 50 points per call).

### Rationale
- Named vectors enable storing both dense and sparse representations within a single point struct in Qdrant (ADR 0006).
- Creating payload indexes on `allowed_groups` and `status` enables fast pre-filtering during runtime retrieval, ensuring deterministic zero-trust access control before generative context assembly.
- Qdrant natively manages Reciprocal Rank Fusion (RRF) when querying both vector types simultaneously.

### Alternatives Considered
- **ChromaDB**: Evaluated in ADR 0006; rejected because ChromaDB lacks native sparse BM25 vectors and payload-level group intersection in a single query path.
- **Separate BM25 Engine (Elasticsearch + Vector DB)**: Rejected due to synchronization overhead and operational complexity across dual writes.

---

## 4. Ephemeral Batch OpenTelemetry Instrumentation & Flush Lifecycle

### Decision
Instrument the ingestion process using the official `opentelemetry-sdk`:
1. **Logging**: Structured JSON formatter outputting to `stdout` containing `timestamp`, `level`, `message`, `run_id`, `stage`, and `doc_id`.
2. **Tracing**: `TracerProvider` configured with `BatchSpanProcessor` pointing to `OTLPSpanExporter` (or console exporter in local mode). Stage spans:
   - `ingestion.run` (root span with attribute `run_id`)
   - `ingestion.manifest.validate`
   - `ingestion.document.parse`
   - `ingestion.document.chunk`
   - `ingestion.embeddings.compute`
   - `ingestion.storage.upsert`
3. **Metrics**: Counter for `ingestion.documents.processed`, `ingestion.chunks.created`, and `ingestion.documents.rejected`.
4. **Shutdown Invariant**: Wrapped in a Python `try...finally` block (or `atexit` handler) that calls:
   ```python
   tracer_provider.force_flush()
   tracer_provider.shutdown()
   meter_provider.force_flush()
   meter_provider.shutdown()
   ```

### Rationale
- Ephemeral batch jobs exit as soon as their work completes. Without an explicit flush and shutdown, default background exporter threads are terminated abruptly by the operating system, resulting in dropped spans and lost audit metrics.
- Correlating with `run_id` allows operators to trace an entire batch execution end-to-end in Grafana / Tempo.

### Alternatives Considered
- **Standard Python `logging` without OTel**: Lacks distributed trace correlation and OTLP metric export.
- **Relying on auto-instrumentation**: Ingestion is a custom batch loop without HTTP endpoints; explicit manual SDK instrumentation provides precise stage spans and guarantees the flush lifecycle.

---

## 5. Multi-Stage Dockerfile with Dependency Isolation

### Decision
Construct a multi-stage Dockerfile (`docker/Dockerfile.ingestion`):
- **Stage 1 (Builder)**: Base `python:3.14-slim`. Installs `uv`, copies `pyproject.toml` and `uv.lock`, and runs `uv sync --frozen --no-dev`.
- **Stage 2 (Runtime)**: Base `python:3.14-slim`. Copies the compiled virtual environment from the builder to `/app/.venv`. Pre-downloads or bundles the FastEmbed ONNX model cache into `/root/.cache/fastembed`. Sets `PATH="/app/.venv/bin:$PATH"` and executes `python -m src.ingestion.cli`.
- **Exclusion**: Build tools, compilers, and `uv` are excluded from the runtime stage to minimize image footprint and attack surface.

### Rationale
- Produces a secure, minimal runtime image without compilers or package installers.
- Embedding models pre-cached in the image prevent network downloads at container startup.

### Alternatives Considered
- **Single-stage Dockerfile with `uv run`**: Rejected because executing `uv run` in production containers introduces unnecessary toolchain overhead and startup latency instead of running directly against the compiled environment.
- **Mounting source code dynamically in production**: Good for local dev, but production release requires an immutable, self-contained container image.

