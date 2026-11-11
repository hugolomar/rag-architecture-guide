---
description: "Task list for Governed Document Ingestion Pipeline implementation"
---

# Tasks: Governed Document Ingestion Pipeline

**Input**: Design documents from `/specs/001-document-ingestion/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)
**Constitution Compliance**: Enforces Constitution v1.0.0 (Articles 1-27), including hexagonal architecture, test-first development, zero-trust trimming, dual-vector indexing, zero telemetry loss, and container packaging.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., `[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency management, and architecture validation tooling

- [X] T001 Configure project dependencies in `pyproject.toml` using uv (`pydantic>=2.0`, `fastembed>=0.4`, `qdrant-client>=1.12`, `opentelemetry-api>=1.28`, `opentelemetry-sdk>=1.28`, `python-frontmatter>=1.1`, `pydantic-settings>=2.0`, dev dependencies `pytest>=9.1`, `pytest-cov`, `import-linter`, `testcontainers`) and lock with `uv lock` per Constitution Article 7
- [X] T002 [P] Create directory structure per implementation plan: `src/domain/ports/`, `src/adapters/embeddings/`, `src/adapters/storage/`, `src/adapters/telemetry/`, `src/ingestion/`, `tests/unit/`, `tests/contract/`, `tests/integration/`, and `docker/`
- [X] T003 [P] Configure architectural boundary enforcement in `.importlinter` to verify Constitution Articles 2, 3, and 19 (ensuring `src.domain` has zero imports from `src.adapters`, `src.ingestion`, or third-party storage/vector libraries)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain contracts, ports, and configuration that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Define closed governance catalog enums in `src/domain/enums.py`: `Department` (values: `"HR"`, `"Engineering"`, `"Security"`, `"Finance"`, `"Legal"`), `Classification` (values: `"public"`, `"internal"`, `"restricted"`), `LifecycleStatus` (values: `"current"`, `"deprecated"`, `"archived"`), and `IdPGroup` (values: `"all-employees"`, `"people-team"`, `"engineering-core"`, `"security-oncall"`, `"leadership"`) per Constitution Article 5
- [X] T005 [P] Define abstract behavioral ports in `src/domain/ports/embeddings.py` (`EmbedderPort` with `abc.ABC` and `@abstractmethod` for dense and sparse vector generation) and `src/domain/ports/storage.py` (`ChunkStorageWriterPort` with `abc.ABC` and `@abstractmethod` for collection initialization and point upsert) per Constitution Article 4
- [X] T006 [P] Define environment and pipeline configuration model in `src/ingestion/config.py` using `pydantic_settings.BaseSettings` for `RAG_DATA_DIR` (default: `"data/raw"`), `RAG_MANIFEST_PATH` (default: `"data/manifest.json"`), `QDRANT_HOST` (default: `"localhost"`), `QDRANT_PORT` (default: `6333`), `QDRANT_COLLECTION_NAME` (default: `"governed_docs"`), `OTEL_EXPORTER_OTLP_ENDPOINT` (default: `"http://localhost:4318"`), `OTEL_SERVICE_NAME` (default: `"rag-ingestion"`), and `LOG_LEVEL` (default: `"INFO"`) per `contracts/ingestion-cli.md`
- [X] T007 [P] Implement architectural contract test in `tests/contract/test_architecture_contracts.py` using `import-linter` to enforce that `src/domain/` has zero infrastructure imports and all adapters inherit directly from `src/domain/ports/`

**Checkpoint**: Foundation ready - domain models, ports, and configuration initialized. User story implementation can now begin.

---

## Phase 3: User Story 1 - Enforce Governance and Manifest Access Rules (Priority: P1) 🎯 MVP

**Goal**: Validate manifest records against closed governance catalogs, fail loud on invalid records or uncataloged files, drop `archived` documents, and produce canonical documents retaining `current` and `deprecated` metadata.

**Independent Test**: Run validation stage against valid, malformed, and out-of-catalog manifest records; verify valid documents proceed, invalid fail loud, and archived documents are completely excluded.

### Tests for User Story 1 (Test-First per Constitution Article 16) ⚠️

- [X] T008 [P] [US1] Create unit tests for domain enums and validation rules in `tests/unit/test_domain_models.py` verifying fail-loud behavior on invalid catalog values and strict enum containment
- [X] T009 [P] [US1] Create contract test for `data/manifest.json` against `specs/001-document-ingestion/contracts/manifest.schema.json` in `tests/contract/test_manifest_contract.py` verifying real corpus manifest compliance
- [X] T010 [P] [US1] Create unit tests for manifest parsing and fail-loud validation in `tests/unit/test_manifest_validation.py` verifying schema validation, missing file detection, and exclusion of `status == "archived"`
- [X] T011 [P] [US1] Create unit tests for Markdown frontmatter parsing and body extraction in `tests/unit/test_markdown_parser.py`

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement `ManifestRecord` and `CanonicalDocument` models in `src/domain/models.py` with verbatim field constraints from `data-model.md` (`doc_id` regex `^DOC-[A-Z]{3,4}-[0-9]{3}$`, required `relative_path`, `department: Department`, `allowed_groups: list[IdPGroup]` with `minItems: 1`, `classification: Classification`, `status: LifecycleStatus`, `title: str`, `content: str`, `keywords: list[str]` default empty list)
- [X] T013 [US1] Implement manifest loader and lifecycle filter in `src/domain/manifest.py` validating `data/manifest.json` against `ManifestRecord`, dropping documents where `status == LifecycleStatus.ARCHIVED`, and raising explicit errors on uncataloged files or invalid values (depends on T012)
- [X] T014 [US1] Implement Markdown parser in `src/ingestion/parser.py` using `python-frontmatter` to separate YAML frontmatter from Markdown body and construct `CanonicalDocument` instances for all active manifest entries (depends on T012, T013)

**Checkpoint**: User Story 1 complete and independently testable. Run `pytest tests/unit/test_domain_models.py tests/unit/test_manifest_validation.py tests/unit/test_markdown_parser.py tests/contract/test_manifest_contract.py`.

---

## Phase 4: User Story 2 - Structure-Preserving Chunking & Dual-Representation Indexing (Priority: P1)

**Goal**: Chunk Markdown content preserving tables intact (repeating headers on oversized row splits), attach inherited governance metadata (`doc_id`, `allowed_groups`, `status`) to all chunks, generate dual representations (dense ONNX embeddings + sparse BM25 token weights), and upsert points to Qdrant collection `governed_docs`.

**Independent Test**: Run chunker and indexing engine against Markdown documents containing complex tables and technical flags; verify table rows preserve header context, chunks inherit parent governance metadata, and both dense and sparse vectors are stored with payloads in Qdrant.

### Tests for User Story 2 (Test-First per Constitution Article 16) ⚠️

- [X] T015 [P] [US2] Create unit tests for table-preserving chunking in `tests/unit/test_table_chunker.py` verifying that Markdown tables remain intact in single chunks and oversized tables split along row boundaries with repeated headers
- [X] T016 [P] [US2] Create integration tests for FastEmbed adapter in `tests/integration/test_fastembed_adapter.py` verifying 1024-dim dense vector generation (`BAAI/bge-large-en-v1.5`), sparse BM25 indices/values (`Qdrant/bm25`), and finite float values
- [X] T017 [P] [US2] Create integration tests for Qdrant storage adapter in `tests/integration/test_qdrant_writer.py` against running Qdrant instance verifying collection initialization per `contracts/qdrant-collection.json`, point upsert with dual vectors, payload filtering by `allowed_groups` and `status`, and zero `archived` points

### Implementation for User Story 2

- [X] T018 [P] [US2] Implement `GovernedChunk` and `VectorizedChunk` models in `src/domain/models.py` with verbatim field constraints from `data-model.md` (`chunk_id` format `{doc_id}#c{chunk_index}`, `doc_id: str`, `allowed_groups: list[IdPGroup]`, `status: LifecycleStatus`, `department: Department`, `classification: Classification`, `chunk_index: int`, `text: str`, `is_tabular: bool` default `False`, `dense_vector: list[float]` 1024-dim, `sparse_indices: list[int]`, `sparse_values: list[float]`)
- [X] T019 [US2] Implement strategy contract `DocumentChunker` and default `TablePreservingChunker` in `src/ingestion/chunker.py` identifying Markdown table blocks (`| ... |`), keeping tables within 500-800 token windows intact, splitting oversized tables across rows while repeating column headers, and assigning inherited governance metadata to each `GovernedChunk` (depends on T018)
- [X] T020 [US2] Implement `FastEmbedAdapter` inheriting from `EmbedderPort` in `src/adapters/embeddings/fastembed_adapter.py` using `fastembed` TextEmbedding (`BAAI/bge-large-en-v1.5`, 1024 dims) and SparseTextEmbedding (`Qdrant/bm25`) to produce `VectorizedChunk` instances (depends on T005, T018)
- [X] T021 [US2] Implement `QdrantStorageAdapter` inheriting from `ChunkStorageWriterPort` in `src/adapters/storage/qdrant_adapter.py` creating the collection per `contracts/qdrant-collection.json` with named vectors (`dense` 1024 Cosine, `sparse` idf) and payload keyword indexes (`doc_id`, `allowed_groups`, `status`, `department`, `classification`), and batch upserting points with governance payloads (depends on T005, T018)
- [X] T022 [US2] Integrate parsing, pluggable chunking (`DocumentChunker`), embedding, and storage indexing via dependency injection in `src/ingestion/pipeline.py` to process active canonical documents into Qdrant (depends on T014, T019, T020, T021)

**Checkpoint**: User Stories 1 and 2 complete and independently testable. Run `pytest tests/unit/test_table_chunker.py tests/integration/test_fastembed_adapter.py tests/integration/test_qdrant_writer.py`.

---

## Phase 5: User Story 3 - Spec-Driven Batch Observability & Telemetry Flush (Priority: P2)

**Goal**: Emit structured JSON logs on stdout with `run_id`, stage spans (`ingestion.run`, `ingestion.manifest.validate`, `ingestion.document.parse`, `ingestion.document.chunk`, `ingestion.embeddings.compute`, `ingestion.storage.upsert`), progress counters, scrub confidential content, and guarantee explicit telemetry flush before termination.

**Independent Test**: Execute batch run with telemetry listener or stdout inspection; confirm structured JSON logs carry `run_id`, all stage spans close, counters match processed totals, and exporters flush cleanly prior to process exit code 0 (or non-zero on error).

### Tests for User Story 3 (Test-First per Constitution Article 16) ⚠️

- [X] T023 [P] [US3] Create unit tests for structured JSON logging and sensitive data scrubbing in `tests/unit/test_telemetry.py` verifying newline-delimited JSON on stdout with `run_id`, `stage`, `level`, `timestamp`, and ensuring document text/secrets are masked
- [X] T024 [P] [US3] Create integration tests for OTel tracer, stage spans, metric counters, and flush lifecycle in `tests/integration/test_telemetry_flush.py` verifying that `force_flush()` and `shutdown()` are called before process exit

### Implementation for User Story 3

- [X] T025 [P] [US3] Implement OpenTelemetry adapter and structured JSON log formatter in `src/adapters/telemetry/otel_emitter.py` generating a unique `run_id`, initializing `TracerProvider` with stage spans, `MeterProvider` with progress counters (`ingestion.documents.processed`, `ingestion.chunks.created`, `ingestion.documents.rejected`), and explicit `flush_and_shutdown()` method per Constitution Articles 20 and 22
- [X] T026 [US3] Integrate stage spans and metric counters into `src/ingestion/pipeline.py` wrapping manifest validation, parsing, chunking, embedding, and storage upsert within child spans of root span `ingestion.run` (depends on T022, T025)
- [X] T027 [US3] Implement CLI composition root entrypoint, exit code handling (0: Success, 1: Schema Failure, 2: File Mismatch, 3: Store Failure, 4: Telemetry Failure), and guaranteed `finally` telemetry flush in `src/ingestion/cli.py` per `contracts/ingestion-cli.md` (depends on T025, T026)

**Checkpoint**: User Story 3 complete. Batch execution logs structured JSON with `run_id` and flushes all spans/metrics before process termination.

---

## Phase 6: User Story 4 - Single-Command Containerized Deployment (Priority: P3)

**Goal**: Package the ingestion pipeline into a multi-stage container image (`docker/Dockerfile.ingestion`), excluding build tools (`uv`) from the runtime image, and orchestrate with Qdrant via `docker/docker-compose.yml` so that a single command starts Qdrant, executes one-shot ingestion, and exits with code 0.

**Independent Test**: Execute container orchestration command in a clean environment; verify storage starts, one-shot ingestion container runs to completion, populates collection, and exits with code 0 while Qdrant remains healthy.

### Tests for User Story 4 (Test-First per Constitution Article 16) ⚠️

- [X] T028 [P] [US4] Create end-to-end integration test in `tests/integration/test_ingestion_e2e.py` executing the complete batch pipeline from raw files to populated Qdrant collection, validating point counts, dual vector shapes, payload metadata, and zero archived documents

### Implementation for User Story 4

- [X] T029 [P] [US4] Create multi-stage containerfile in `docker/Dockerfile.ingestion` with builder stage running `uv sync --frozen --no-dev` and runtime stage based on `python:3.14-slim` copying `/app/.venv`, pre-caching FastEmbed models into `/root/.cache/fastembed`, and executing directly with `python -m src.ingestion.cli` without `uv` per Constitution Article 26
- [X] T030 [US4] Create container orchestration in `docker/docker-compose.yml` declaring Qdrant service with healthcheck and one-shot `ingestion` service mounting `data/` and passing environment variables per `contracts/ingestion-cli.md` and Constitution Article 27
- [X] T031 [US4] Validate containerized batch execution and zero-archived count against running Qdrant service following `specs/001-document-ingestion/quickstart.md` (depends on T029, T030)

**Checkpoint**: User Story 4 complete. Full stack runs reproducibly via `docker compose -f docker/docker-compose.yml run --rm ingestion`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation compliance, complete test suite execution, and corpus validation

- [X] T032 [P] Validate documentation and PEP 257 Google-style docstrings across `src/domain/`, `src/adapters/`, and `src/ingestion/` per Constitution Article 23
- [X] T033 [P] Execute full test suite (`pytest tests/unit tests/contract tests/integration -v --cov=src`) and verify 100% pass rate
- [X] T034 Run full end-to-end validation against the 36-document corpus following `specs/001-document-ingestion/quickstart.md` verifying > 300 points indexed, dual vectors present, and exactly 0 `archived` points in Qdrant

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories. 🎯 MVP.
  - **User Story 2 (P1)**: Depends on User Story 1 domain models and parsing components.
  - **User Story 3 (P2)**: Depends on User Story 2 pipeline to wrap pipeline stages with telemetry and wire in CLI.
  - **User Story 4 (P3)**: Depends on User Story 3 CLI and exit codes to package into container.
- **Polish (Phase 7)**: Depends on all user stories being complete.

### User Story Dependencies

```mermaid
flowchart TD
    Setup["Phase 1: Setup"] --> Foundational["Phase 2: Foundational (Enums, Ports, Config)"]
    Foundational --> US1["Phase 3: User Story 1 (Governance & Manifest Validation)"]
    US1 --> US2["Phase 4: User Story 2 (Chunking & Dual Indexing)"]
    US2 --> US3["Phase 5: User Story 3 (Observability & Telemetry Flush)"]
    US3 --> US4["Phase 6: User Story 4 (Container Packaging & Compose)"]
    US4 --> Polish["Phase 7: Polish & End-to-End Validation"]
```

### Within Each User Story

- Tests MUST be written first and fail before implementation (Constitution Article 16).
- Abstract ports and domain models before adapter implementations.
- Adapters before orchestrator pipeline integration.
- Story complete and verified before moving to next priority.

### Parallel Opportunities

- **Phase 1**: `T002` (directory structure) and `T003` (import-linter config) can run in parallel after `T001`.
- **Phase 2**: `T004` (enums), `T005` (ports), `T006` (config), and `T007` (contract test) can all run in parallel.
- **Phase 3 (US1)**: Test tasks `T008`, `T009`, `T010`, `T011` can all run in parallel. `T012` (models) can be written in parallel with tests.
- **Phase 4 (US2)**: Test tasks `T015`, `T016`, `T017` and model task `T018` can all run in parallel. Adapters `T020` (FastEmbed) and `T021` (Qdrant) can run in parallel once ports are ready.
- **Phase 5 (US3)**: Test tasks `T023`, `T024` and adapter task `T025` can run in parallel.
- **Phase 6 (US4)**: Test `T028` and Dockerfile `T029` can run in parallel.
- **Phase 7**: Documentation `T032` and test suite execution `T033` can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all test creation for User Story 1 in parallel:
Task T008: "Create unit tests for domain enums and validation rules in tests/unit/test_domain_models.py"
Task T009: "Create contract test for data/manifest.json against specs/.../contracts/manifest.schema.json in tests/contract/test_manifest_contract.py"
Task T010: "Create unit tests for manifest parsing and fail-loud validation in tests/unit/test_manifest_validation.py"
Task T011: "Create unit tests for Markdown frontmatter parsing and body extraction in tests/unit/test_markdown_parser.py"

# Launch models implementation for User Story 1 in parallel:
Task T012: "Implement ManifestRecord and CanonicalDocument models in src/domain/models.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch test creation and models for User Story 2 in parallel:
Task T015: "Create unit tests for table-preserving chunking in tests/unit/test_table_chunker.py"
Task T016: "Create integration tests for FastEmbed adapter in tests/integration/test_fastembed_adapter.py"
Task T017: "Create integration tests for Qdrant storage adapter in tests/integration/test_qdrant_writer.py"
Task T018: "Implement GovernedChunk and VectorizedChunk models in src/domain/models.py"

# Launch adapters implementation in parallel:
Task T020: "Implement FastEmbedAdapter in src/adapters/embeddings/fastembed_adapter.py"
Task T021: "Implement QdrantStorageAdapter in src/adapters/storage/qdrant_adapter.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001` - `T003`).
2. Complete Phase 2: Foundational (`T004` - `T007`).
3. Complete Phase 3: User Story 1 (`T008` - `T014`).
4. **STOP and VALIDATE**: Verify manifest validation, fail-loud behavior on invalid categories, and exclusion of `archived` files against the real `data/manifest.json`.

### Incremental Delivery

1. **Increment 1 (Foundation & MVP)**: Setup + Foundational + User Story 1. Governance taxonomy and canonical document models validated.
2. **Increment 2 (Core Data Plane)**: Add User Story 2. Table-preserving chunking, FastEmbed dual vectors (BGE dense + BM25 sparse), and Qdrant persistence fully operational.
3. **Increment 3 (Production Observability)**: Add User Story 3. Structured JSON logging with `run_id`, stage spans, progress metrics, and zero-telemetry-loss flush on exit.
4. **Increment 4 (Containerization & Release)**: Add User Story 4 + Polish. Multi-stage container image, Docker Compose orchestration, and validation against the 36-document corpus per `quickstart.md`.

---

## Notes

- Every task strictly adheres to the format `- [ ] [TaskID] [P?] [Story?] Description with file path`.
- `[P]` tasks target different files with no uncompleted dependencies.
- `[Story]` labels (`[US1]`, `[US2]`, `[US3]`, `[US4]`) are restricted exclusively to user story phases.
- Field constraints and closed catalogs are quoted verbatim from `data-model.md`.
- All tests are written test-first per Constitution Article 16.

