<!--
SYNC IMPACT REPORT
Version change: initial-template -> 1.0.0
List of modified principles: Initial adoption from draft
Added sections:
- I. Domain limits and abstractions (clean/hexagonal core) (Articles 1-6)
- II. Dependencies and environments (Article 7)
- III. Security by design (Articles 8-12)
- IV. Retrieval and evaluation (Articles 13-15)
- V. Verification (Articles 16-19)
- VI. Observability (Articles 20-22)
- VII. Documentation (Articles 23-25)
- VIII. Deployment (Articles 26-27)
- IX. Governance (Articles 28-31)
Removed sections: Template placeholders
Follow-up TODOs: None
-->

# Enterprise Governed RAG Constitution

This constitution is the supreme architectural and engineering policy for this repository. Its articles are non-negotiable invariants enforced automatically by CI tooling. A requirement without automated verification is considered unenforced.

## I. Domain limits and abstractions (clean/hexagonal core)

### Article 1 — Python baseline

The Data Plane and the Runtime Plane run on Python 3.14. The series is pinned in `.python-version`. The patch may be the latest in that series.

### Article 2 — Hexagonal architecture

The domain stays at the center: governed knowledge and who may read it. Business rules, entities, and value objects live there. The domain does not import an infrastructure package. Dependency inversion is mandatory at the boundary. Orchestration depends on domain ports, not on a provider SDK.

Inbound adapters call the domain. The HTTP API is one. The evaluation harness is another, calling the same retrieval and generation ports without going through HTTP. Ingestion is the inbound path that writes governed chunks.

Outbound adapters implement the ports. The retrieval store, the identity provider, and the model gateway are outbound adapters.

### Article 3 — Shared domain

Domain model ownership resides in one shared domain package in this repository. Ingestion, the API, and the evaluation harness import that package. None of them keeps a second copy of the contracts.

The canonical document and the governance each chunk inherits are domain models. The parser, the embedding step, and the store writer are not in the package. Adapters translate at their own boundary and do not own the models.

### Article 4 — Behavioral ports

All contracts that cross a layer boundary are `abc.ABC` classes with `@abstractmethod`. An adapter must inherit from the port. A class that merely exposes methods of the same name does not satisfy the port.

`typing.Protocol` is not the mechanism for cross-layer contracts.

The retrieval and generation seams are `retrieve_fn(query, user_id, top_k=5)` and `generate_fn(query, context_doc_ids, user_id)`.

### Article 5 — Data contracts and boundary validation

Data that crosses a port is a Pydantic v2 model validated at the boundary. A type mismatch or a value outside a closed catalog is a validation failure. Silent coercion is not allowed. The caller is not the authority for validation; a client, a prompt, or a caller payload does not relax a type or grant access.

Where the contract carries governance, the required fields are `doc_id`, `allowed_groups`, `status`, and the caller's identity context. Closed governance catalogs are defined as strict enums in the shared domain package: departments (`HR`, `Engineering`, `Security`, `Finance`, `Legal`), classifications (`public`, `internal`, `restricted`), lifecycle statuses (`current`, `deprecated`, `archived`), and identity-provider groups (`all-employees`, `people-team`, `engineering-core`, `security-oncall`, `leadership`). Access is the intersection of the caller's resolved groups with `allowed_groups`. `department` and `classification` do not grant access.

### Article 6 — Simplicity and proportionality

Abstractions are introduced only when a port boundary or a documented decision requires them. Framework features are used directly. A custom wrapper around a framework feature requires a recorded reason. Additional complexity requires documented justification explaining why simpler alternatives are insufficient; complexity lacking that justification does not enter the codebase.

## II. Dependencies and environments

### Article 7 — uv

uv is the only project tool for the Python interpreter, the virtual environment, and package resolution.

A dependency enters through `pyproject.toml` with `uv add` or `uv add --dev`, and is locked in `uv.lock`. `uv sync` installs that tree. An install that does not update `pyproject.toml` and `uv.lock` is not a change to the project.

## III. Security by design

### Article 8 — Zero trust

The caller, the query text, and the path the request traveled are not trusted. User-facing access requires an OIDC token. `retrieve_fn` and `generate_fn` receive `user_id`; they do not receive a group list from the request or the evaluation case. The system resolves groups through the identity provider. The caller does not supply or modify the group list, and text in the query does not change them. A service-to-service call follows the same rule: the network does not grant access.

### Article 9 — Deny by default

A document is retrieved only when the caller's groups intersect `allowed_groups`. No intersection means the document is absent. The group list on the document is the whole of the access rule. `department` and `classification` do not add a second one. No escalation path exists through query text or request metadata.

### Article 10 — Trim before the model

Security trimming is deterministic. The group intersection and the lifecycle rule run before any chunk is passed to generation. The model does not decide whether the caller may see a document. An answer that contains a prohibited keyword is a leak even when the behavior is `deny_access`.

### Article 11 — Prompt isolation

Retrieved document content is enclosed in isolation markers before it is passed to the model. Instruction-like text inside a retrieved chunk does not alter the system instructions or the caller's access. The prompt template is the authority for the structure of the model input.

### Article 12 — Secrets stay out of the tree

Credentials, tokens, and keys are not written into source or into a tracked config file. The protected suite stays outside git. A secret store is chosen when a deployed service needs one.

## IV. Retrieval and evaluation

### Article 13 — The suites are the specification

`evals/` defines the behavioral contract of the pipeline. One prohibited document in the retrieved set or one prohibited keyword in the answer is a hard failure; aggregate scores do not offset a security violation.

The development suite does not block CI. The validation suite is the pull-request gate. The protected suite is the release gate and is strictly isolated; it is never used to tune chunk size, retrieval weights, prompts, or model selection.

Pipeline responses conform to one of four mutually exclusive behaviors: `ground_answer`, `deny_access`, `abstain`, or `clarify`. `deny_access` and `abstain` require an explicit, non-empty refusal response.

### Article 14 — Written-token and semantic retrieval

Retrieval must support both semantic matching (by meaning) and exact written-token matching (flags, configuration keys, error codes, and identifiers). Semantic similarity alone does not satisfy an exact-token query.

Both representations are computed before storage. The query path uses the exact same model and channel-specific transforms as ingestion. The embedding model identity and vector dimensions are governed by a single project-wide configuration. Changing the embedding model requires creating a new collection and re-indexing the corpus; mixing vectors from different models in the same collection is prohibited.

### Article 15 — Fail loud on unimplemented ports

Unimplemented ports and adapters raise `NotImplementedError`. An empty collection, null payload, or silent stub does not stand in for an implementation.

## V. Verification

### Article 16 — Testing pyramid and test-first development

All implementation follows test-first development: tests exist and fail before implementation code is written.

The testing strategy consists of distinct, non-overlapping levels:
- **Unit tests:** specify pure domain rules, schema constraints, and isolated adapter translation logic.
- **Integration tests:** verify adapters against real infrastructure (such as a running Qdrant instance) rather than in-memory mocks. Behavior that depends on external storage or engines must be proven against the real dependency.
- **End-to-end (E2E) tests:** verify the complete pipeline: raw document ingestion, vector indexing, HTTP API request with OIDC identity, retrieval with security trimming, and model generation.
- **Evaluation suites:** govern probabilistic retrieval quality, grounding, and security leak policies against golden benchmark cases.

### Article 17 — Contract tests

Contract tests run in the first gate and enforce that interfaces between layers and external consumers remain strictly compatible:
- **HTTP API contract:** verified by Spectral schema linting and the OpenAPI drift test. A divergence between code and the recorded specification fails the build.
- **Port contracts:** the signatures of `retrieve_fn` and `generate_fn` are verified by the harness self-check and suite integrity tests. A signature divergence fails before integration tests run.
- **Data manifest contract:** the corpus governance manifest (`manifest.json`) is verified against its canonical Pydantic model. Schema mismatches or values outside closed catalogs fail before ingestion begins.

### Article 18 — What blocks a merge

A pull request runs two gates in order:

The first gate runs without external LLM provider keys (model credentials) and fails fast on any defect: code formatting and linting, strict static type checks, contract tests and OpenAPI drift, automated documentation validation (`mkdocs build --strict`), suite integrity and harness self-checks, unit tests, structural dependency direction checks, and static security scans (SAST and dependency vulnerabilities).

The second gate runs the validation suite with provider access. A prohibited document in the retrieved set, a prohibited keyword in the answer, or a missing expected document blocks the merge. General security scans or passing scores never waive a deterministic evaluation failure.

### Article 19 — Executable architecture

Architectural constraints are enforced by automated tooling in CI, never by convention, documentation, or diagrams alone.

Every structural rule in this constitution—including layer boundaries, inward dependency direction, and port inheritance—must have an associated automated check (such as `import-linter` or structural contract tests). A constraint lacking an automated enforcement check is considered unenforced.

## VI. Observability

### Article 20 — Telemetry baseline

Every deployable process emits structured logs, metrics, and distributed traces via OpenTelemetry. Log lines are JSON on stdout. Every relevant signal carries the correlation identifiers for that process: `trace_id`, `span_id`, and `request_id` for the API or `run_id` for ingestion. `user_id` is included in runtime signals once it is resolved. `test_id` is included in evaluation executions.

Correlation identifiers are propagated across all inbound and outbound calls. A signal that drops the trace context is a defect.

Ingestion flushes and shuts down the telemetry exporters before the process exits. Telemetry lost at exit is a defect.

Observability requirements are declared in the feature specification. A component that does not emit the signals its specification requires does not meet its delivery condition.

### Article 21 — AI traceability

For each query execution, the AI trace records: `user_id` reference and request correlation identifiers, query text and any rewrite artifact, retrieved document and chunk identifiers with ranking metadata, the prompt version identifier and the isolation template used, model invocation metadata (provider, model, latency, token usage, completion status), and the response behavior classification.

Denied and trimmed chunks appear in the AI trace as audit metadata only: `doc_id`, decision reason, and stage. Document text does not appear.

Prompts are versioned. A prompt change does not require a code redeploy. The version that produced a response is recoverable from the trace.

The AI observability platform is behind an internal adapter boundary. Orchestration logic does not depend on its SDK types.

### Article 22 — Telemetry data hygiene

Telemetry does not carry secrets, credentials, raw authorization headers, PII, or provider keys. Restricted document content does not appear in any telemetry payload. Redaction and masking policies are applied before emission.

## VII. Documentation

### Article 23 — Codebase and verification documentation

Every module, class, interface, method, and function across the domain, adapters, evaluation harness, and frontend components must be documented with native structured docstrings (PEP 257 Google style for Python; JSDoc/TSDoc for frontend). Documentation must explicitly detail:
- **Summary:** The core responsibility and business purpose of the element.
- **Args / Parameters:** The meaning, valid range, units, and constraints of all inputs.
- **Returns:** The exact structure, behavior, and semantic significance of return values.
- **Raises / Exceptions:** Explicit error conditions, boundary failure states, and exception types.

Test classes and test methods follow the same standard, explicitly documenting the scenario under test, preconditions, and expected invariant verification.

### Article 24 — Internal commentary and rationale

Internal implementation logic avoids redundant comments that restate what the code does or how it does it. Comments (`#` or `//`) are reserved exclusively to document the "why": non-obvious algorithmic decisions, enterprise security constraints, external library workarounds, or hardware/OS idiosyncrasies. Self-evident logic requires no commentary.

### Article 25 — Documentation accuracy and evolution

Documentation, API specifications, and architectural diagrams must remain in continuous synchronization with the implementation:
- Any change that alters a contract, parameter, return value, or architectural boundary must update the corresponding docstrings, OpenAPI schemas, and documentation artifacts within the same commit.
- Outdated, contradictory, or misleading documentation is classified as a defect, not deferred technical debt.
- Automated documentation validation (`mkdocs build --strict` and OpenAPI drift tests) runs in CI; any warning, missing parameter, or broken cross-reference fails the build and blocks the merge.

## VIII. Deployment

### Article 26 — Container packaging and process boundaries

Deployable processes run as container images:
- **Deployable units:** The API is packaged as a single image running the stateless FastAPI runtime with the model gateway (LiteLLM) embedded in-process. Ingestion is packaged as an image executing a one-shot batch process that terminates upon completion. The retrieval store (Qdrant), identity provider (Keycloak), observability stack (OTel Collector, Loki, Tempo, Prometheus, Grafana), and decoupled Web UI each run in their own dedicated containers.
- **Non-services:** The shared domain package and evaluation harness are software libraries and test suites, not deployable network services.
- **Multi-stage image hygiene:** Images built by this project use multi-stage Dockerfiles. The build stage installs dependencies via `uv sync` from `uv.lock`. The runtime stage copies the virtual environment and bundled ONNX embedding models (preloaded from the project's single model configuration, never hardcoded in Dockerfiles), executing directly with the environment's `python` (never `uv run` in production). Build tools (`uv`, compilers) are excluded from runtime images.
- **Upstream images:** Upstream services are consumed as published; rebuilding upstream images is prohibited.

### Article 27 — Runtime orchestration and lifecycle

The entire runtime stack starts with a single command (`docker compose up` or a single wrapper script when dependency ordering or identity realm pre-seeding is required). Secondary manual execution procedures are prohibited.

Container definitions are environment-agnostic; all runtime configuration is injected exclusively via environment variables.

Service lifecycles are strictly differentiated:
- **Long-running services** (API, Qdrant, Keycloak, Observability) expose health check endpoints for startup orchestration. The API health check reports process liveness only; it does not grant access or bypass authentication or retrieval.
- **Batch processes** (ingestion) must not expose a health endpoint. Completion status is determined strictly by process exit code after all OpenTelemetry exporters are flushed and shut down.

## IX. Governance

### Article 28 — Supremacy

This constitution is the highest-priority engineering policy for this repository. In case of conflict between this document and a local convention, this document takes precedence.

### Article 29 — Amendment procedure

A change to this constitution requires: a description of the affected articles and the migration impact, explicit maintainer approval, and an update to the corresponding ADR when the underlying reason changes. Templates and guidance artifacts that depend on the changed article are updated in the same change set.

### Article 30 — Versioning

The constitution follows semantic versioning. A MAJOR increment removes or redefines a principle. A MINOR increment adds a principle or materially expands mandatory guidance. A PATCH increment clarifies wording without changing meaning.

### Article 31 — Compliance

Every plan, spec, and task set generated for this project includes a constitution compliance check. Every pull request review records pass or fail against the relevant articles. Non-compliance is resolved before merge or explicitly waived with documented rationale.

**Version**: 1.0.0 | **Ratified**: 2026-10-27 | **Last Amended**: 2026-10-27
