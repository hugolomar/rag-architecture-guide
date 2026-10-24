# ADR 0016: Production Feedback Loop to Dataset

- Status: Proposed
- Date: 2026-10-23

## Context

The project has evaluation suites and quality gates (note 03, ADR 0014) plus runtime and AI
observability (ADRs 0011-0013). It needs a formal process to convert production failures and low
confidence traces into durable regression cases without leaking protected benchmark content.

## Decision

Adopt a governed feedback-to-dataset loop.

### 1) Feedback intake sources

- runtime traces flagged for low confidence or unexpected behavior,
- user complaints and explicit negative feedback,
- incident tickets for leakage, wrong grounding, or denial/abstention errors.

### 2) Case creation rules

- Each accepted incident becomes at least one new structured case with known user context and
  expected behavior.
- New cases are first added to `dev_set` for local fixing.
- A sibling regression case (not used for tuning) is promoted to `val_set` after fix validation.
- Sensitive hold-out additions go to protected suite management path, not versioned repository
  files.

### 3) Anti-overfitting controls

- Cases that directly guided a fix are not copied verbatim into protected release hold-out.
- Protected additions require wording or user-context variation from tuned cases.
- Case provenance metadata records origin and promotion decisions.

### 4) Data-handling rules

- Incident-derived cases redact sensitive content according to ADR 0009 and ADR 0011.
- For restricted evidence, case artifacts keep identifiers and behavior expectations, not raw text.

## Rationale

- Production feedback closes the loop between real failures and pre-release regression defense.
- Structured promotion from dev to val to protected balances speed, reliability, and overfitting
  resistance.
- Provenance metadata improves auditability of why a case exists and where it belongs.

## Alternatives Considered

1. **No formal feedback loop**
   - Pros: less process overhead.
   - Cons: repeated incidents and weak learning retention.
   - Rejected.

2. **Directly add all incidents to protected hold-out**
   - Pros: stricter release test growth.
   - Cons: quickly contaminates hold-out with tuning knowledge.
   - Rejected.

3. **Only dashboard monitoring, no dataset updates**
   - Pros: simpler operations.
   - Cons: quality gates do not evolve with observed failure modes.
   - Rejected.

## Consequences

- **Positive:** incidents become durable regression protection.
- **Positive:** clearer governance of suite evolution and hold-out integrity.
- **Negative:** added triage overhead for case curation and promotion.
- **Boundary:** this ADR does not define CI platform/job mechanics.
- **Follow-up:** ADR 0017 defines Jenkins pipeline stages that enforce this lifecycle.
