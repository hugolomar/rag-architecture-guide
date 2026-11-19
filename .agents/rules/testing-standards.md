---
description: Mandatory standards for authoring, structuring, and maintaining pytest test suites across unit, contract, and integration tiers
trigger: model_decision
---

# Testing Standards and Suite Quality Invariants

All test code in this repository must strictly adhere to these standards to ensure determinism, maintainability, and clean segregation.

## 1. Suite Categorization & Pytest Markers
- Every test file in `tests/` must declare its test tier at module level using `pytestmark`:
  ```python
  pytestmark = pytest.mark.unit  # or pytest.mark.contract, pytest.mark.integration
  ```
- Tests must strictly live in their corresponding directory (`tests/unit/`, `tests/contract/`, `tests/integration/`).
- The three test pyramid tiers (`unit`, `contract`, `integration`) are strictly reserved for test code under `tests/`. Evaluation suite markers (`dev`, `validation`, `release_gate`, and behavioral category markers like `hybrid_search`, `security_rbac`) belong strictly to the dynamic RAG evaluation harness in `evals/` and must never be applied as module test tiers in `tests/`.
- Any custom pytest marker must be declared in `pyproject.toml` under `[tool.pytest.ini_options] markers`.

## 2. Visual Section Headers
- Organize tests logically into visually distinct sections using 42-character comment dividers:
  ```python
  # ==========================================
  # SECTION NAME (e.g. Happy Path, Boundary Edge Cases)
  # ==========================================
  ```

## 3. Strict Exception Assertions (Ruff PT011)
- Never use bare broad exceptions in `pytest.raises()` (e.g., `ValueError`, `TypeError`).
- Always specify the regex pattern with `match=`:
  ```python
  with pytest.raises(ValueError, match="min_chunk_size must be >= 1"):
      ...
  ```

## 4. Test Data Strategy: Helpers vs. Fixtures
- **Factory Helpers (`_build_...`)**: Prefer plain, in-memory helper functions for constructing domain objects or dynamic data variants with clear defaults.
- **Fixtures (`@pytest.fixture`)**: Reserve strictly for lifecycle management, shared external resources, or dependency injection across multiple tests.
- **Fixture Scope**: Use `scope="module"` for expensive I/O-bound setup (loading files from disk, parsing manifests, initializing embedder models) shared across tests in a single module. Default function scope for everything else.
- Keep tests **DAMP** (Descriptive And Meaningful Phrases) rather than overly DRY. Avoid unneeded abstraction layers or lambdas inside tests.

## 5. Schema Validation in Tests
- When validating structured data (JSON manifests, config files) against Pydantic models, prefer batch validation via `TypeAdapter` over manual field-by-field assertions:
  ```python
  adapter = TypeAdapter(list[ManifestRecord])
  records = adapter.validate_python(raw_data)  # fails loud on schema violations
  ```
- This eliminates redundant assertions that merely re-check what Pydantic already enforces and keeps test intent focused on behavioral invariants (e.g., missing files, partition counts).

## 6. Boundary Partitions & Parametrization
- Use `@pytest.mark.parametrize` for boundary value testing (regex validation, partition equivalence, invalid payloads).
- Never introduce unused parameters into test signatures.

## 7. Zero Legalistic Noise in Tests
- **Test Names & Docstrings**: Name tests and describe their intent strictly based on the technical behavior, edge case, or invariant being verified (e.g., `test_rejects_missing_manifest_entry`, `test_excludes_archived_documents`).
- **No Governance Citations**: Never cite `Constitution Article X`, requirement tickets (`FR-XXX`), or story identifiers (`USX`) in test function names, docstrings, or module comments. Tests test runtime behavior, not ticket tracking.

## 8. Heavy Artifacts & Offline Determinism in Integration Tests
- Integration tests requiring heavy binary artifacts (e.g. local ONNX models, embedding weights >100MB) must run deterministically and must never hang indefinitely on socket timeouts.
- When executing in offline or sandboxed environments where weights are absent from local cache:
  - Tests must eagerly probe artifact availability and gracefully invoke `pytest.skip()` with an explicit, actionable message instructing how to warm up the cache (`Run 'bash scripts/warmup_models.sh' to download`).
  - Tests must never block CI runners or local development workflows on unhandled network errors.

## 9. In-Memory Test Doubles for Workflow Orchestrators
- Application workflow orchestrators and CLI entrypoints must be verified at the unit tier using pure in-memory test doubles that nominally inherit from domain port contracts (e.g., `EmbedderPort`, `ChunkStorageWriterPort`).
- This ensures 100% deterministic coverage of orchestration logic, lifecycle state transitions, and OpenTelemetry instrumentation in microsecond unit runs, completely decoupled from external network access, storage services, or heavy machine learning weights.


