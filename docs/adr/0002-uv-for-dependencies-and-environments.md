# ADR 0002: uv for Python, Environments, and Dependencies

- Status: Accepted
- Date: 2026-10-20

## Context

ADR 0001 chooses Python 3 for the Data Plane and the Runtime Plane. It does not choose how the
interpreter is installed, how the environment is isolated, or how dependencies are declared.

The usual split is a version manager, `venv`, and `pip` with `requirements.txt`. A flat
requirements file lists direct and transitive packages together, and it does not lock hashes by
default. Two installs of the same file can resolve different trees.

This repository already declares the project in `pyproject.toml` (PEP 621) and locks the tree in
`uv.lock`. The interpreter series is Python 3.14. `pytest` is a development dependency. There is
no `requirements.txt`.

## Decision

Use **uv** as the only project tool for the Python interpreter, the virtual environment, and
package resolution.

- The interpreter series is pinned with `uv python pin` (Python 3.14). uv may download that
  interpreter. The system Python stays the operating system's.
- Dependencies are declared in `pyproject.toml`. Runtime dependencies are added with `uv add`.
  Development dependencies are added with `uv add --dev`.
- `uv.lock` is the lockfile. It records the full tree and the SHA-256 hash of each distribution.
- A clone installs that tree with `uv sync`. Commands run inside the project environment with
  `uv run`.
- An install that does not update `pyproject.toml` and `uv.lock` is not a change to the project.

## Rationale

- One binary covers the interpreter, the environment, and the resolver, so the project does not
  keep a second toolchain beside `pyproject.toml`.
- The lockfile makes a later install resolve the same distributions, including hashes, on another
  machine and in CI when CI exists.
- Direct dependencies stay in `pyproject.toml`. Transitive packages stay in the lockfile, so
  updates start from the direct list.
- uv resolves and installs faster than pip or Poetry. A future CI workflow and a future
  container image build repeat that same install step.
- `uv sync` and `uv run` are enough to reproduce the environment from the lockfile. Separate
  wrapper scripts are not required for that.

## Alternatives Considered

1. **pip and requirements.txt**
   - Pros: widely known; no extra tool.
   - Cons: no hash-locked tree by default; direct and transitive requirements share one flat list.
   - Rejected. This repository no longer uses `requirements.txt`.

2. **Poetry or Pipenv**
   - Pros: `pyproject.toml` and a lockfile; a single project command for dependencies.
   - Cons: a second tool that does not also provide the Python 3.14 interpreter used here.
   - Rejected for this iteration.

3. **uv only for installs, with dependencies still typed by hand**
   - Pros: fast installer.
   - Cons: a package can be present in `.venv` and absent from the lockfile.
   - Rejected. `uv add` and `uv add --dev` are the way a dependency enters the project.

## Consequences

- **Positive:** interpreter, environment, and packages are one workflow. `uv sync` reproduces the
  locked tree.
- **Negative:** `pip install` and `python -m venv` are not the project commands. A package
  installed only into `.venv` will be missing on the next `uv sync`.
- **Boundary note:** hashes in `uv.lock` pin the distributions that were resolved. They do not
  scan those distributions for known vulnerabilities.
- **Follow-up:** CI, when it exists, installs from `uv.lock` with `uv sync`. There is no CI
  workflow in the repository yet.
