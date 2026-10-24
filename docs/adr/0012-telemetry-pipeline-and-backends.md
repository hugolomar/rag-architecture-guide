# ADR 0012: Telemetry Pipeline and Backends

- Status: Accepted
- Date: 2026-10-23

## Context

ADR 0011 defines a vendor-neutral observability baseline and telemetry contract. The project now
needs a concrete backend stack for system observability in local/dev environments and CI-oriented
diagnosis.

Requirements from current architecture:

- OpenTelemetry signals from FastAPI runtime and ephemeral ingestion jobs.
- Correlation across logs, metrics, and traces by `trace_id` and related identifiers.
- Low operational overhead for Docker Compose workflows.
- Safe defaults for governed content (metadata-first logging, no restricted text dumps).

## Decision

Use a Grafana-oriented OSS stack for system telemetry:

- **OpenTelemetry Collector** as the ingestion/processing entrypoint for telemetry signals.
- **Prometheus** for metrics storage and query.
- **Alertmanager** for metric-alert routing, grouping, and notification dispatch.
- **Loki** for structured log storage.
- **Tempo** for distributed tracing storage.
- **Grafana** for unified dashboards and cross-signal correlation.

Signal flow:

1. Runtime and ingestion emit OpenTelemetry traces/metrics/logs.
2. Signals go to the OpenTelemetry Collector (OTLP).
3. Collector exports:
   - metrics to Prometheus,
   - logs to Loki,
   - traces to Tempo.
4. Prometheus evaluates metric alert rules and sends firing alerts to Alertmanager.
5. Grafana reads from Prometheus/Loki/Tempo.

Ingestion is an ephemeral job, so each run must call telemetry exporter
`force_flush()/shutdown()` before process exit (as required by ADR 0011).

## Rationale

- OpenTelemetry Collector centralizes routing and reduces per-service backend coupling.
- Loki + Tempo + Prometheus + Grafana is a common, lightweight local stack for correlated
  operational diagnosis.
- Alertmanager keeps alert routing/grouping separate from application code and runtime services.
- Loki's label-based indexing and compressed log chunks fit local Compose constraints better than a
  full-text-first log stack.
- Tempo integrates cleanly with `trace_id` navigation from logs and dashboards.

## Alternatives Considered

1. **Direct-to-backend exporters from each service**
   - Pros: fewer components.
   - Cons: repeated exporter logic and tighter backend coupling in app code.
   - Rejected.

2. **ELK/OpenSearch-centric stack for logs and traces**
   - Pros: strong full-text search ecosystem.
   - Cons: higher resource footprint for a system that does not need large-scale text analytics.
   - Rejected.

A single backend is not reconsidered here: ADR 0011 already requires traces, metrics, and logs correlated by `trace_id`. One backend would leave weak multi-signal correlation and poor traceability for distributed issues.

## Consequences

- **Positive:** clear, implementable telemetry path from runtime/ingestion to dashboards.
- **Positive:** unified correlation across traces, logs, and metrics.
- **Negative:** additional operational components in local stack (collector + 5 platform services).
- **Negative:** requires dashboard/alert maintenance discipline as features evolve.
- **Boundary:** this ADR does not define AI-semantic trace schema, prompt registry workflows, or
  model-cost analytics workflows.
- **Follow-up:** ADR 0013 defines AI observability, prompt-governance workflows, and the semantic
  tracing platform choice.
