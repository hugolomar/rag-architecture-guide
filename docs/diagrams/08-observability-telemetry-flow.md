# Observability telemetry flow

Operational telemetry flow from ADR 0011 and ADR 0012.

Runtime and ingestion both emit OTLP signals to the OpenTelemetry Collector. The collector routes
metrics to Prometheus, logs to Loki, and traces to Tempo. Prometheus sends firing metric alerts to Alertmanager. Grafana reads from Prometheus, Loki, and Tempo.

```mermaid
graph TD
  API["RAG API<br/>OTel instrumentation"]
  Ingest["Ingestion job<br/>OTel instrumentation"]
  Collector["OpenTelemetry Collector<br/>OTLP entrypoint and routing"]
  Prom[("Prometheus")]
  Alert["Alertmanager"]
  Loki[("Loki")]
  Tempo[("Tempo")]
  Graf["Grafana"]
  Ops["Ops notification targets"]

  API -- "OTLP traces, metrics, logs" --> Collector
  Ingest -- "OTLP traces, metrics, logs" --> Collector
  Collector -- "Metrics export" --> Prom
  Collector -- "Logs export" --> Loki
  Collector -- "Traces export" --> Tempo
  Prom -- "Firing metric alerts" --> Alert
  Alert -- "Routes grouped notifications" --> Ops
  Graf -- "Query metrics" --> Prom
  Graf -- "Query logs" --> Loki
  Graf -- "Query traces" --> Tempo

  style API fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Ingest fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Collector fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Prom fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
  style Alert fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
  style Loki fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
  style Tempo fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
  style Graf fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Ops fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
```

Notes:

- Ingestion is ephemeral and must call exporter `force_flush()/shutdown()` before exit.
- Correlation IDs (`trace_id`, `span_id`, `request_id` or `run_id`) are required for joins.
