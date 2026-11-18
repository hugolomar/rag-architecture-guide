---
description: Mandatory standards for structured JSON logging, OpenTelemetry tracing/metrics, credential scrubbing, flush lifecycle, and process exit codes
trigger: model_decision
---

# Telemetry and Observability Standards

All application processes, batch pipelines, and CLI entrypoints in this repository must strictly adhere to these standards to prevent telemetry loss, guarantee data hygiene, and maintain uniform correlation.

## 1. Structured JSON Logging Format

All logs must be emitted as newline-delimited JSON to stdout. Unformatted plain-text log lines are prohibited in production runtimes.
Every log event must contain at least the following standard fields:
- `timestamp`: UTC ISO 8601 string (`YYYY-MM-DDTHH:MM:SS.sssZ`).
- `level`: Log level name in uppercase (`INFO`, `WARNING`, `ERROR`, `DEBUG`).
- `message`: Human-readable description of the event.
- `run_id` or `trace_id`: Deterministic execution correlation identifier. Batch jobs propagate `run_id`; runtime request-reply queries propagate `trace_id` and `span_id`.
- `stage`: Current processing pipeline stage (e.g., `manifest.validate`, `document.parse`, `storage.upsert`).

## 2. Sensitive Data Hygiene & Credential Scrubbing

Telemetry payloads must never expose confidential data:
- **Credential Masking**: Automated masking must intercept known secret patterns in logs and trace attributes:
  - Authorization headers / `Bearer [token]` -> `Bearer ***`
  - Passwords and API keys (`api_key=[val]`, `password=[val]`) -> `***`
- **Body Text Scrubbing**: Raw document body text, restricted/confidential policy content, and personally identifiable information (PII) must **never** be attached to span attributes or logged. Telemetry signals only record counts, identifiers (`doc_id`), and execution durations.

## 3. Ephemeral Batch Lifecycle & Guaranteed Telemetry Flush

Batch pipelines (such as document ingestion) are ephemeral and exit upon completion. Default asynchronous telemetry buffers drop in-flight spans and metrics when the process terminates.

- **Guaranteed Flush**: Every CLI composition root entrypoint must enclose execution within a `try ... finally` block that explicitly calls `flush_and_shutdown()` on the `TelemetryManager` before process exit.
- Telemetry failure during shutdown must not mask business domain errors, but must fail loudly if all business operations were successful yet telemetry failed to persist.

## 4. Deterministic Process Exit Codes

Batch entrypoints communicate execution status strictly through process exit codes:
- `0`: **Success** - All active documents parsed, chunked, embedded, indexed, and telemetry flushed.
- `1`: **Schema Failure** - Manifest validation error, out-of-catalog governance values, or invalid configuration.
- `2`: **File Mismatch** - Manifest references non-existent files on disk, or uncataloged raw files detected.
- `3`: **Storage Failure** - Qdrant connectivity drop, collection initialization failure, or vector upsert error.
- `4`: **Telemetry Failure** - Exporter timeout, OTel endpoint unreachable during guaranteed flush.
