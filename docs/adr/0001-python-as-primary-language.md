# ADR 0001: Python as the Primary Language for Backend and Data Plane

- Status: Accepted
- Date: 2026-10-20

## Context

This project builds an enterprise RAG system that must orchestrate document ingestion, chunking,
embedding generation, retrieval, and HTTP runtime orchestration.

In many corporate environments, Java and C# are default backend choices due to strict static
typing, mature dependency injection containers, and strong compile-time guarantees for component
integration.

However, modern AI and retrieval tooling is most complete in Python. Choosing a different primary
language would require wrappers, sidecar services, or reimplementation of core data and model
integration paths.

## Decision

Use Python as the primary language for both:

- the Data Plane (ingestion and indexing),
- the Runtime Plane (retrieval orchestration and stateless HTTP backend, via FastAPI).

TypeScript/Node.js may still be used for a decoupled frontend or experience layer, but not as the
core language for ingestion and retrieval orchestration in this project.

## Rationale

- Python provides first-class support for document processing and extraction tooling commonly used
  in RAG systems (for example, structured parsing and PDF/text extraction stacks).
- Python is the reference ecosystem for embedding and model integration (Hugging Face, PyTorch,
  and related libraries).
- Vector and lexical retrieval components used in early iterations have direct Python support
  (for example, local vector indexes and BM25 libraries), reducing glue code.
- FastAPI enables clean HTTP decoupling, so the RAG engine can run as an independent stateless API
  service.

## Alternatives Considered

1. **Java / C# as the primary language**
   - Pros: strict compile-time type safety; mature IoC and enterprise runtime patterns.
   - Cons: weaker first-class integration with current AI/RAG tooling; higher integration overhead.
   - Rejected as the primary language for this project stage.

2. **TypeScript / Node.js as the primary language**
   - Pros: strong async model; good type safety across frontend/backend boundaries.
   - Cons: less suitable ecosystem depth for ingestion-heavy and model-centric RAG workloads.
   - Rejected as the primary language for this project stage.

3. **Polyglot core from day one**
   - Pros: each component can use its "best" language.
   - Cons: operational complexity and interface friction too early for the current evaluation-first
     phase.
   - Deferred.

## Consequences

- **Positive:** direct access to state-of-the-art AI and retrieval tooling with minimal adaptation
  layers; faster iteration in ingestion and retrieval experiments.
- **Negative:** dynamic typing increases the risk of runtime integration errors if boundaries are
  weakly defined.
- **Mitigation:** enforce explicit dependency boundaries, typed interfaces, and runtime validation
  of external/internal payloads (for example with Pydantic models). A dedicated ADR will codify the
  strict domain modeling and dependency rules.
