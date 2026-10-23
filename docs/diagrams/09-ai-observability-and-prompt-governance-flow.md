# AI observability and prompt governance flow

Semantic AI tracing and prompt-governance flow from ADR 0012.

```mermaid
sequenceDiagram
  actor U as Employee
  participant API as FastAPI orchestration
  participant RET as Retrieval path
  participant PROMPT as Prompt registry and versioning
  participant GEN as Generation adapter
  participant LLM as LiteLLM + Gemini
  participant LF as Langfuse
  participant FB as User feedback

  U->>API: Query + X-User-Id
  API->>RET: Retrieve filtered evidence
  RET-->>API: doc_ids/chunk_ids + ranking metadata
  API->>PROMPT: Resolve prompt version/tag
  PROMPT-->>API: Prompt template metadata
  API->>GEN: generate_fn(query, context_doc_ids, user_id)
  GEN->>LLM: Completion request
  LLM-->>GEN: Completion response + usage
  GEN-->>API: answer + behavior + citations
  API-->>U: Response

  API->>LF: Trace query metadata + retrieval ids + prompt version + model usage
  GEN->>LF: Trace generation metadata + latency + token usage
  FB->>LF: Thumbs up/down + optional note

  Note over LF: Store metadata-only for denied/trimmed evidence.
  Note over LF: Apply redaction policy for sensitive prompt/response fields.
```

Captured dimensions:

- Query and correlation identifiers
- Retrieval identifiers and ranking metadata
- Prompt version/tag and release stage
- Provider/model/latency/token usage
- Output behavior classification and user feedback
