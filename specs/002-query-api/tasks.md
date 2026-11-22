# Tasks: Governed Query API and RAG Runtime

**Input**: Design documents from `specs/002-query-api/` (`spec.md`, `plan.md`, `data-model.md`, `research.md`, `contracts/openapi.yaml`)  
**Prerequisites**: Constitution Articles 1-15, ADRs 0003-0015, ADR 0017, `.agents/rules/`  
**Tests**: Mandatory TDD discipline per Constitution Article 11 and `.agents/rules/testing-standards.md`. Every functional component has an explicit test task that fails first.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Mapped to spec user story (Foundational, US1, US2, US3, US4, Eval, Polish)
- All descriptions reference exact file paths.

---

## Phase 1: Environment Setup & Dependencies

**Purpose**: Initialize project dependencies and lock file for the Runtime Plane.

- [x] T001 Add runtime dependencies (`fastapi>=0.115`, `uvicorn[standard]>=0.32`, `pyjwt[crypto]>=2.9`, `litellm>=1.50`) and test dependency (`httpx>=0.28`) to `pyproject.toml` and regenerate `uv.lock`.
- [x] T002 [P] Verify local ONNX embeddings cache and run `bash scripts/warmup_models.sh` to ensure offline models are primed.

**Checkpoint**: `uv sync` succeeds and offline environment is locked.

---

## Phase 2: Foundational — Domain Modularization & Abstract Ports (ADRs 0003, 0004)

**Purpose**: Establish clean hexagonal domain architecture, modularize domain entities by bounded context, and define abstract ports before implementing any adapters or delivery logic.

> **CRITICAL**: User story implementations cannot begin until domain ports and entities are established.

- [x] T003 [P] [Foundational] Write unit tests in `tests/unit/test_domain_modularization.py` verifying `src/domain/documents.py`, `src/domain/queries.py`, and public re-exports in `src/domain/__init__.py`.
- [x] T004 [Foundational] Refactor existing document models from `src/domain/models.py` into `src/domain/documents.py` (`ManifestRecord`, `CanonicalDocument`, `GovernedChunk`, `VectorizedChunk`).
- [x] T005 [Foundational] Implement query runtime domain entities in `src/domain/queries.py` (`Citation`, `CallerContext`, `RetrievedChunk`, `GenerationResult`).
- [x] T006 [Foundational] Extend closed catalogs in `src/domain/enums.py` with `BehaviorEnum` (`ground_answer`, `deny_access`, `abstain`, `clarify`).
- [x] T007 [Foundational] Expose public domain entities via `src/domain/__init__.py` and establish backward-compatible alias in `src/domain/models.py`.
- [x] T008 [P] [Foundational] Define abstract behavioral ports inheriting from `abc.ABC` in:
  - `src/domain/ports/identity.py`: `TokenValidatorPort`
  - `src/domain/ports/retrieval.py`: `RetrievalPort`
  - `src/domain/ports/generation.py`: `GenerationPort`

**Verification**:
```bash
uv run pytest tests/unit/test_domain_modularization.py tests/unit/test_domain_models.py -m unit
uv run mypy --strict src/domain/
```

---

## Phase 3: User Story 1 — Authenticated & Security-Trimmed Retrieval (Priority: P1) 🎯 MVP

**Goal**: Authenticate callers via OIDC JWT tokens, extract verified identity groups, and retrieve candidate evidence from Qdrant with deterministic pre-inference security trimming (`allowed_groups` ∩ caller groups != ∅, `status != archived`).

### Tests for User Story 1 (Write FIRST — must fail)
- [x] T009 [P] [US1] Write unit tests in `tests/unit/test_oidc_validator.py` verifying JWT signature, issuer, audience, expiration validation, and group claim extraction using fixture keys.
- [x] T010 [P] [US1] Write integration tests in `tests/integration/test_qdrant_retrieval.py` verifying hybrid retrieval scoring and pre-inference security trimming against in-memory Qdrant.

### Implementation for User Story 1
- [x] T011 [US1] Implement `OIDCValidatorAdapter` in `src/adapters/auth/oidc_validator.py` implementing `TokenValidatorPort` via `pyjwt[crypto]`.
- [x] T012 [US1] Implement `QdrantRetrievalAdapter` in `src/adapters/retrieval/qdrant_retrieval.py` implementing `RetrievalPort` using FastEmbed dense/sparse vectorization and Qdrant RRF hybrid search with pre-inference payload filtering.

**Verification**:
```bash
uv run pytest tests/unit/test_oidc_validator.py -m unit
uv run pytest tests/integration/test_qdrant_retrieval.py -m integration
```

---

## Phase 4: User Story 2 — Evidence-Grounded Synthesis & Governed Behaviors (Priority: P1)

**Goal**: Synthesize answers strictly derived from retrieved evidence chunks enclosed within protective context delimiters (`<evidence>...</evidence>`) to defeat prompt injection, classifying responses into governed behaviors.

### Tests for User Story 2 (Write FIRST — must fail)
- [x] T013 [P] [US2] Write unit tests in `tests/unit/test_generation_adapter.py` verifying prompt delimiter construction, injection defense directives, behavior classification, and citation extraction.

### Implementation for User Story 2
- [x] T014 [US2] Implement `LiteLLMGenerationAdapter` in `src/adapters/generation/litellm_adapter.py` implementing `GenerationPort` using in-process LiteLLM (Gemini Flash baseline) with protective context delimiters.
- [x] T015 [US2] Implement deterministic `MockGenerationAdapter` in `src/adapters/generation/mock_adapter.py` implementing `GenerationPort` for offline test suites and deterministic evaluation runs.

**Verification**:
```bash
uv run pytest tests/unit/test_generation_adapter.py -m unit
```

---

## Phase 5: User Story 3 — Application Orchestration & Deterministic Governance (Priority: P2)

**Goal**: Coordinate authentication, vectorization, security-trimmed retrieval, and grounded generation into a unified domain workflow that deterministically resolves `ground_answer`, `deny_access`, `abstain`, and `clarify`.

### Tests for User Story 3 (Write FIRST — must fail)
- [x] T016 [P] [US3] Write unit tests in `tests/unit/test_query_orchestrator.py` verifying orchestrator flow across all 4 behaviors using in-memory mock ports.

### Implementation for User Story 3
- [x] T017 [US3] Implement `QueryOrchestrator` in `src/orchestration/query_orchestrator.py` orchestrating `TokenValidatorPort` -> `RetrievalPort` -> `GenerationPort` -> behavior classification and citation mapping.

**Verification**:
```bash
uv run pytest tests/unit/test_query_orchestrator.py -m unit
```

---

## Phase 6: User Story 4 — Contract-First HTTP API & Observability (Priority: P2)

**Goal**: Expose the FastAPI presentation delivery layer (`POST /query`, `GET /healthz`), enforce OpenAPI 3.1 contract drift verification, propagate OpenTelemetry distributed trace IDs and latency metrics, and implement ASGI lifespan telemetry flushing and credential scrubbing.

### Tests for User Story 4 (Write FIRST — must fail)
- [x] T018 [P] [US4] Write contract drift test in `tests/contract/test_openapi_drift.py` comparing FastAPI's generated schema against `specs/002-query-api/contracts/openapi.yaml`.
- [x] T019 [P] [US4] Write end-to-end integration tests in `tests/integration/test_query_api_e2e.py` testing `POST /query` via FastAPI `TestClient` (asserting status codes `200`, `401`, `422`, `502`, `504`).
- [x] T020 [P] [US4] Write telemetry integration tests in `tests/integration/test_api_telemetry.py` verifying trace ID propagation, latency calculation, and bearer token redaction in logs.

### Implementation for User Story 4
- [x] T021 [US4] Implement HTTP request/response models in `src/api/schemas.py` (`QueryRequest`, `QueryResponse`, `ErrorResponse`).
- [x] T022 [US4] Implement runtime configuration settings in `src/api/config.py` using `pydantic-settings`.
- [x] T023 [US4] Implement dependency injection wiring in `src/api/dependencies.py` acting as Composition Root.
- [x] T024 [US4] Implement HTTP routes in `src/api/routes/query.py` and `src/api/routes/health.py` (`/healthz`).
- [x] T025 [US4] Implement FastAPI application factory and ASGI lifespan in `src/api/main.py` binding `TelemetryManager.flush_and_shutdown()` to server shutdown and attaching credential scrubbing middleware.

**Verification**:
```bash
uv run pytest tests/contract/test_openapi_drift.py -m contract
uv run pytest tests/integration/test_query_api_e2e.py tests/integration/test_api_telemetry.py -m integration
```

---

## Phase 7: Evaluation Suites Integration Gate (Article 9, ADRs 0014, 0015)

**Purpose**: Connect domain ports directly to `evals/conftest.py` without HTTP to pass the formal evaluation suites.

- [x] T026 [Eval] Wire domain `RetrievalPort` and `GenerationPort` into `evals/conftest.py` implementing `retrieve_fn` and `generate_fn`.
- [x] T027 [Eval] Execute local development evaluation suite `evals/runners/test_retrieval_dev.py` and verify all 14 cases pass.
- [x] T028 [Eval] Execute blocking PR validation suite `evals/runners/test_regression_val.py` and verify all 6 cases pass with zero security leaks.

**Verification**:
```bash
uv run pytest evals/runners/test_retrieval_dev.py -m dev
uv run pytest evals/runners/test_regression_val.py -m validation
```

---

## Phase 8: Container Packaging, Orchestration & Quality Gate (ADR 0017, Art. 13)

**Purpose**: Package the Query API into a secure, multi-stage production container and verify full repository quality gates.

- [x] T029 [P] [Polish] Implement multi-stage `docker/Dockerfile.api` following `.agents/rules/container-packaging-standards.md` with non-root security and pre-cached FastEmbed weights.
- [x] T030 [Polish] Update `docker/docker-compose.yml` to orchestrate Qdrant, Ingestion, Keycloak, and Query API services.
- [x] T031 [Polish] Execute complete repository quality gate script `bash scripts/check.sh` (linting, formatting, strict typing, tests).

**Verification**:
```bash
bash scripts/check.sh
```

---

## Dependencies & Execution Order

### Phase Dependencies
1. **Phase 1 (Setup)**: No dependencies.
2. **Phase 2 (Foundational)**: Depends on Phase 1. Blocks all subsequent phases.
3. **Phase 3 (User Story 1)**: Depends on Phase 2. Delivers secure retrieval MVP.
4. **Phase 4 (User Story 2)**: Depends on Phase 2. Can proceed in parallel with Phase 3 adapters.
5. **Phase 5 (User Story 3)**: Depends on Phase 3 and Phase 4. Unifies retrieval and generation.
6. **Phase 6 (User Story 4)**: Depends on Phase 5. Delivers the HTTP API and OpenAPI contract.
7. **Phase 7 (Evaluation Gate)**: Depends on Phase 5 (domain ports).
8. **Phase 8 (Packaging & Polish)**: Depends on Phase 6 and Phase 7.

---

## Implementation Strategy: MVP First

1. **Step 1 (Foundation)**: Complete Phase 1 & 2 -> Pure modular domain and nominal ports ready.
2. **Step 2 (Retrieval MVP)**: Complete Phase 3 -> Test security-trimmed hybrid retrieval against Qdrant.
3. **Step 3 (Generation & Orchestration)**: Complete Phase 4 & 5 -> Full RAG domain pipeline working with mock and real models.
4. **Step 4 (HTTP Delivery & Evals)**: Complete Phase 6 & 7 -> FastAPI API live, OpenAPI drift passing, evaluation suites 100% green.
5. **Step 5 (Packaging & CI Gate)**: Complete Phase 8 -> Dockerfile.api and `scripts/check.sh` passing.
