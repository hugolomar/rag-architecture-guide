# ADR 0011: Observability Baseline and Telemetry Contract

- Status: Accepted
- Date: 2026-10-23

## Context

ADRs 0005-0009 define ingestion, retrieval, API orchestration, provider/gateway strategy, and
runtime security boundaries. The project now needs a baseline observability contract that is
implementation-agnostic and safe for governed data.

Observability must support:

- operational diagnosis of API and ingestion jobs,
- security/audit verification of pre-inference controls,
- evaluation traceability without leaking restricted content.

## Decision

Adopt OpenTelemetry-based instrumentation and a minimum telemetry contract for all runtime paths.

### 1) Instrumentation scope

- Instrument FastAPI runtime paths and ingestion job paths with OpenTelemetry SDK for Python.
- Treat ingestion as ephemeral: each run must flush/shutdown telemetry exporters before process exit.

### 2) Required telemetry signals

- **Traces:** end-to-end request/job traces with spans for identity resolution, query embedding,
  retrieval call, generation adapter call, provider call, and ingestion stages.
- **Metrics:** HTTP status counters, API latency distributions, upstream failure counters, ingestion
  duration counters/histograms, and chunk/indexing counters.
- **Note:** these metrics stay operational. A query has no business-event stream. Its business
  outcome is the response `behavior`, recorded as AI-semantic telemetry (ADR 0013), not as a
  business dashboard on the system metrics stack.
- **Logs:** structured JSON logs on stdout, correlated to traces.

### 3) Correlation contract

Every relevant signal should carry correlation identifiers where applicable:

- `trace_id`
- `span_id`
- `request_id` (runtime) or `run_id` (ingestion)
- `user_id` (runtime, when resolved)
- `test_id` (evaluation executions, when applicable)

### 4) Security and data-minimization rules

- Never log secrets, API keys, raw authorization headers, or provider credentials.
- Never log restricted chunk content in observability payloads.
- For denied/trimmed evidence, log metadata only (for example: `doc_id`, decision reason, stage),
  not document text.
- Prompt/response capture, if enabled, must follow the data-minimization rules above.

### 5) Provider and stack neutrality

- This ADR does not choose specific telemetry backends (for example Grafana/Loki/Tempo, Langfuse,
  Phoenix, or others).
- This ADR does not choose sampling rates, retention windows, or cost policies.
- Those choices are deferred to follow-up ADRs.

## Rationale

- OpenTelemetry gives a portable baseline independent from a specific vendor stack.
- A minimum correlation contract allows joining logs, traces, and metrics across runtime/evals.
- Ephemeral ingestion jobs require explicit flush/shutdown to avoid losing telemetry at process end.
- Metadata-only records for trimmed evidence preserve forensic value without leaking restricted text.

## Alternatives Considered

1. **Backend-first decision without telemetry contract**
   - Pros: faster tooling setup.
   - Cons: unclear data semantics and inconsistent instrumentation across components.
   - Rejected.

2. **Logs-only observability**
   - Pros: minimal implementation complexity.
   - Cons: weak latency diagnosis and poor cross-component causality analysis.
   - Rejected.

3. **Capture full prompts and full retrieved content by default**
   - Pros: easier debugging.
   - Cons: high data-exposure risk for governed content.
   - Rejected.

## Consequences

- **Positive:** unified, vendor-neutral baseline for runtime and ingestion observability.
- **Positive:** safer operational telemetry for governed data (metadata-only, no restricted text exposure).
- **Negative:** extra implementation work to maintain instrumentation consistency.
- **Boundary:** this ADR does not choose observability products or the AI-tracing platform. ADR 0012 chooses the operational stack. ADR 0013 chooses semantic tracing and prompt governance.
