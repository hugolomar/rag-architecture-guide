# ADR 0003: Shared Domain Contracts and Adapter Boundaries

- Status: Accepted
- Date: 2026-10-20

## Context

The repository defines governance and evaluation rules before implementation (notes 01, 02, and 03).
The next implementation phase needs stable domain contracts that do not depend on a specific vector
database, embedding provider, or LLM API.

Without an explicit shared domain, infrastructure choices can leak into application logic. This
causes accidental coupling, weakens security-trimming guarantees, and makes retrieval and generation
tests harder to reason about across provider changes.

## Decision

Define and maintain a **shared domain layer** as the source of truth for business semantics and
cross-layer contracts.

The shared objects are these:

- **Identity.** A caller is a `user_id`. The system resolves the caller's groups. The query does not
  supply them.
- **Governed document.** Identity is `doc_id`. The contract carries `allowed_groups`, `status`,
  `department`, and `classification` together. Only `allowed_groups` grants read access, by
  intersection with the caller's groups. `department` names the owner. `classification` names
  sensitivity. Neither grants access.
- **Lifecycle.** `current` is indexed. `deprecated` stays indexed. `archived` is omitted from the
  index.
- **Retrieved evidence and answer.** Retrieval returns evidence tied to those document identities.
  An answer carries one behavior: `ground_answer`, `deny_access`, `abstain`, or `clarify`. Those
  four stay distinct.

Closed catalogs, which document is readable by which groups, and the Python class names stay in the
project notes. ADR 0004 decides how these contracts are modeled.

- Infrastructure adapters (vector store, lexical index, model gateway, external APIs) must
  translate provider payloads into domain contracts at the boundary.
- Core domain contracts are provider-agnostic and do not encode vendor-specific response shapes.
- Security and lifecycle semantics are first-class fields in those contracts, not side channels.
- Runtime orchestration is allowed to depend on domain contracts and port interfaces only; it does
  not depend directly on provider SDK models.

## Rationale

- The domain already exists in the project notes: governance metadata, identity groups, lifecycle
  status, and behavior categories are explicit and testable.
- Treating vector DBs and LLMs as adapters preserves replaceability without rewriting business rules.
- Security trimming and freshness behavior become enforceable invariants of the application model,
  not optional post-processing.
- Evaluation cases score behavior against domain outcomes; stable contracts reduce ambiguity between
  retrieval defects and generation defects.

## Alternatives Considered

1. **Provider-first modeling**
   - Pros: faster start for one chosen stack.
   - Cons: provider payloads become de facto domain models; hard to swap infrastructure later.
   - Rejected.

2. **Thin wrappers over provider payloads**
   - Pros: low initial code volume.
   - Cons: hidden coupling remains; governance fields are inconsistently represented.
   - Rejected.

3. **Single monolithic runtime model**
   - Pros: fewer object types at first.
   - Cons: weak boundaries between ingestion, retrieval, and generation responsibilities.
   - Rejected.

## Consequences

- **Positive:** infrastructure can change while preserving behavior contracts and evaluation rules.
- **Positive:** security and lifecycle invariants are explicit in the same objects used by runtime
  orchestration and tests.
- **Negative:** requires up-front design discipline and explicit model ownership.
- **Follow-up:** the next ADR defines strict modeling and validation mechanisms in Python for these
  contracts and ports.
