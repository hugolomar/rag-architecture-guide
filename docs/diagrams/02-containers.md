# Containers

C4 level 2. These are the processes and data stores inside the governed RAG from the context diagram. People and external systems stay outside the boundary.

FastAPI is the decided HTTP runtime. Retrieval has two channels, and both live in Qdrant (ADR 0006). The dense vector finds a chunk by meaning. The sparse vector finds a written token, such as an option name, a flag, or an identifier. Stemming and the rest of the lexical analysis run in Python before a point is written (ADR 0005). Generation uses LiteLLM as an in-process library inside the API (ADR 0008). System observability follows ADR 0011 and ADR 0012: API and ingestion emit OTLP telemetry to an observability platform. Detailed telemetry internals are documented in diagram 08. There is no web UI in this system. The evaluation harness calls the same retrieval and generation ports as the API. It does not go through HTTP.

Ingestion reads document text and the governance catalog. It does not read the identity provider. Each chunk becomes one Qdrant point: dense vector, sparse vector, and governance payload. `deprecated` documents stay in the collection. `archived` documents are left out. The API validates bearer tokens and resolves groups from token claims. Qdrant applies that intersection, together with the lifecycle filter, before it returns candidates.

```mermaid
graph TD
  subgraph System["Governed RAG"]
    API["RAG API<br/>Python 3.14 / FastAPI<br/>Resolves the caller, retrieves, then generates"]
    Harness["Evaluation harness<br/>Python 3.14 / pytest<br/>Scores the same retrieval and generation ports"]
    Ingest["Ingestion<br/>Python 3.14, offline<br/>Parses Markdown, merges governance, chunks, builds both vectors"]
    Qdrant[("Qdrant<br/>Dense and sparse vectors, governance payload<br/>Filters by allowed_groups and status")]
    Langfuse["Langfuse<br/>AI semantic traces and prompt governance"]
    Observability["Observability platform<br/>Collector + Prometheus + Alertmanager + Loki + Tempo + Grafana"]
  end

  Employee["Employee"]
  IdP["Identity provider<br/>Keycloak (local) or enterprise IdP (prod)"]
  Docs["Document sources"]
  Catalog["Governance catalog"]
  LLM["LLM provider<br/>Initial: Gemini Flash via AI Studio"]

  Employee -- "Asks a question and receives an answer" --> API
  Harness -- "Calls retrieve_fn and generate_fn" --> API
  API -- "Validates bearer token and resolves groups" --> IdP
  API -- "Queries within the caller's groups" --> Qdrant
  API -- "Calls LiteLLM and sends surviving evidence" --> LLM
  API -- "Sends semantic traces and prompt metadata" --> Langfuse
  Docs -- "Supplies Markdown" --> Ingest
  Catalog -- "Supplies allowed_groups and status" --> Ingest
  Ingest -- "Indexes current and deprecated chunks" --> Qdrant
  API -- "Emits traces, metrics, logs (OTLP)" --> Observability
  Ingest -- "Emits traces, metrics, logs (OTLP)" --> Observability

  style API fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Harness fill:#438dd5,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Ingest fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Qdrant fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
  style Observability fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Langfuse fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Employee fill:#08427b,stroke:#052e56,color:#ffffff,stroke-width:2px
  style IdP fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Docs fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Catalog fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style LLM fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
```
