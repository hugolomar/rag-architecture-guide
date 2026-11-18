# Implementation Plan: Governed Document Ingestion Pipeline

**Branch**: `001-document-ingestion` | **Date**: 2026-11-05 | **Spec**: [specs/001-document-ingestion/spec.md](spec.md)

**Input**: Feature specification from `/specs/001-document-ingestion/spec.md`

## Summary

This feature implements the **Data Plane vertical slice** for the Governed RAG system. It establishes the clean hexagonal **Shared Domain Core** (`src/domain/`), a one-shot batch ingestion pipeline (`src/ingestion/`), vectorization and storage adapters (`src/adapters/` for FastEmbed and Qdrant), spec-driven OpenTelemetry instrumentation, and multi-stage container packaging. 

The pipeline parses Markdown documents from `data/raw/`, validates them against `data/manifest.json` and strict closed catalogs, drops `archived` documents, chunks body text while preserving tables intact, computes dual representations (dense ONNX + sparse BM25), upserts points into Qdrant with governance payloads, and flushes all OpenTelemetry telemetry before exiting with code 0.

---

## Technical Context

**Language/Version**: Python 3.14 (pinned in `.python-version`).

**Primary Dependencies**:
- `pydantic>=2.0` (boundary validation, closed enums, canonical models)
- `fastembed>=0.4` (in-process ONNX dense embeddings and sparse BM25 vectors)
- `qdrant-client>=1.12` (storage adapter, dual vector upsert, payload filtering)
- `opentelemetry-api>=1.28` and `opentelemetry-sdk>=1.28` (structured JSON logging, tracing, metrics)
- `python-frontmatter>=1.1` (Markdown frontmatter extraction)

**Storage**: Qdrant vector database (running locally or in Docker). Single collection with named dense vector (`dense`), named sparse vector (`sparse`), and governance payload (`doc_id`, `allowed_groups`, `status`, `text`).

**Testing**: 
- `pytest>=9.1`, `pytest-cov` (test runner and coverage — conventions in `.agents/rules/testing-standards.md`)
- `import-linter` (architecture boundary enforcement)
- `testcontainers-python` / local Docker (integration tests against real Qdrant)

**Standards Compliance**:
- Testing & Pytest Suite: `.agents/rules/testing-standards.md`
- Telemetry, Logging & Flush: `.agents/rules/telemetry-and-observability.md`
- Domain Modeling & Data Contracts: `.agents/rules/domain-modeling-contracts.md`
- Container Packaging & Docker: `.agents/rules/container-packaging-standards.md`

**Target Platform**: Linux container (multi-stage Dockerfile per `.agents/rules/container-packaging-standards.md`).

**Project Type**: Batch CLI / one-shot ephemeral pipeline (Data Plane) + Shared Domain Library.

**Performance Goals**: Complete ingestion of the 36-document corpus in < 45 seconds on standard CPU; peak batch process memory < 1.2 GB.

**Constraints**:
- Absolute Zero Telemetry Loss: exporters must be flushed and shut down before process exit.
- Fail loud: reject any unknown catalog values or malformed manifest rows before indexing.
- Clean Hexagonal Core: `src/domain/` has zero dependencies on `src/adapters/`, `qdrant_client`, or `fastembed`.

**Scale/Scope**: 36 enterprise documents (synthetic policies and Docker technical documentation), resulting in ~200-400 governed chunks.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article / Principle | Status | Compliance Details in this Plan |
| :--- | :---: | :--- |
| **Article 1 (Python baseline and strict typing)** | **PASS** | Target interpreter is Python 3.14 as specified in `.python-version`. Strict static typing via `mypy --strict`. |
| **Article 2 (Hexagonal Architecture & Composition Roots)** | **PASS** | `src/domain/` is defined as a clean standalone package containing canonical models and enums with zero external imports. Adapters wired strictly in CLI composition root. |
| **Article 3 (Behavioral Ports & Nominal Subtyping)** | **PASS** | Behavioral ports across boundaries are declared as `abc.ABC` with `@abstractmethod`. Adapters explicitly subclass domain ports; duck typing prohibited. |
| **Article 4 (Data Contracts & Boundary Validation)** | **PASS** | Boundary data validated via Pydantic v2 `ManifestRecord` and `CanonicalDocument`. Closed catalogs (`Department`, `Classification`, `LifecycleStatus`, `IdPGroup`) are strict enums. |
| **Article 6 (Single dependency authority)** | **PASS** | Dependencies managed exclusively through `pyproject.toml` and locked in `uv.lock`. |
| **Article 7 (Zero Trust & Security Trimming)** | **PASS** | `archived` documents completely excluded; `current` and `deprecated` retained. `allowed_groups` attached inseparably to each chunk. |
| **Article 10 (Dual written-token and semantic retrieval)** | **PASS** | Dual vectors produced per chunk: dense (meaning) and sparse BM25 (exact written tokens). FastEmbed transforms match query requirements. |
| **Article 11 (Testing Pyramid & Real Infrastructure)** | **PASS** | Test-first approach. Unit tests for domain models, contract tests for `manifest.json` and ports, and integration tests against real Qdrant (no mocks). |
| **Article 12 (Executable Architecture & Quality Gates)** | **PASS** | Enforced by `import-linter` contracts in CI to prevent domain leakage and structural contract tests in `tests/contract/`. |
| **Article 13 (Observability Baseline & Data Hygiene)** | **PASS** | OpenTelemetry SDK emits JSON logs to stdout with `run_id`, stage spans (parse, chunk, embed, index), and metrics. Explicit flush before exit. No sensitive content in telemetry. |
| **Article 14 (Container Packaging & Lifecycle)** | **PASS** | Multi-stage Dockerfile for ingestion. Compose coordinates Qdrant and the batch container. Batch exits with status code 0 and has no healthcheck endpoint. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-document-ingestion/
├── plan.md              # This implementation plan
├── research.md          # Technical research, library choices, and trade-offs
├── data-model.md        # Canonical models, Enums, schemas, and Qdrant payloads
├── quickstart.md        # Local execution, verification commands, and validation steps
├── contracts/           # Boundary contracts (CLI schema, Qdrant collection spec)
│   ├── manifest.schema.json
│   ├── qdrant-collection.json
│   └── ingestion-cli.md
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Ordered task breakdown (created by /speckit-tasks)
```

### Source Code Layout (repository root)

```text
src/
├── domain/                          # Hexagonal Core (Zero external infra dependencies)
│   ├── __init__.py
│   ├── enums.py                     # Closed catalogs: Department, Classification, LifecycleStatus, IdPGroup
│   ├── models.py                    # CanonicalDocument, GovernedChunk
│   ├── manifest.py                  # Pydantic v2 validator for data/manifest.json
│   └── ports/                       # Cross-layer abstract behavioral contracts
│       ├── __init__.py
│       ├── embeddings.py            # abc.ABC: EmbedderPort (dense & sparse generation)
│       └── storage.py               # abc.ABC: ChunkStorageWriterPort (Qdrant writer contract)
│
├── adapters/                        # Outbound Infrastructure Adapters
│   ├── __init__.py
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── fastembed_adapter.py     # Implements EmbedderPort using FastEmbed (ONNX + BM25)
│   ├── storage/
│   │   ├── __init__.py
│   │   └── qdrant_adapter.py        # Implements ChunkStorageWriterPort using qdrant-client
│   └── telemetry/
│       ├── __init__.py
│       └── otel_emitter.py          # OTel tracer, meter, JSON logger & flush lifecycle
│
└── ingestion/                       # Inbound Batch Ingestion Pipeline
    ├── __init__.py
    ├── config.py                    # Pydantic Settings (paths, collection name, model names)
    ├── parser.py                    # Markdown parser (frontmatter extraction)
    ├── chunker.py                   # Strategy contract (DocumentChunker) & table-preserving default (TablePreservingChunker)
    ├── pipeline.py                  # Domain orchestrator workflow (injected ports and chunker strategy)
    └── cli.py                       # Composition root CLI entrypoint (wires concrete adapters & chunker)

tests/
├── unit/                            # Pure domain and logic tests (no network/db)
│   ├── test_domain_models.py        # Validates closed enums, fail loud, chunk inheritance
│   ├── test_manifest_validation.py  # Validates data/manifest.json schema constraints
│   ├── test_markdown_parser.py      # Frontmatter splitting and body extraction
│   ├── test_table_chunker.py        # Verifies table header & row preservation
│   └── test_telemetry.py            # Validates JSON logging, correlation IDs, and data hygiene
│
├── contract/                        # Interface & architectural contract tests
│   ├── test_architecture_contracts.py # import-linter runner (hexagonal boundaries)
│   └── test_manifest_contract.py    # Strict validation of data/manifest.json against real files
│
└── integration/                     # Tests against real dependencies (Qdrant & FastEmbed)
    ├── test_fastembed_adapter.py    # Vector dimension, finiteness, and token recall
    ├── test_qdrant_writer.py        # Point upsert, dual vectors, and payload filters in real Qdrant
    ├── test_telemetry_flush.py      # Verifies OTel tracer attributes, capsys stdout JSON logs, and provider shutdown
    └── test_ingestion_e2e.py        # Complete batch run against sample corpus and Qdrant

docker/
├── Dockerfile.ingestion             # Multi-stage image for batch ingestion
└── docker-compose.yml               # Local orchestration for Qdrant + Ingestion
```

**Structure Decision**: 
Standard single-project hexagonal architecture separating the pure business domain (`src/domain/`) from outbound technology adapters (`src/adapters/`) and the inbound application batch driver (`src/ingestion/`). All cross-layer boundaries inherit from `abc.ABC` behavioral ports.

---

## Complexity Tracking

> **Constitution Compliance**: No violations. All patterns follow ratified ADRs and Constitution v2.0.0.

| Decision / Pattern | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Dual vectorization (Dense + BM25)** | Supports both semantic similarity and exact-token recall (flags, error codes, configuration keys). | Dense-only search fails on exact technical tokens and configuration parameters. |
| **Pluggable DocumentChunker Strategy** | Enables evaluation and swapping of chunking strategies without coupling orchestrator logic to concrete splitting algorithms. | Hardcoding TablePreservingChunker directly into pipeline.py prevents clean dependency injection and A/B benchmarking. |
| **Multi-stage Dockerfile** | Excludes build tools (`uv`, compilers) and development dependencies from the final runtime image. | Single-stage image unnecessarily inflates image size and introduces build-time security attack surface. |
| **Explicit Telemetry Flush** | Ephemeral batch processes terminate immediately upon completion; explicit flush prevents dropped in-flight signals. | Standard default telemetry buffers drop in-flight spans and metrics when the process exits. |
