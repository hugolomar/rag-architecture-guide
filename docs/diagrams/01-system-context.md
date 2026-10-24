# System context

C4 level 1. The governed RAG is the system being built. People and external systems sit outside it. The evaluation harness is inside the system, so it does not appear here.

Access is granted by groups. Document text and governance arrive from different places. In this repository those places are `data/raw/` and `data/manifest.json`. Generation uses LiteLLM in-process with Gemini Flash as the initial provider (ADR 0008). AI-semantic traces and prompt governance are handled by Langfuse (ADR 0013).

```mermaid
graph TD
  Employee["Employee<br/>Member of the organization"]
  RAG["Governed RAG<br/>Access-aware retrieval and answers"]

  IdP["Identity provider<br/>OIDC token issuer and group authority"]
  Docs["Document sources<br/>Document text"]
  Catalog["Governance catalog<br/>allowed_groups, status, ownership"]
  LLM["LLM provider<br/>Initial: Gemini Flash via AI Studio"]
  LF["Langfuse<br/>AI observability and prompt governance"]

  Employee -- "Asks a question and receives an answer" --> RAG
  RAG -- "Validates bearer token and resolves caller groups" --> IdP
  Docs -- "Supplies document text" --> RAG
  Catalog -- "Supplies access and lifecycle" --> RAG
  RAG -- "Sends only evidence the caller may see" --> LLM
  RAG -- "Sends semantic traces and prompt metadata" --> LF

  style RAG fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px
  style Employee fill:#08427b,stroke:#052e56,color:#ffffff,stroke-width:2px
  style IdP fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Docs fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Catalog fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style LLM fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style LF fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
```
