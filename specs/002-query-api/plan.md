# Implementation Plan: Governed Query API and RAG Runtime

**Branch**: `002-query-api` | **Date**: 2026-11-21 | **Spec**: [specs/002-query-api/spec.md](spec.md)

**Input**: Feature specification from `/specs/002-query-api/spec.md`

## Summary

This feature implements the **Runtime Plane (Stage B)** of the Governed RAG system. It exposes a secure, observable, contract-first HTTP service that allows authenticated enterprise callers to execute natural language queries against the governed knowledge base.

The runtime enforces Zero-Trust security at the perimeter: inbound requests must supply an OIDC Bearer token validated via Keycloak/JWKS, extracting authoritative subject identity (`user_id`) and group claims (`groups`). It vectorizes queries using dual dense (`bge-small`) and sparse (`bm25`) FastEmbed representations matching the ingestion pipeline, performs hybrid retrieval in Qdrant with deterministic pre-inference security trimming (`allowed_groups ∩ caller.groups != ∅` and `status != archived`), grounds generation via in-process LiteLLM (Gemini Flash baseline) within protective prompt delimiters, classifies outcomes into governed behaviors (`ground_answer`, `deny_access`, `abstain`, `clarify`), and propagates OpenTelemetry distributed traces and latency metrics under a strict 10-second budget.

---

## Technical Context

**Language/Version**: Python 3.14 (pinned in `.python-version` per Article 1).

**Primary Dependencies**:
- `fastapi>=0.115` & `uvicorn[standard]>=0.32` (HTTP delivery and composition root)
- `pydantic>=2.0` & `pydantic-settings>=2.0` (strict boundary validation and settings)
- `pyjwt[crypto]>=2.9` (OIDC bearer token validation and JWKS handling)
- `litellm>=1.50` (in-process LLM generation adapter)
- `fastembed>=0.4` (in-process dense/sparse query vectorization matching ingestion)
- `qdrant-client>=1.12` (hybrid retrieval with payload filters)
- `opentelemetry-api>=1.28` & `opentelemetry-sdk>=1.28` (distributed tracing, RED metrics, audit logging)

**Storage**: Qdrant vector database (running locally or in Docker). Searches the governed collection populated in Stage A with pre-inference filtering on `allowed_groups` and `status`.

**Testing & Standards Compliance**:
- Testing Pyramid: `.agents/rules/testing-standards.md` (`pytest>=9.1.1`, unit, contract, integration tiers)
- Evaluation Harness: `evals/harness.py`, `evals/runners/test_retrieval_dev.py`, `test_regression_val.py` (ADRs 0014, 0015)
- Telemetry & Logging: `.agents/rules/telemetry-and-observability.md` (clean flush lifecycle, credential scrubbing)
- Domain Modeling: `.agents/rules/domain-modeling-contracts.md` (Pydantic v2 strict models, closed `StrEnum`)
- Container Packaging: `.agents/rules/container-packaging-standards.md` (multi-stage `Dockerfile.api`, non-root)

**Target Platform**: Linux container (`Dockerfile.api`) orchestrated via Docker Compose alongside Qdrant and Keycloak.

**Project Type**: Synchronous/Asynchronous Web Service (FastAPI) + Hexagonal Shared Domain Extension.

**Performance Goals**: 95% of queries complete in < 3.0 seconds; 100% of transactions terminate within the 10.0-second timeout ceiling.

**Constraints**:
- Zero security leaks: prohibited documents must never cross the retrieval boundary into LLM context.
- Contract-First: `contracts/openapi.yaml` is the single source of truth; zero drift against FastAPI schema.
- Hermetic test isolation: tests must run without internet access, utilizing local cached models and token fixtures.
- Hexagonal core purity: `src/domain/` has zero framework/SDK imports.

**Scale/Scope**: Support concurrent interactive queries against the 36-document corpus and pass all 14 `dev_set` cases and 6 blocking `val_set` evaluation cases.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article / Principle | Status | Compliance Details in this Plan |
| :--- | :---: | :--- |
| **Article 1 (Python baseline and strict typing)** | **PASS** | Python 3.14 pinned. Strict static type analysis (`mypy --strict`) enforced across all API, domain, and adapter code. |
| **Article 2 (Hexagonal Architecture & Composition Roots)** | **PASS** | Domain core (`src/domain/`) remains pure with zero external imports. Abstract ports defined in `src/domain/ports/`. FastAPI routes in `src/api/` act as Composition Root. |
| **Article 3 (Behavioral Ports & Nominal Subtyping)** | **PASS** | Ports are defined as `abc.ABC` with `@abstractmethod` (`RetrievalPort`, `GenerationPort`, `TokenValidatorPort`). Adapters inherit nominally. |
| **Article 4 (Data Contracts & Boundary Validation)** | **PASS** | Pydantic v2 models with `extra="forbid"`. Closed enums (`BehaviorEnum`). Access granted solely by intersection of caller groups with `allowed_groups`. |
| **Article 6 (Single dependency authority)** | **PASS** | Dependencies managed exclusively through `pyproject.toml` and locked in `uv.lock`. |
| **Article 7 (Zero-Trust & Deterministic Trimming)** | **PASS** | Identity resolved from OIDC token claims (`sub`, `groups`). Qdrant filters by `allowed_groups` and excludes `archived` before generation. Context isolated in delimiters against prompt injection. |
| **Article 8 (Secrets stay out of the tree)** | **PASS** | All API keys and tokens injected via environment variables; bearer tokens and credentials redacted from logs and traces. |
| **Article 9 (The suites are the specification)** | **PASS** | Pipeline evaluates against `evals/suites/dev_set.json` and `val_set.json`. Zero-leak gate: any prohibited document or keyword is a hard failure. Responses strictly adhere to 4 behaviors. |
| **Article 10 (Dual written-token and semantic retrieval)** | **PASS** | Dense (`bge-small`) and sparse (`bm25`) vectorization reused from FastEmbed adapter matching ingestion representations. |
| **Article 11 (Testing pyramid and test-first development)** | **PASS** | Complete testing pyramid: unit tests (isolated logic), contract tests (OpenAPI drift), integration tests (FastAPI TestClient), and evaluation runner tests. |
| **Article 12 (Observability Baseline & Data Hygiene)** | **PASS** | OpenTelemetry tracer/meter integrated into API. Trace ID and latency returned in response payload. Credential scrubbing enforced. |
| **Article 13 (AI Observability & Prompt Governance)** | **PASS** | Prompts governed with protective delimiters (`<evidence>...</evidence>`). System directives isolate reference data from commands. |
| **Article 14 (Evaluation Governance & Quality Gates)** | **PASS** | Multi-gate policy: `dev_set` for development, `val_set` blocking PR gate. Hard-blocking criteria for security leaks and behavior mismatches. |
| **Article 15 (Evaluation Stack & Tooling Boundaries)** | **PASS** | Phase 1 retrieval scored deterministically via pytest and harness (no LLM judge); Phase 2 semantic metrics scored via RAGAS. |
| **Article 17 (Container Packaging & Lifecycle)** | **PASS** | Multi-stage `Dockerfile.api` with non-root user and healthcheck endpoint (`/healthz`). |

---

## Project Structure

### Documentation (this feature)

```text
specs/002-query-api/
├── plan.md              # This implementation plan
├── research.md          # Technical research, architecture decisions, and alternatives
├── data-model.md        # Canonical domain models, schemas, and abstract ports
├── quickstart.md        # Local execution, verification commands, and test suites
├── contracts/           # Boundary contracts
│   └── openapi.yaml     # Canonical OpenAPI 3.1.0 contract source of truth
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Ordered task breakdown (created by /speckit-tasks)
```

### Source Code Layout (repository root)

```text
src/
├── domain/                          # Hexagonal Domain Core (Pure Python)
│   ├── __init__.py                  # Public facade re-exporting all domain entities
│   ├── enums.py                     # Closed catalogs: Department, Classification, LifecycleStatus, IdPGroup, BehaviorEnum
│   ├── exceptions.py                # Domain and infrastructure exception hierarchy
│   ├── documents.py                 # Document/Ingestion entities: ManifestRecord, CanonicalDocument, GovernedChunk, VectorizedChunk
│   ├── queries.py                   # Query runtime entities: Citation, CallerContext, RetrievedChunk, GenerationResult
│   └── ports/                       # Abstract Ports (abc.ABC)
│       ├── retrieval.py             # RetrievalPort: retrieve(query, caller_groups, top_k)
│       ├── generation.py            # GenerationPort: generate(query, context, user_id)
│       └── identity.py              # TokenValidatorPort: validate_token(token)
│
├── adapters/                        # Outbound Infrastructure Adapters
│   ├── auth/                        # Identity & Token Adapters
│   │   ├── __init__.py
│   │   └── oidc_validator.py        # PyJWT OIDC validator implementing TokenValidatorPort
│   ├── retrieval/                   # Retrieval Adapters
│   │   ├── __init__.py
│   │   └── qdrant_retrieval.py      # Qdrant hybrid retrieval implementing RetrievalPort
│   ├── generation/                  # LLM Generation Adapters
│   │   ├── __init__.py
│   │   ├── litellm_adapter.py       # LiteLLM Gemini Flash implementing GenerationPort
│   │   └── mock_adapter.py          # Deterministic MockGenerationAdapter for tests/evals
│   ├── embeddings/                  # (Reused from Stage A)
│   │   └── fastembed_adapter.py
│   ├── storage/                     # (Reused from Stage A)
│   │   └── qdrant_adapter.py
│   └── telemetry/                   # (Reused from Stage A)
│       └── otel_emitter.py          # TelemetryManager with flush lifecycle
│
├── api/                             # Inbound Presentation Delivery Layer (Composition Root)
│   ├── __init__.py
│   ├── main.py                      # FastAPI application factory, lifespan, and CORS/middlewares
│   ├── config.py                    # API Pydantic Settings (OIDC issuer, timeout, model, collection)
│   ├── schemas.py                   # HTTP Request/Response Pydantic schemas (QueryRequest, QueryResponse)
│   ├── dependencies.py              # Dependency injection providers for TokenValidator, Retrieval, Generation
│   └── routes/
│       ├── __init__.py
│       ├── health.py                # GET /healthz liveness/readiness endpoint
│       └── query.py                 # POST /query endpoint orchestrating the pipeline
│
└── orchestration/                   # Application Service Layer
    ├── __init__.py
    └── query_orchestrator.py        # QueryOrchestrator: coordinates retrieval -> generation -> behavior classification

tests/
├── unit/                            # Pure unit tests (isolated, fast, no I/O)
│   ├── test_query_domain.py         # Validates domain models, BehaviorEnum, Citation
│   ├── test_query_orchestrator.py   # Orchestrator logic with Mock ports (deny, abstain, ground, clarify)
│   └── test_oidc_validator.py       # JWT claim parsing and validation with fixture keys
│
├── contract/                        # Interface contract tests
│   ├── test_openapi_drift.py        # Validates FastAPI schema matches contracts/openapi.yaml
│   └── test_query_contracts.py      # Pydantic boundary validation tests
│
└── integration/                     # Integration tests against real/in-memory adapters
    ├── test_qdrant_retrieval.py     # Hybrid retrieval with pre-filtering against in-memory Qdrant
    ├── test_query_api_e2e.py        # FastAPI TestClient end-to-end tests (200, 401, 422, 502, 504)
    └── test_api_telemetry.py        # Trace propagation, latency_ms header/body, and token scrubbing

evals/
├── conftest.py                      # Wires retrieve_fn and generate_fn to domain ports
└── runners/
    ├── test_retrieval_dev.py        # Local development suite (14 cases)
    └── test_regression_val.py       # Blocking PR gate suite (6 cases)

docker/
├── Dockerfile.api                   # Multi-stage image for FastAPI Query runtime
└── docker-compose.yml               # Service orchestration (Qdrant + Ingestion + API + Keycloak)
```

**Structure Decision**: Hexagonal architecture extending existing `src/domain/` and `src/adapters/` while introducing `src/api/` as the presentation delivery mechanism and `src/orchestration/` as the pure application coordinator.

---

## Complexity Tracking

> **Constitution Check: 100% PASS with 0 Violations.** No complexity exemptions required.
