# Evaluation Case Curation From Production Signals

**Status:** Draft operational guide
**Scope:** Real-project operation once runtime traffic exists

This guide defines how a production failure becomes a durable evaluation case without leaking
restricted content or contaminating the protected hold-out.

## 1) Intake sources

Accept signals from:

- runtime traces flagged for low confidence or unexpected behavior,
- user complaints and explicit negative feedback,
- incident tickets for leakage, wrong grounding, or deny/abstain mismatch.

## 2) Case creation and promotion

1. Create at least one structured case with known user context and expected behavior.
2. Add the first case to `evals/suites/dev_set.json` and fix there.
3. Add a sibling case to `evals/suites/val_set.json` that was not used to tune the fix (change
   wording and/or user context while keeping the same failure class).
4. If the failure class must be represented in hold-out, add a separate protected case through the
   protected-suite management path, never by copying the tuned case verbatim.

## 3) Anti-overfitting controls

- Cases that directly guided a fix are not copied into the protected hold-out.
- Protected additions require variation from tuned cases.
- Promotion decisions record provenance (origin signal, tuned set, sibling set, hold-out decision).

## 4) Restricted-data handling

- Apply redaction rules from ADR 0009 and ADR 0011.
- For restricted evidence, keep identifiers and expected behavior only; do not copy raw text into
  versioned suite files.
- CI logs and case-review artifacts must not print secrets or restricted payloads.

## 5) Guardrails

- A case that references an unknown `doc_id` or unknown user is invalid and must be rejected.
- New docs/groups must be added to `data/manifest.json` and identity fixtures/IdP seed before case
  promotion.
- This guide does not redefine quality gates. Gate semantics remain in ADR 0014.
