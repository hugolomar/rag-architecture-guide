# Note 06: Architectural verification boundaries, linters, and contract tests

**Date:** 2026-11-12 · **Status:** decided

In accordance with Constitution Articles 2, 4, 18, and 19 (ratified in Constitution v1.2.2) and ADR 0016, this note records the official technical separation of responsibilities for architectural verification: which structural concerns belong to static import linters (`import-linter`), which belong to executable contract tests (`pytest` + `inspect`), and how automated quality gates enforce these boundaries in local development and CI.

---

## 1. Context and Problem Statement

The repository enforces clean hexagonal architecture. However, an initial implementation of architectural contract tests attempted to verify both layer dependency directions and class inheritance inside `tests/contract/test_architecture_contracts.py` using Python's standard `ast` module. This created two issues:

1. **Dual source of truth and maintenance drift:** Rules already declared in `.importlinter` were duplicated in ad-hoc AST walking logic.
2. **Tool mismatch:** AST traversal over individual files is prone to false negatives with relative imports, nested packages, or transitive dependencies (`domain` → `utils` → `infra`), while static import linters cannot inspect class definitions, inheritance hierarchies, or `@abstractmethod` decorators.

To resolve this ambiguity, Constitution Article 19 formally distinguishes between **static import-graph analysis** and **structural contract tests**.

---

## 2. Verification Stack Matrix

Architectural enforcement is partitioned across three non-overlapping layers:

| Responsibility | Target of Verification | Enforcing Tool | Execution Mechanism | Constitution Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Layer & module isolation** | Inward dependency direction; no leakage of infrastructure or adapters into domain or orchestration | `import-linter` | Static graph analysis (`uv run lint-imports`) | Articles 2, 19 · ADR 0016 |
| **Class contract structure** | Ports inherit from `abc.ABC` with `@abstractmethod`; concrete adapters explicitly inherit from domain ports | `pytest` + `inspect` | In-memory reflection in `tests/contract/` | Articles 4, 19 |
| **Interface type safety** | Signature compatibility, return types (`Sequence[VectorizedChunk]`), and strict domain enums | `mypy --strict` | Static type checking (`uv run mypy src tests`) | Articles 1, 5 · ADR 0016 |
| **External boundary drift** | Governance manifest schema compliance and API OpenAPI contracts | `pytest` + `pydantic` / `spectral` | Contract tests in `tests/contract/` | Articles 5, 17 · ADR 0007 |

---

## 3. What Belongs in the Import Linter (`.importlinter`)

`import-linter` defines declarative architectural contracts analyzed by building a complete dependency graph of all modules across the project.

### Active Contracts in `.importlinter`:
1. **`domain-isolation` (`src.domain`):**
   - **Rule:** `src.domain` must have zero direct or indirect dependencies on `src.adapters`, `src.ingestion`, or third-party infrastructure SDKs (`qdrant_client`, `fastembed`, `opentelemetry`).
   - **Rationale:** The business domain must remain pure, deterministic, and free from external I/O or vendor lock-in (Article 2).
2. **`pipeline-isolation` (`src.ingestion.pipeline`):**
   - **Rule:** The batch ingestion orchestrator must have zero imports from concrete storage or embedding adapters (`src.adapters.storage`, `src.adapters.embeddings`, `qdrant_client`, `fastembed`).
   - **Rationale:** Orchestration must interact strictly with domain ports via dependency injection; wiring concrete adapters is confined exclusively to the composition root (`src.ingestion.cli.py`).

### Why `import-linter` (and not `pytest-archon` or AST tests):
- As documented in ADR 0016, `import-linter` provides fast-fail static analysis in Stage A prior to running any test suites.
- Unlike file-level AST parsing, `import-linter` traces transitive dependencies through package re-exports (`__init__.py`) and intermediate modules.

**Execution Command:**
```bash
uv run lint-imports
```

---

## 4. What Belongs in Contract Tests (`tests/contract/`)

`pytest` contract tests verify object-level and runtime structural properties that static linters cannot evaluate:

### 1. Abstract Port Validation (`test_behavioral_ports_are_abstract_classes`)
- Verifies that cross-layer seams (`EmbedderPort`, `ChunkStorageWriterPort`) are classes, inherit from `abc.ABC`, and declare non-empty `__abstractmethods__` (Article 4).
- Ensures that interfaces cannot be instantiated directly without an implementation.

### 2. Strict Adapter Subclassing (`test_concrete_adapters_inherit_from_domain_ports`)
- Verifies that concrete adapters (`FastEmbedAdapter`, `QdrantStorageAdapter`) explicitly subclass their respective domain ports (`issubclass(adapter_cls, port_cls)`).
- Enforces the constitutional rule that **duck typing is strictly prohibited across layer boundaries** (Article 4: *"An adapter must inherit from the port. A class that merely exposes methods of the same name does not satisfy the port"*).

**Execution Command:**
```bash
uv run pytest tests/contract/test_architecture_contracts.py -v
```

---

## 5. Local and CI Execution Sequence (Stage A)

To guarantee fast feedback and zero test suite pollution, Stage A checks execute in a strict fail-fast pipeline:

```bash
# 1. Code style and bandit security scan (instantaneous)
uv run ruff check .

# 2. Strict static typing and port signature matching
uv run mypy src tests

# 3. Hexagonal layer boundary and import graph verification
uv run lint-imports

# 4. Unit and architectural contract tests
uv run pytest tests/unit tests/contract -v
```

---

## 6. Spec Kit Workflow Integration Policy

- **Constitution role:** Supreme architectural policy defining invariants (hexagonal layers, port abstractness, real infrastructure testing).
- **ADR role:** Concrete technical choices fulfilling constitutional invariants (e.g., ADR 0016 selecting `import-linter` and rejecting `pytest-archon`).
- **Prompting guidance:** When generating feature plans or task breakdowns via Spec Kit (`/speckit-plan`, `/speckit-tasks`), always pass relevant ADR references in the prompt (e.g., `consider docs/adr/0016-jenkins-ci-platform-and-pipeline-implementation.md for CI gates and linters`) so generated tasks align with established tool decisions rather than improvising ad-hoc scripts.

