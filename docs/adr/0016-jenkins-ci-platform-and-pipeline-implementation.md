# ADR 0016: Jenkins CI Platform and Pipeline Implementation

- Status: Proposed
- Date: 2026-10-23

## Context

ADRs 0013-0015 define evaluation policy, phase tooling, and feedback-loop governance. The project
needs a concrete CI platform and pipeline structure to enforce those rules in automated checks.

## Decision

Use **Jenkins** as the CI platform for this project stage.

### 1) Pipeline stages

- **Stage A: integrity and static checks**
  - suite integrity tests,
  - schema/contract checks,
  - baseline lint/test sanity.

- **Stage B: PR validation gate**
  - run `val_set` phase-1 deterministic checks,
  - run phase-2 semantic checks (RAGAS subset/smoke profile),
  - fail on hard-blocking criteria from ADR 0013.

- **Stage C: mainline validation**
  - full `val_set` phase-1 + phase-2 run,
  - publish artifacts and trend metadata.

- **Stage D: release gate**
  - inject protected suite path via CI secret/config (`RAG_PROTECTED_SUITE_PATH`),
  - enforce protected-suite-required mode,
  - block release on any hard-failure rule.

### 2) Secret and protected-data handling

- Provider keys and protected suite path/contents are managed in Jenkins credentials, not repository.
- Jobs access secrets only in stages that require them.
- Build logs must avoid printing secret values or restricted-case contents.

### 3) Artifacts and traceability

- Persist machine-readable evaluation artifacts per run (phase results, gate outcomes, timings).
- Include correlation metadata (`build_id`, commit SHA, branch, suite id, optional `trace_id` links).
- Retain enough history for regression trend inspection and incident forensics.

## Rationale

- Jenkins provides mature staged pipelines and secret handling patterns suitable for mixed local/CI
  workflows.
- Explicit stage boundaries mirror evaluation governance boundaries from ADR 0013.
- Protected-suite injection via credentials preserves hold-out isolation from repository access.

## Alternatives Considered

1. **Tool-agnostic CI only (no platform decision)**
   - Pros: flexibility.
   - Cons: delayed operational enforcement and ambiguous implementation ownership.
   - Rejected.

2. **GitHub Actions as initial platform**
   - Pros: tight GitHub integration and simpler hosted setup.
   - Cons: not selected as current organizational CI baseline for this repository.
   - Rejected for this stage.

3. **Single-stage monolithic pipeline**
   - Pros: simple configuration.
   - Cons: poor visibility and weak separation of PR, mainline, and release controls.
   - Rejected.

## Consequences

- **Positive:** evaluation governance is enforceable in automated delivery flow.
- **Positive:** protected benchmark handling is explicit and isolated.
- **Negative:** Jenkins operational maintenance overhead.
- **Negative:** additional work to optimize build time and agent caching.
- **Boundary:** this ADR does not redefine gate semantics (ADR 0013) or evaluator role boundaries
  (ADR 0014).
- **Follow-up:** add concrete Jenkinsfile/job templates and credentials mapping documentation.
