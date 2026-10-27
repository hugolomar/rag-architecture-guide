# ADR 0004: Strict Domain Modeling and Validation in Python

- Status: Accepted
- Date: 2026-10-20

## Context

ADR 0003 defines shared domain contracts and adapter boundaries. Python provides type hints but does
not enforce full structural validity or nominal subtyping at runtime by itself. In a governed
enterprise RAG pipeline, malformed metadata, boundary payload drift, or accidental structural
matches can silently break security trimming and lifecycle behavior.

The project needs a strict mechanism to define:

- infrastructure-agnostic behavioral ports,
- strict domain data models,
- runtime validation of payloads entering the shared domain.

## Decision

Use **`abc.ABC` ports** plus **Pydantic v2 domain models** as the default modeling pattern.

- All contracts that cross a layer boundary are defined with `abc.ABC` and `@abstractmethod`.
  This includes the core behavioral ports and any other contract between domain, adapter, and
  infrastructure layers. `typing.Protocol` is not used for cross-layer contracts.
- Adapters must explicitly inherit from those domain ports.
- Domain entities and boundary payloads use Pydantic models with explicit fields and validation.
- Security/governance fields are required in validated models where applicable (`doc_id`,
  `allowed_groups`, lifecycle status, and identity context).
- Adapter boundaries validate and normalize external payloads into domain models before they enter
  orchestration logic.

## Rationale

- `abc.ABC` enforces explicit nominal commitment to architecture contracts across all layer
  boundaries, not only for the core retrieval and generation ports. In a governed enterprise
  pipeline, a class that happens to expose methods of the same name can silently satisfy a contract
  without ever intending to, and without any runtime error until traffic exposes the gap. The cost
  of explicit inheritance is accepted in exchange for that guarantee.
- It prevents accidental structural matches where a class happens to expose similar method names but
  is not intended to satisfy the port.
- Violations surface at instantiation time for incomplete implementations, before runtime traffic.
- Pydantic provides strict runtime parsing and validation, which directly mitigates accidental
  integration errors and field drift in dynamic Python code.
- The combination separates behavioral contracts (ports) from data correctness (models), matching
  the repository's evaluation-first approach.
- The current toolchain already includes Python 3.14 and modern package management, making this
  approach straightforward to operationalize.

## Alternatives Considered

1. **Protocol-based ports (`typing.Protocol`)**
   - Pros: flexible structural typing; low adapter ceremony.
   - Cons: weaker runtime architectural guardrails; easier accidental structural matches; a
     structural match can satisfy a contract silently, which in a governed pipeline means a
     security boundary can appear valid without nominal commitment.
   - Rejected for all cross-layer contracts in this project.

2. **Native classes only**
   - Pros: minimal dependencies; lowest initial ceremony.
   - Cons: weak runtime validation; higher risk of silent field drift.
   - Rejected.

3. **`dataclasses` only**
   - Pros: lightweight standard-library models.
   - Cons: no strict runtime coercion/validation by default; custom validators required everywhere.
   - Rejected as the primary pattern.

4. **Marshmallow schemas**
   - Pros: mature serialization/validation ecosystem.
   - Cons: schema layer is separate from Python typing model used by application code.
   - Rejected for this codebase, which prioritizes typed models in code.

5. **`attrs` with validators**
   - Pros: flexible model definition and validation hooks.
   - Cons: additional design surface without clear advantage over Pydantic for this project scope.
   - Rejected for this iteration.

## Consequences

- **Positive:** runtime payload errors surface early at boundaries, before retrieval/generation
  logic consumes invalid data.
- **Positive:** domain contracts stay explicitly governed across adapters.
- **Negative:** adds model/validation ceremony, explicit inheritance coupling, and a small runtime
  validation cost.
- **Mitigation:** keep models focused on boundary and invariant checks, and avoid over-modeling
  transient internal values.
