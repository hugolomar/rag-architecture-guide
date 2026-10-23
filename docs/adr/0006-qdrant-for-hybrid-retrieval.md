# ADR 0006: Qdrant for Hybrid Retrieval and Vector Storage

- Status: Accepted
- Date: 2026-10-22

## Context

The project defines an evaluation-first governed RAG system (notes 01-03). Retrieval must satisfy
both semantic relevance and exact-token recall, while enforcing deterministic access control and
lifecycle rules before generation.

ADR 0005 defines that dense and sparse vectors are built in Python before storage. Therefore,
storage selection is evaluated on hybrid query execution, filtering behavior, and operational fit,
not on engine-native tokenization or stemming.

Three requirements drive the storage decision:

1. **Hybrid retrieval:** the system needs dense semantic retrieval and lexical retrieval in the same
   runtime path.
2. **Deterministic pre-inference filtering:** each chunk must carry governance metadata (`doc_id`,
   `allowed_groups`, `status`). Retrieval must apply group and lifecycle filters before any chunk
   reaches generation.
3. **Operational simplicity:** avoid maintaining separate stores and custom synchronization logic
   between dense vectors, lexical indices, and metadata filters.

The alternatives evaluated were Qdrant, ChromaDB, PostgreSQL with `pgvector`, and split designs
using separate vector and search engines.

## Decision

Use **Qdrant** as the retrieval storage engine.

- Store dense vectors, sparse vectors, and governance payload in the same point.
- Run dense prefetch, sparse prefetch, and fusion in one query path.
- Apply payload filters for `allowed_groups` and lifecycle `status` before candidate chunks are
  returned to orchestration.
- Keep retrieval behind the domain retrieval port (ADR 0003 and ADR 0004), so orchestration and
  evaluation harness depend on port contracts, not Qdrant client types.

## Rationale

- Qdrant supports dense+sparse retrieval plus payload filtering in one engine and one query path.
- Access and lifecycle must apply to both channels together. In Qdrant, dense vector, sparse
  vector, and governance payload are stored and filtered together.
- A two-engine design moves synchronization risk to application code and increases leakage/staleness
  risk when ACL or lifecycle changes are not mirrored exactly.

## Alternatives Considered

1. **ChromaDB + external lexical index**
   - Pros: simple local start for vector-only retrieval.
   - Cons: lexical retrieval and fusion orchestration move to application code.
   - Rejected for the hybrid-governed target architecture.

2. **PostgreSQL + `pgvector`**
   - Pros: mature transactional platform and familiar operational practices.
   - Cons: hybrid dense+sparse retrieval still requires additional lexical indexing and fusion logic
     in application adapters.
   - Rejected for this retrieval layer iteration.

3. **Vector-only retrieval**
   - Pros: smallest implementation surface.
   - Cons: does not cover token-critical retrieval behavior.
   - Rejected.

4. **Two fully separate engines (vector DB + search engine)**
   - Examples considered: Qdrant + Elasticsearch, Qdrant + OpenSearch, PostgreSQL+`pgvector` +
     Elasticsearch/OpenSearch.
   - Pros: independent lexical scaling and rich search-engine analyzer pipelines.
   - Cons: dual writes, dual filters, and result fusion increase coupling and synchronization risk.
   - Rejected for this system.

## Consequences

- **Positive:** less custom fusion/synchronization code in application layer.
- **Positive:** deterministic filtering before generation sees evidence.
- **Negative:** client-server dependency instead of in-process-only store.
- **Negative:** more explicit collection design (dense vectors, sparse vectors, payload indexes).
- **Boundary note:** this ADR chooses the retrieval engine. It does not choose tokenizer rules,
  embedding model, model provider, or reranking strategy.
- **Follow-up:** implement a Qdrant retrieval adapter behind the domain retrieval port and keep the
  harness-facing retrieval signature stable (`retrieve_fn(query, user_id, top_k=5)`).
