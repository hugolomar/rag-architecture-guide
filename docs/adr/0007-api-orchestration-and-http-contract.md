# ADR 0007: API Orchestration and HTTP Contract

- Status: Proposed
- Date: 2026-10-23

## Context

ADR 0001 defines a stateless FastAPI runtime. ADR 0003 and ADR 0004 define domain ports and
validated contracts. ADR 0005 defines query vectorization in Python, and ADR 0006 defines Qdrant
as the retrieval store with pre-inference filtering by `allowed_groups` and `status`.

What remains open is the API boundary contract and orchestration commitments: source of truth for
HTTP schema, error semantics, operational limits, response payload shape, and identity transport.

## Decision

### 1) HTTP contract source of truth

- Keep a versioned contract file at `docs/openapi.yaml`.
- Follow contract-first governance for API changes.
- Validate contract quality in CI with Spectral (`--fail-severity=error`).
- Add a contract-drift test so FastAPI-generated schema and `docs/openapi.yaml` must match.

### 2) Endpoint orchestration order

For a query request, orchestration runs in this order:

1. Validate HTTP input.
2. Resolve caller context from `user_id` (groups are not accepted from the caller).
3. Build query vectors with ADR 0005 transforms.
4. Retrieve evidence through `retrieve_fn(query, user_id, top_k=3)`.
5. Generate through `generate_fn(query, context_doc_ids, user_id)` using only retrieved evidence.

The evaluation harness calls retrieval/generation ports directly and does not go through HTTP.

### 3) HTTP error semantics

- **422 Unprocessable Entity** for invalid request shape/constraints (missing fields, invalid
  `top_k`, query length out of bounds).
- **401 Unauthorized** for missing/unknown identity in request headers.
- **502 Bad Gateway** or **504 Gateway Timeout** for upstream provider/runtime dependency failures.
- **200 OK** for business outcomes `ground_answer`, `deny_access`, and `abstain` (classification is
  expressed in payload `behavior`, not HTTP status code).

### 4) Operational limits

- Query length: min `3`, max `500` characters.
- `top_k`: default `3`, max `10`.
- Global endpoint timeout budget: `10s`.
- No HTTP-layer retries in the API route.

### 5) Public response model

The query response contract includes:

- `answer`
- `behavior` (`ground_answer` | `deny_access` | `abstain` | `clarify`)
- `citations` (possibly empty for `deny_access` or `abstain`)
- `trace_id`
- `latency_ms`

### 6) Identity transport for this stage

- Use `X-User-Id` as the required request header in development and evaluation stages.
- Resolve user groups from `data/users.json` through the identity component.
- Unknown `X-User-Id` is rejected with `401` before orchestration.
- Bearer-token-based identity is deferred to a later ADR.

## Rationale

- A versioned OpenAPI file supports spec-driven development and multi-consumer governance.
- Drift checks keep implementation and contract aligned.
- Business outcomes remain explicit without leaking authorization semantics into transport-level
  status codes.
- Fixed limits and no route-level retries protect latency and cost envelopes.
- Header-based identity is sufficient for local/eval workflows and keeps authorization deterministic
  against existing datasets.

## Alternatives Considered

1. **FastAPI-generated OpenAPI only (no versioned file)**
   - Pros: less maintenance.
   - Cons: weaker contract governance and reviewability.
   - Rejected.

2. **Caller-supplied groups in request payload**
   - Pros: fewer lookups.
   - Cons: violates domain rule that identity context is resolved by system authority.
   - Rejected.

3. **403/404 for deny/abstain**
   - Pros: conventional HTTP usage.
   - Cons: confuses transport failure with governed business behavior for this RAG contract.
   - Rejected.

4. **Route-level retries**
   - Pros: simple resilience mechanism.
   - Cons: retry amplification for interactive traffic and unstable latency.
   - Rejected.

## Consequences

- **Positive:** API behavior is explicit, testable, and contract-governed.
- **Positive:** deterministic identity handling aligns with evaluation suites and security rules.
- **Negative:** requires maintaining both implementation and versioned OpenAPI file.
- **Negative:** production auth integration remains a pending decision.
- **Boundary:** this ADR does not choose the LLM provider, gateway product, or telemetry backend.
- **Follow-up:** define production authentication and model-gateway strategy in dedicated ADRs.
