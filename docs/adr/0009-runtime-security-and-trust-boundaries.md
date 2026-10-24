# ADR 0009: Runtime Security and Trust Boundaries

- Status: Accepted
- Date: 2026-10-23

## Context

The project already defines governed retrieval and evaluation behavior across notes 02-03 and ADRs
0003, 0006, 0007, and 0008. Security rules exist, but they are distributed and not yet recorded as
a single runtime security decision.

The system retrieves governed evidence and then calls an external LLM provider. Security must be
deterministic and enforced before generation, not delegated to model behavior.

## Decision

Adopt a zero-trust runtime posture with deterministic pre-inference controls.

- **Pre-inference security trimming is mandatory.** Only documents whose `allowed_groups` intersect
  caller groups can become model context. `department` and `classification` are attributes, not
  access grants.
- **Identity context is system-resolved.** Runtime caller groups come from the token `groups` claim
  (ADR 0010). Deterministic suites still resolve them from `user_id` via the identity fixture.
  Request text and retrieved content do not change caller groups.
- **Identity tokens are validated before orchestration.** Bearer tokens must pass issuer, audience,
  signature, and expiry checks (ADR 0010) before user context enters retrieval.
- **Lifecycle enforcement is part of runtime filtering.** Retrieval excludes `archived` content and
  keeps `current`/`deprecated` behavior consistent with governed rules.
- **Model context is untrusted data.** Retrieved chunks are treated as data, never as executable
  instructions for changing access behavior or trust boundaries.
- **Zero-leak gates are release criteria.** Any `prohibited_doc_ids` hit in retrieval context or
  `prohibited_answer_keywords` hit in answer output is a hard failure.
- **Secret material never lives in source.** API keys and provider credentials are externalized from
  repository files and managed through environment/secret-management mechanisms.

## Rationale

- Deterministic filters are auditable and testable, unlike model-only policy following.
- Identity authority must stay in system components to prevent caller-side privilege escalation.
- Treating retrieved context as untrusted mitigates indirect prompt-injection pathways.
- Explicit leak gates align security checks with existing evaluation harness semantics.
- Secret separation reduces accidental key exposure and credential sprawl in local and CI workflows.

## Alternatives Considered

1. **Model-mediated authorization**
   - Pros: minimal retrieval-layer logic.
   - Cons: non-deterministic access control and unacceptable leakage risk.
   - Rejected.

2. **Caller-supplied groups as authority**
   - Pros: simpler request handling.
   - Cons: trust boundary violation and privilege-escalation risk.
   - Rejected.

3. **Post-generation redaction as primary access control**
   - Pros: easier retrofit in some architectures.
   - Cons: sensitive context already exposed to model/provider before redaction.
   - Rejected.

4. **Inline secrets in repo/config files**
   - Pros: setup convenience.
   - Cons: high leakage risk and poor operational hygiene.
   - Rejected.

## Consequences

- **Positive:** runtime security behavior is explicit, deterministic, and testable.
- **Positive:** trust boundaries remain consistent across retrieval, generation, and evaluation.
- **Negative:** stricter filtering can reduce apparent answer coverage for unauthorized callers.
- **Negative:** secret-management setup becomes a required operational dependency.
- **Boundary:** this ADR does not choose a specific secret manager, observability backend, or
  production identity provider implementation.
- **Follow-up:** observability ADR should define safe audit fields for denied/trimmed evidence
  without logging restricted content.
