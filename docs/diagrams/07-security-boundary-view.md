# Security boundary view

Trust-boundary view for runtime security from ADR 0009. It highlights which component is authority
for identity, which component enforces document-level access, and where external-provider exposure
starts.

```mermaid
graph TD
  User["Caller"]

  subgraph Runtime["RAG API runtime"]
    HTTP["HTTP boundary<br/>Input validation"]
    Auth["Identity resolution<br/>from bearer token"]
    Retrieve["Hybrid retrieval orchestration"]
    Generate["Generation adapter"]
    Lite["LiteLLM in-process"]
  end

  IdP["Identity source<br/>users/groups authority"]
  Qdrant[("Qdrant<br/>Policy enforcement<br/>allowed_groups + status")]
  LLM["Managed provider<br/>Gemini (initial)"]

  User --> HTTP
  HTTP --> Auth
  Auth --> IdP
  Auth --> Retrieve
  Retrieve --> Qdrant
  Retrieve --> Generate
  Generate --> Lite
  Lite --> LLM

  classDef trusted fill:#1168bd,stroke:#0b4884,color:#fff,stroke-width:2px;
  classDef control fill:#229954,stroke:#114d2a,color:#fff,stroke-width:2px;
  classDef external fill:#999999,stroke:#666666,color:#fff,stroke-width:2px;
  classDef store fill:#f68a1e,stroke:#c46e18,color:#fff,stroke-width:2px;

  class HTTP,Auth,Retrieve,Generate,Lite trusted;
  class Qdrant control;
  class User,IdP,LLM external;
  class Qdrant store;
```

Security invariants:

- Identity authority is bearer-token validation, not caller-supplied groups.
- Access control is deterministic at retrieval time, before generation.
- Generation only receives already-trimmed evidence.
- Provider exposure starts only after security trimming.
