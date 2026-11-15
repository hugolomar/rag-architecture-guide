---
description: Critical evaluation governance rule prohibiting reading or indexing hold-out secrets inside evals/.secrets/
trigger: always_on
---

# Hold-Out Evaluation Suite Boundary

The directory `evals/.secrets/` (specifically `protected_set.json`) is the hold-out test set reserved strictly for automated release quality gates (Constitution Article 9, ADR 0014, Note 03).

## Mandatory Invariant for AI Agents:
- Never read, grep, index, cite, or search files within `evals/.secrets/`.
- Never inspect `protected_set.json` or use its contents to tune retrieval, prompts, chunking, or implementation code.
- Rely exclusively on open development suites (`evals/suites/dev_set.json` and `evals/suites/val_set.json`) for local evaluation and testing.

