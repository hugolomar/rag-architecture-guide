---
description: Mandatory standards for Python code quality, PEP 257 Google-style docstrings, strict static typing, and zero legalistic noise
trigger: model_decision
---

# Python Code Standards and Clean Architecture

All Python source code across `src/` and `tests/` must strictly comply with these engineering standards to maintain high readability, maintainable documentation, and strict type safety.

## 1. Docstrings Format (PEP 257 Google Style)

Every public module, class, method, and function must include an informative docstring adhering to PEP 257 and Google Style:
- **Module docstrings**: First statement in the file, summarizing the component's responsibility and role in the pipeline.
- **Class docstrings**: Summarize the class purpose, public contract, and any immutability or validation invariants.
- **Function/Method docstrings**: Required sections:
  - Concise one-line summary followed by an optional blank line and detailed paragraph.
  - `Args:` List each parameter with its meaning (types are already checked by type annotations, so avoid repeating types in prose unless clarifying structure).
  - `Returns:` Describe the semantic significance of the returned value.
  - `Raises:` List explicit exception types raised and the conditions under which they trigger.

## 2. Zero Legalistic Noise and Specification Independence

Code and docstrings describe **technical behavior, contracts, and architecture**, never project management tickets or governance bureaucracy:
- **No Governance Article Citations**: Never write "In accordance with Constitution Article X..." in production code, docstrings, Dockerfiles, or test headers.
- **No Specification Requirement Tags**: Never include requirement IDs (`FR-001`, `FR-008`), User Story tags (`US1`, `US4`), or sprint tickets in comments or docstrings.
- **No ADR Number Clutter**: Code should document *why* a technical choice was made in plain engineering terms rather than citing "per ADR 0005".

## 3. Strict Static Typing (`mypy --strict`)

All code must pass strict static type analysis without untyped definitions or unchecked generics:
- Explicit type annotations on all function signatures (arguments and return types).
- Use modern Python type hints (`list[str]`, `dict[str, Any]`, `tuple[int, ...]`) instead of legacy `typing` constructs.
- Never use `# type: ignore` without an explicit error code and brief technical comment explaining why static analysis cannot infer the type.

## 4. Hexagonal Core Purity & Port Discipline

- **Pure Domain (`src/domain/`)**: Zero imports from `src/adapters/`, `src/ingestion/`, or external infrastructure/storage SDKs. Enforced by `import-linter`.
- **Nominal Behavioral Ports**: All contracts crossing layer boundaries must inherit from `abc.ABC` and declare `@abstractmethod`. Structural subtyping (`typing.Protocol`) and duck typing are strictly prohibited across boundary seams.

## 5. Defensive Adapter Initialization & Operational Errors
- Infrastructure adapters (`src/adapters/`) initializing third-party models, drivers, or network transports must never leak raw socket timeouts or cryptic transport traces (e.g. `urllib3.ConnectTimeoutError`).
- Adapters must wrap external model/driver instantiation in explicit error handling, raising actionable runtime exceptions that clearly communicate missing prerequisites (e.g., pre-cached weights in `~/.cache/`) to operators and developers.
