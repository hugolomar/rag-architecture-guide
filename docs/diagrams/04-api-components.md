# API components

C4 level 3, inside the RAG API container from the container diagram. The process is stateless. It accepts a question plus `Authorization: Bearer <token>`, and it returns an answer. The caller does not send their groups.

FastAPI is the HTTP boundary where input is validated. Group resolution, retrieval, and generation sit behind it. The evaluation harness calls the retrieval and generation ports directly without going through HTTP.

The query is embedded with FastEmbed, with the same transforms ingestion used for a query (ADR 0005). Retrieval passes the caller's groups to Qdrant. Qdrant applies that intersection, and the lifecycle filter, before it returns candidates (ADR 0006). Generation sees only that evidence. The generation adapter uses LiteLLM in-process and calls Gemini Flash as the initial provider (ADR 0008). API components emit OTLP telemetry through an exporter component toward the OpenTelemetry Collector (ADR 0011 and ADR 0012).

The ports are `retrieve_fn(query, user_id, top_k=3)` and `generate_fn(query, context_doc_ids, user_id)`. They are `abc.ABC` implementations. The data that crosses them is a Pydantic model (ADR 0004).

---

## 1. Core query pipeline (functional view)

This view shows the linear sequence of internal processing stages when a query is executed, isolating the business flow from auxiliary telemetry sinks and harness infrastructure.

```mermaid
graph LR
  User["Employee<br/>POST /query"] --> HTTP["1. HTTP boundary<br/>FastAPI / Pydantic<br/>Validates schema"]
  HTTP --> Identity["2. Identity resolution<br/>Validates OIDC token<br/>Resolves user groups"]
  Identity --> Vectors["3. Query vectorization<br/>FastEmbed: Dense + BM25<br/>Matches ingestion transforms"]
  Vectors --> Retrieve["4. Retrieval port<br/>retrieve_fn<br/>Hybrid search & security trimming"]
  Retrieve --> Prompt["5. Context isolation<br/>Encloses evidence in markers<br/>Prevents prompt injection"]
  Prompt --> Generate["6. Generation port<br/>generate_fn<br/>LiteLLM / Gemini Flash"]
  Generate --> Response["7. Typed response<br/>ground_answer, deny_access,<br/>abstain, or clarify"]

  style HTTP fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Identity fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Vectors fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Retrieve fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Prompt fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Generate fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style User fill:#08427b,stroke:#052e56,color:#ffffff,stroke-width:2px
  style Response fill:#08427b,stroke:#052e56,color:#ffffff,stroke-width:2px
```

---

## 2. Component and integration topology (structural view)

This view shows all internal components alongside external systems, identity authorities, data stores, evaluation entry points, and observability sinks (ADR 0005–ADR 0013).

```mermaid
graph TD
  subgraph API["RAG API · Python 3.14 / FastAPI · stateless"]
    HTTP["HTTP<br/>Accepts the question and bearer token<br/>Validates the request"]
    Identity["Token validation<br/>Groups from token claims"]
    Vectors["Query vectors<br/>FastEmbed<br/>Same transforms as ingestion"]
    Retrieve["Retrieval port<br/>retrieve_fn"]
    Generate["Generation port<br/>generate_fn"]
    Gateway["LiteLLM client<br/>In-process adapter"]
    Telemetry["Telemetry exporter<br/>OTLP traces, metrics, logs"]
  end

  Employee["Employee"]
  Harness["Evaluation harness<br/>pytest"]
  IdP["Identity provider<br/>OIDC/JWKS authority<br/>Keycloak local, enterprise IdP in production"]
  Qdrant[("Qdrant<br/>Filters by allowed_groups and status")]
  LLM["LLM provider<br/>Initial: Gemini Flash via AI Studio"]
  OTel["OpenTelemetry Collector"]
  LF["Langfuse<br/>AI semantic traces and prompt governance"]

  Employee -- "Asks a question" --> HTTP
  HTTP -- "Resolves the caller" --> Identity
  Identity -- "Validates token and reads claims" --> IdP
  HTTP -- "Embeds the question" --> Vectors
  Identity -- "Passes the caller's groups" --> Retrieve
  Vectors -- "Passes the query vectors" --> Retrieve
  Retrieve -- "Queries within the caller's groups" --> Qdrant
  Retrieve -- "Passes only surviving evidence" --> Generate
  Generate -- "Passes payload to LiteLLM" --> Gateway
  Gateway -- "Calls provider with surviving evidence" --> LLM
  Generate -- "Returns the answer" --> HTTP
  HTTP -- "Returns the answer" --> Employee
  Harness -- "Calls retrieve_fn" --> Retrieve
  Harness -- "Calls generate_fn" --> Generate
  HTTP -- "Emits request telemetry" --> Telemetry
  Retrieve -- "Emits retrieval telemetry" --> Telemetry
  Generate -- "Emits generation telemetry" --> Telemetry
  Telemetry -- "Exports OTLP signals" --> OTel
  Generate -- "Sends prompt/version and response metadata" --> LF

  style HTTP fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Identity fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Vectors fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Retrieve fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Generate fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Gateway fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Telemetry fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Harness fill:#438dd5,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Employee fill:#08427b,stroke:#052e56,color:#ffffff,stroke-width:2px
  style IdP fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Qdrant fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
  style LLM fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style OTel fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style LF fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
```
