<!--
SYNC IMPACT REPORT
Version change: 1.2.2 -> 2.0.0
List of modified principles:
- Consolidate 31 articles into 16 high-density architectural invariants optimized for LLM comprehension and deterministic verification.
- Section I (Domain Limits & Hexagonal Core): Unify domain purity, dependency inversion, and composition root discipline (Article 2). Enforce nominal subtyping via abc.ABC while eliminating redundant NotImplementedError article (Article 3). Abstract governance validation and closed catalogs without hardcoding business enum names (Article 4).
- Section II (Dependencies & Environment): Generalize runtime environment pinning (.python-version, pyproject.toml) and single lockfile discipline (Article 6).
- Section III (Security by Design): Consolidate Zero-Trust, deterministic security trimming, and pre-inference filtering into a unified invariant (Article 7).
- Section IV (Retrieval & Evaluation): Correct default retrieval contract top_k to 3 aligning with evals and ADR 0011; formalize dual dense/sparse representation parity (Articles 9, 10).
- Section V (Verification & Executable Architecture): Unify testing pyramid with real-infrastructure requirement and automated CI gates (Articles 10, 11).
- Section VI (Observability & Operation): Consolidate structured logging, distributed tracing, zero telemetry loss, and data hygiene into unified observability invariant (Article 12).
- Section VII (Deployment & Lifecycle): Consolidate multi-stage container packaging and single-command orchestration invariants (Article 13).
- Section VIII (Governance): Retain supremacy, amendment protocol, SemVer, and compliance rules (Articles 14-16).
Migration impact:
- MAJOR amendment. Eliminates specification drift, removes micro-style linters from constitutional scope, and updates contract test tests/contract/test_constitution_governance.py to match new article numbers.
Follow-up TODOs: Update tests/contract/test_constitution_governance.py and add scripts/check.sh.
-->

# Enterprise Governed RAG Constitution

This constitution is the supreme architectural and engineering policy for this repository. Its articles are non-negotiable invariants enforced automatically by CI tooling. A requirement without automated verification is considered unenforced.

## I. Domain limits and abstractions (clean/hexagonal core)

### Article 1 — Python baseline and strict typing

The Data Plane and Runtime Plane run on the Python series pinned in `.python-version` and managed via `pyproject.toml`.

The codebase strictly enforces comprehensive static typing and modern idioms. All production and test code must pass strict static type analysis (`mypy --strict`) without untyped definitions or unchecked generics.

### Article 2 — Hexagonal architecture and composition roots

The domain stays at the center: business entities, value objects, and governance rules reside exclusively in the shared domain package (`src/domain/`). The domain layer has zero imports from infrastructure, storage, ingestion, or third-party SDKs.

Application workflows and orchestrators depend solely on abstract domain ports received via dependency injection. They must never import, instantiate, or provide fallback defaults to concrete infrastructure adapters.

The instantiation and wiring of concrete infrastructure adapters is strictly confined to **Composition Roots** (the outermost application entrypoints, such as batch CLI entrypoints and HTTP application factories). Presentation-tier dependency injection remains strictly at delivery boundaries and never leaks into orchestration or domain logic.

### Article 3 — Behavioral ports and nominal subtyping

All contracts that cross layer boundaries are abstract classes inheriting from `abc.ABC` with `@abstractmethod`. 

Subtyping is strictly nominal: adapters must explicitly inherit from the domain port. Structural typing (`typing.Protocol`) and duck typing are prohibited across layer boundaries. Unimplemented ports or adapters must fail loudly; empty stubs or silent fallbacks do not stand in for an implementation.

The retrieval and generation seams provide provider-agnostic access to the knowledge base and model gateway without coupling orchestration to concrete storage or LLM provider SDKs.

### Article 4 — Data contracts and boundary validation

Data crossing a port boundary is validated strictly against Pydantic v2 domain models. Type coercion, extra undocumented fields, and silent defaults are prohibited at boundaries.

Access authorization and document lifecycle decisions are governed strictly by closed domain catalogs (`StrEnum`). Access permissions are determined solely by the intersection of the caller's resolved identity groups with the document's `allowed_groups`. Department ownership and sensitivity classification represent provenance and handling metadata, but never confer read access on their own.

### Article 5 — Simplicity and proportionality

Abstractions are introduced only when an explicit port boundary, multi-provider requirement, or documented architectural decision demands them. Framework features and standard library primitives are used directly. Custom abstractions lacking documented rationale do not enter the codebase.

## II. Dependencies and environments

### Article 6 — Single dependency authority

The project runtime and dependencies are managed exclusively through a single package manager with deterministic lockfile enforcement (`uv.lock`). 

Direct environment mutations or dependency additions outside `pyproject.toml` and `uv.lock` are prohibited. Production runtime containers execute strictly using the locked environment without build-time installers.

## III. Security by design

### Article 7 — Zero-trust and deterministic security trimming

Callers, query strings, and transport paths are untrusted. Identity context is resolved exclusively through the authoritative identity provider, never from user-supplied request headers or prompt text.

Security trimming is deterministic and mandatory: document and chunk access is granted only when the caller's resolved groups intersect `allowed_groups`. Obsolete or archived documents (`status == archived`) are completely excluded from indexing and retrieval.

All security trimming and lifecycle filtering executes before context is supplied to the generative model. The generative model never decides authorization. Retrieved document content must be isolated with clear boundary markers to prevent prompt injection.

### Article 8 — Secrets stay out of the tree

Credentials, API keys, tokens, and private hold-out evaluation datasets must never be committed to version control or hardcoded in configuration files.

## IV. Retrieval and evaluation

### Article 9 — The suites are the specification

Evaluation suites (`evals/`) define the formal behavioral contract of the system. A single security leak (retrieving a prohibited document or emitting a prohibited keyword) is a deterministic failure; aggregate retrieval metrics never offset a security violation.

Pipeline responses conform strictly to four mutually exclusive behaviors: `ground_answer`, `deny_access`, `abstain`, or `clarify`. Refusals (`deny_access`, `abstain`) must return an explicit refusal response.

The validation suite serves as the blocking pull-request gate. The protected suite is isolated and reserved strictly for release gating.

### Article 10 — Dual written-token and semantic retrieval

Retrieval must support both semantic matching (by meaning) and exact written-token matching (flags, error codes, configuration keys, and exact identifiers).

Dense and sparse representations are computed before storage. The query path uses the exact same model identity, dimensions, and channel transforms as the ingestion path. Changing the embedding model requires creating a new collection and re-indexing the corpus; mixing embedding representations within a single collection is prohibited.

## V. Verification and quality

### Article 11 — Testing pyramid and test-first development

All implementation follows test-first development: tests exist and fail before implementation code is written.

The testing strategy consists of distinct, non-overlapping levels:
- **Unit tests:** verify pure domain rules, schema validation, and isolated transformation logic in memory.
- **Integration tests:** verify adapters against real infrastructure instances (or isolated containers via testcontainers) rather than in-memory mocks.
- **End-to-end (E2E) tests:** verify full vertical pipelines from ingestion through storage and retrieval to final generation.
- **Evaluation suites:** govern probabilistic retrieval quality, grounding, and security policies against benchmark cases.

### Article 12 — Executable architecture and quality gates

Architectural constraints are enforced by automated tooling in CI, never by convention or documentation alone.

Layer boundaries and inward dependency directions are verified via static import-graph analysis (`import-linter`). Port contracts and adapter inheritance are verified via structural contract tests. Documentation accuracy and public API docstrings (PEP 257 Google style) are validated automatically. A failure in static typing, linting, architectural contracts, unit tests, or evaluation gates blocks the merge.

## VI. Observability and operation

### Article 13 — Observability baseline, lifecycle, and data hygiene

Every deployable process emits structured JSON logs to stdout, metrics, and distributed traces via OpenTelemetry. All signals must carry consistent correlation identifiers (`run_id` for batch ingestion; `trace_id`, `span_id`, `request_id` for runtime queries).

Batch processes must guarantee zero telemetry loss: all OpenTelemetry exporters must be flushed (`force_flush`) and cleanly shut down prior to process termination. Completion status is reported strictly via process exit codes.

Telemetry signals must never contain credentials, raw authorization tokens, personal data, or restricted document body text.

### Article 14 — Container packaging and single-command deployment

Deployable units are packaged as reproducible, multi-stage container images. Build-time dependencies, compilers, and package installers are excluded from final runtime images.

The entire local runtime stack must start with a single declarative command (`docker compose up` or an orchestrating script). Runtime configuration is supplied exclusively through environment variables. Long-running services expose health check endpoints for lifecycle readiness; batch jobs communicate results strictly via exit codes.

## VII. Governance

### Article 15 — Supremacy

This constitution is the highest-priority engineering policy for this repository. In case of conflict between this document and any local convention, feature specification, or documentation note, this constitution takes precedence.

### Article 16 — Amendment procedure, versioning, and compliance

Amendments to this constitution require:
1. An explicit description of affected articles, migration rationale, and impact report.
2. Maintainer approval.
3. Synchronized updates to corresponding ADRs, contract tests, and documentation artifacts.

This constitution follows Semantic Versioning:
- **MAJOR**: Removing, consolidating, or fundamentally redefining an architectural principle.
- **MINOR**: Adding a new principle or materially expanding mandatory invariants.
- **PATCH**: Wording clarifications and non-semantic corrections.

Every plan, specification, and pull request must record compliance against this constitution.

**Version**: 2.0.0 | **Ratified**: 2026-10-27 | **Last Amended**: 2026-11-13
