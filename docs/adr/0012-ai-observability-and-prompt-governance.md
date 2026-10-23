# ADR 0012: AI Observability and Prompt Governance

- Status: Proposed
- Date: 2026-10-23

## Context

ADR 0010 defines the telemetry baseline contract and ADR 0011 defines the system-observability
stack. Those decisions cover operational signals, but they do not define semantic AI tracing,
prompt lifecycle governance, or domain-specialist workflows.

The project needs:

- end-to-end AI traceability across retrieval and generation,
- controlled prompt evolution without code redeploys for every text change,
- cost and token visibility by request and usage segment,
- safety controls that keep governed-data restrictions intact in AI traces.

## Decision

Use **Langfuse** as the AI observability and prompt-governance platform.

### 1) Semantic trace scope

For each query execution, record AI-semantic telemetry with at least:

- caller identity reference (`user_id`) and request correlation ids (`trace_id`, `request_id`),
- query text and optional rewrite artifacts when rewrite is enabled,
- retrieved document/chunk identifiers and ranking metadata,
- final prompt assembly metadata and prompt version identifiers,
- model invocation metadata (provider/model id, latency, token usage, completion status),
- response behavior classification (`ground_answer`, `deny_access`, `abstain`, `clarify`).

### 2) Prompt governance workflow

- Prompts are versioned and tagged by environment stage (for example `staging`, `production`).
- Domain specialists can propose and review prompt revisions through governed workflows.
- Runtime selects prompt versions by configuration, enabling controlled rollback without API
  redeploy.

### 3) Security and redaction rules

- AI traces must not store secrets, credentials, or raw authorization headers.
- Restricted document content remains subject to data-minimization policy from ADR 0009.
- For denied/trimmed evidence, store metadata-only audit fields (`doc_id`, reason, stage), not raw
  restricted text.
- Prompt/response capture must support configurable redaction for sensitive fields.

### 4) Integration boundary

- Langfuse integration is implemented behind internal adapter boundaries so orchestration logic does
  not depend directly on Langfuse SDK types.
- Core retrieval/generation port contracts remain unchanged.

## Rationale

- System telemetry alone cannot explain LLM-specific behavior regressions.
- Prompt version traceability is required for reproducible evaluation and safe rollback.
- Domain-specialist collaboration on prompt content improves governance without coupling every text
  edit to full code release cycles.
- Adapter-bounded integration preserves replaceability of observability tooling.

## Alternatives Considered

1. **No dedicated AI observability platform**
   - Pros: fewer dependencies.
   - Cons: weak semantic debugging and poor prompt-change auditability.
   - Rejected.

2. **Keep AI traces only in generic logs/metrics backends**
   - Pros: single telemetry stack.
   - Cons: limited prompt/version workflow support and weaker model-level analytics UX.
   - Rejected.

3. **Phoenix as primary AI observability platform**
   - Pros: useful tracing and experimentation capabilities.
   - Cons: weaker fit for the required prompt governance workflow for domain-specialist ownership in
     this phase.
   - Rejected for this stage.

## Consequences

- **Positive:** richer AI debugging and prompt-change audit trail.
- **Positive:** controlled prompt iteration by domain and engineering stakeholders.
- **Negative:** additional platform dependency and integration complexity.
- **Negative:** requires strict redaction discipline to avoid governed-data leakage in traces.
- **Boundary:** this ADR does not redefine runtime authorization logic, retrieval filters, or HTTP
  contract semantics from ADRs 0006, 0007, and 0009.
- **Follow-up:** add prompt-governance operational playbook and evaluation linking rules between
  prompt versions and suite runs.
