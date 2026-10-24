# ADR 0008: LLM Provider and Gateway Strategy

- Status: Accepted
- Date: 2026-10-23

## Context

ADR 0007 defines API orchestration and HTTP contract semantics, but leaves LLM provider and gateway
product open. The project needs an initial generation path that is low-cost for development and
evaluation while preserving adapter boundaries from ADR 0003 and ADR 0004.

The runtime orchestration must stay unchanged:

- retrieval filters access and lifecycle before generation (ADR 0006),
- generation receives only surviving evidence,
- upstream generation failures map to HTTP `502`/`504` (ADR 0007).

## Decision

Use **LiteLLM as an in-process library** in the generation adapter, with **Google AI Studio
Gemini Flash** as the initial provider for development and evaluation.

- LiteLLM runs inside the API process. No standalone proxy container is introduced at this stage.
- The API orchestration continues to call the generation port contract, not provider SDK types.
- The concrete Gemini model identifier is configuration-driven and may change as AI Studio updates
  free-tier model availability.
- Provider limits are read from the active AI Studio project settings. Hardcoded RPM/RPD values are
  not part of this ADR.

## Rationale

- LiteLLM provides one client interface while preserving domain-port decoupling in orchestration.
- In-process usage avoids extra network hops and infrastructure complexity of a dedicated proxy.
- Gemini free tier provides a practical managed starting point for local development and eval runs.
- Keeping model id and provider settings in configuration reduces code churn during provider/model
  experiments.

## Alternatives Considered

1. **Direct Gemini client (no gateway library)**
   - Pros: smallest dependency surface.
   - Cons: provider-specific client logic remains in the adapter and is repeated for each provider.
   - Rejected for the default path.

2. **LiteLLM proxy as separate service**
   - Pros: centralized policy enforcement across multiple services.
   - Cons: extra service/process before multi-service scale exists.
   - Deferred.

3. **DeepSeek as initial provider**
   - Pros: low-cost pricing.
   - Cons: not a guaranteed free-tier baseline for this stage.
   - Rejected for initial dev/eval baseline.

4. **Local-only LLM provider**
   - Pros: no external data transfer.
   - Cons: less predictable quality baseline for current evaluation cadence.
   - Deferred for dedicated local-provider experiments.

## Consequences

- **Positive:** provider swaps can happen in adapter/config with minimal orchestration change.
- **Positive:** no extra proxy container is required now.
- **Negative:** generation payloads leave the system when using managed providers. A local model would keep that text inside.
- **Negative:** free-tier behavior and quotas are provider-managed and can change.
- **Security note:** managed free tiers may use submitted content according to provider terms.
- **Boundary:** this ADR does not choose production authentication, observability backend, or
  long-term production provider policy.
- **Follow-up:** define runtime security posture for managed providers and secret handling in the
  security ADR.
