# ADR 0014: Evaluation Governance and Quality Gates

- Status: Accepted
- Date: 2026-10-23

## Context

Note 03 defines evaluation-first development and suite partitioning (`dev`, `val`, `protected`).
ADRs 0007-0010 define API semantics and security invariants. ADR 0013 adds AI observability. The
project now needs explicit quality-gate policy for pull requests, mainline integration, and release.

## Decision

Adopt a multi-gate evaluation policy with hard security and behavior blockers.

### 1) Gate layers

- **Development gate (local):** `dev_set` is the daily iteration suite and may fail during feature
  development.
- **Pull request gate:** `val_set` is mandatory and blocks merge on hard-failure criteria.
- **Release gate:** `protected_set` is mandatory in CI with protected-path injection and blocks
  release on any hard-failure criterion.

### 2) Hard-blocking criteria

Any of the following fails the gate immediately:

- retrieval contains any `prohibited_doc_ids`,
- generated answer contains any `prohibited_answer_keywords`,
- missing `expected_doc_ids` for applicable stages,
- behavior mismatch against case expectation (`ground_answer`, `deny_access`, `abstain`, `clarify`),
- contract/schema drift in API response shape.

### 3) Informational criteria

These are tracked and alerted but are not blocking by default:

- latency regressions,
- cost/token increases,
- non-critical output-style shifts that do not violate behavior/security rules.

Thresholds for informational metrics are versioned and reviewed periodically.

### 4) Protected suite policy

- `protected_set` remains out of repository indexing and is injected by CI path configuration.
- Local runs may skip protected suite by design.
- Release pipelines must set protected-suite-required mode.

## Rationale

- Split gates preserve iteration speed while enforcing strong regression controls before release.
- Hard blockers reflect governed-RAG invariants where a single leak is unacceptable.
- Keeping cost/latency initially informational avoids blocking beneficial quality improvements while
  preserving visibility.
- Protected suites reduce benchmark overfitting pressure on both humans and coding agents.

## Alternatives Considered

1. **Single unified gate for all stages**
   - Pros: simpler pipeline.
   - Cons: slows local iteration and mixes tuning with release assurance.
   - Rejected.

2. **One average score as the only gate**
   - Pros: simple dashboard metrics.
   - Cons: can hide severe security failures under average improvements.
   - Rejected.

3. **No protected release suite**
   - Pros: less CI complexity.
   - Cons: higher overfitting and weaker final assurance.
   - Rejected.

## Consequences

- **Positive:** clear, enforceable governance for evaluation outcomes.
- **Positive:** explicit separation between blocking and informational signals.
- **Negative:** three suites and separate blocking and informational signals make the evaluation pipeline more complex than a single pass/fail score.
- **Negative:** release pipeline needs secret/protected suite provisioning.
- **Boundary:** this ADR does not choose phase-2 semantic scoring tooling details.
- **Follow-up:** ADR 0015 defines phase-specific tooling and metric interpretation.
