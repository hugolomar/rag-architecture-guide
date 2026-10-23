# ADR 0005: Preprocessing and Embeddings Before Storage

- Status: Proposed
- Date: 2026-10-23

## Context

Notes 01 and 02 define the corpus and the manifest. ADR 0001 separates the Data Plane from the
Runtime Plane. ADR 0003 and ADR 0004 require ports and validated contracts at boundaries.

Retrieval needs two vectors per chunk:

- a dense vector for semantic similarity,
- a sparse lexical vector for written-token recall.

Both vectors must exist before a point is stored, and the same transformations must run at query
time. This ADR defines how vectors are produced and how ingestion runs. It does not choose the
storage engine.

The concrete dense embedding model is still open. Current candidates for local CPU runs are
`Qwen/Qwen3-Embedding-0.6B` and `BAAI/bge-large-en-v1.5`.

## Decision

Build both vectors in Python before storage.

- **Embedding library:** use FastEmbed as the default adapter.
  - Dense vectors use one configured dense model.
  - Sparse lexical vectors use FastEmbed sparse BM25.
- **Query parity:** the query path uses the same library and channel-specific transforms as indexing
  (document embedding for chunks, query embedding for user queries).
- **Ingestion execution model:** ingestion is a one-shot batch process in the Data Plane. It reads
  Markdown plus `data/manifest.json`, merges governance, chunks, computes vectors, writes points,
  flushes/shuts down telemetry exporters, and exits.
- **Model isolation:** changing the dense model requires a new collection and a new indexing run.
  Collection metadata stores model identity and vector dimensions.
- **Acceptance checks:** candidates are rejected when phase-1 development cases miss expected
  semantic documents, or when adapter checks fail (dimension, finite values, query/document path
  separation, stored vector equality with produced vector).

## Rationale

- Producing vectors before storage keeps lexical analysis and embedding choices independent from
  storage-engine selection.
- FastEmbed covers dense and sparse lexical vectors in one adapter, avoiding a second library for
  the lexical channel in the default path.
- One adapter for indexing and query embedding reduces drift between offline and online behavior.
- One-shot ingestion avoids a permanently idle process and isolates batch failures from the API
  process that serves user traffic.
- The existing phase-1 suite already provides deterministic, model-judge-free acceptance checks on
  document retrieval behavior.

## Alternatives Considered

1. **Sentence Transformers as default**
   - Pros: broad model coverage, straightforward GPU usage through PyTorch.
   - Cons: does not provide the chosen lexical sparse BM25 vector in the same library, which adds
     another component in the default path.
   - Rejected as default. It remains valid for experiments when a dense model is not available in
     FastEmbed.

2. **Hosted embedding API**
   - Pros: no local model inference in the query path.
   - Cons: document/query text leaves the system, and an embedding provider is selected early.
   - Rejected.

3. **Ingestion inside the API process or as a resident service**
   - Pros: fewer moving parts.
   - Cons: batch ingestion resource spikes and failures share fate with runtime query handling.
   - Rejected.

4. **Storage-managed lexical analysis**
   - Pros: leverage engine-native text analyzers.
   - Cons: lexical behavior becomes coupled to engine choice and splits dense/sparse responsibilities.
   - Rejected as baseline architecture.

## Consequences

- **Positive:** indexing and query paths share a single vectorization contract.
- **Positive:** batch ingestion lifecycle is explicit and operationally isolated.
- **Negative:** runtime still loads FastEmbed for query embeddings.
- **Negative:** ephemeral jobs require explicit telemetry flush/shutdown before process exit.
- **Boundary:** this ADR does not choose storage engine, final dense model, chunk size, reranker,
  or telemetry backend.
- **Follow-up:** storage ADR must reference this preprocessing decision.
