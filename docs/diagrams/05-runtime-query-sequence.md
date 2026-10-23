# Runtime query sequence

Sequence view for one interactive query. This diagram complements container/component views by
showing execution order and security gates from ADR 0007, ADR 0008, and ADR 0009.

The caller sends `X-User-Id` and query text. The API validates input, resolves caller groups, and
builds query vectors. Qdrant applies `allowed_groups` and lifecycle status filters before returning
candidates. Generation uses only that surviving evidence through LiteLLM to Gemini.

```mermaid
sequenceDiagram
  actor U as Employee
  participant API as FastAPI runtime
  participant IdP as Identity resolver
  participant V as FastEmbed (query)
  participant Q as Qdrant
  participant G as Generation adapter
  participant L as LiteLLM (in-process)
  participant M as Gemini provider

  U->>API: POST /query (X-User-Id, query, top_k?)
  API->>API: Validate request (422 on schema/limits)
  API->>IdP: Resolve caller from X-User-Id
  IdP-->>API: user_id + user_groups (401 on unknown)
  API->>V: Build query dense+sparse vectors
  V-->>API: query vectors
  API->>Q: Hybrid query + filters (allowed_groups,status)
  Q-->>API: retrieved_doc_ids (already trimmed)
  API->>G: generate_fn(query, context_doc_ids, user_id)
  G->>L: completion request
  L->>M: provider call with surviving evidence
  M-->>L: completion
  L-->>G: normalized response
  G-->>API: answer + behavior + citations
  API-->>U: 200 OK (ground_answer|deny_access|abstain|clarify)

  Note over API,Q: Any prohibited document in retrieved context is a hard failure in eval gates.
  Note over API,M: Upstream provider/dependency failures map to 502/504.
```
