# ADR 0014: Evaluation Stack and Tooling Boundaries

- Status: Proposed
- Date: 2026-10-23

## Context

ADR 0013 defines quality-gate policy, but does not assign tooling per evaluation phase. The project
requires strict phase separation: deterministic retrieval/security checks first, semantic generation
assessment second.

## Decision

Define tooling boundaries by phase.

### 1) Phase 1 (retrieval/security) tooling

- Use `pytest` + project harness (`evals/harness.py`) only.
- Keep phase 1 deterministic and provider-agnostic.
- Evaluate by explicit ids/sets and boolean assertions (expected/prohibited/indexed behavior).
- Do not use LLM-as-a-judge tools in phase 1.

### 2) Phase 2 (generation/semantic) tooling

- Adopt **RAGAS** as semantic evaluator for phase-2 metrics.
- Use RAGAS to score groundedness/faithfulness, answer relevance, and citation consistency.
- Calibrate RAGAS prompts/rubrics against a reviewed sample before enforcing thresholds.

### 3) Boundary rules

- Phase 1 pass/fail must not depend on model-judge outputs.
- Phase 2 metrics must not override hard security failures from phase 1.
- Tool outputs are recorded as artifacts and linked to `trace_id`/`test_id` where available.

## Rationale

- Deterministic retrieval evaluation avoids circular dependency on generative judges.
- RAGAS provides semantic signal where deterministic checks are insufficient (answer quality).
- Strict boundary prevents semantic scores from masking access-control or lifecycle failures.

## Alternatives Considered

1. **RAGAS in both phases**
   - Pros: one framework.
   - Cons: phase-1 non-determinism and root-cause ambiguity.
   - Rejected.

2. **No semantic evaluator, deterministic checks only**
   - Pros: simple and reproducible.
   - Cons: weak coverage of generation quality and groundedness nuances.
   - Rejected.

3. **DeepEval as primary phase-2 tool**
   - Pros: strong testing integrations and safety scenarios.
   - Cons: not selected as primary phase-2 semantic baseline for this project stage.
   - Deferred.

## Consequences

- **Positive:** clear phase ownership and reproducible retrieval diagnostics.
- **Positive:** semantic quality is measured with an explicit phase-2 tool.
- **Negative:** calibration and rubric maintenance effort for RAGAS.
- **Boundary:** this ADR does not define CI platform implementation details.
- **Follow-up:** ADR 0015 defines production feedback ingestion into suite evolution.
