# ADR 0016: Jenkins CI Platform and Pipeline Implementation

- Status: Accepted
- Date: 2026-10-23

## Context

ADR 0014 defines the evaluation gates and ADR 0015 defines the phase tooling. The operational case
curation flow is documented in `docs/processes/eval-case-curation-from-production.md`. The project
needs a concrete CI platform and pipeline structure to install the locked environment, run the
project tests, and enforce those evaluation rules in automated checks.

## Decision

Use **Jenkins** as the CI platform for this system.

### 1) Pipeline stages

Stage execution is fail-fast: each stage runs only if the previous stage succeeds.

- **Checkout:** check out the commit as its own visible stage. Do not rely only on Jenkins' default checkout.
- **Prepare:** install the locked environment with `uv sync` from `uv.lock` (ADR 0002). Later stages reuse that environment. Do not repeat the sync in each stage.
- **Stage A: checks and unit tests without provider calls**
  - lint,
  - schema/contract checks (Spectral and the OpenAPI drift test from ADR 0007),
  - suite integrity tests (`evals/test_suite_integrity.py`),
  - harness self-check (`evals/test_harness_selfcheck.py`),
  - unit tests of the project code, once that code exists,
  - structural checks for ports, models, and dependency direction (`lint-imports`), once the code they govern exists,
  - SAST scan (`bandit`) on the project source,
  - dependency vulnerability scan (`pip-audit`) against known CVEs,
  - SonarQube scanner and quality gate (ADR 0018).
  - This stage does not run `val_set`, `dev_set`, or the protected suite, and it does not receive provider keys. A failure stops the pipeline before stage B.
- **Stage B: PR validation gate**
  - trigger: pull request pipeline,
  - run `val_set` phase-1 deterministic checks,
  - record phase-2 RAGAS scores (smoke profile) without failing the merge on them (ADR 0015),
  - fail the merge on hard-blocking criteria from ADR 0014.
  - The provider key is available in this stage.
- **Stage C: mainline validation**
  - trigger: post-merge mainline pipeline,
  - after merge, run full `val_set` phase-1 and phase-2,
  - enforce calibrated faithfulness and citation-consistency thresholds (ADR 0015). Answer relevance stays informational,
  - publish artifacts and trend metadata.
  - The provider key is available in this stage.
- **Stage D: release gate**
  - trigger: release pipeline,
  - inject protected suite path via CI secret/config (`RAG_PROTECTED_SUITE_PATH`),
  - enforce protected-suite-required mode (`RAG_PROTECTED_REQUIRED=1`),
  - block release on any hard-failure rule.
  - Do not tune RAGAS thresholds or rubrics against this suite (ADR 0015).
- **Docs: generate and publish the architecture site**
  - Build the site with **MkDocs** and the **Material for MkDocs** theme. Material renders the Mermaid fences already used in `docs/diagrams/`.
  - The site input is `docs/`, the repository README, and the docstrings in `src/` once that code exists. **mkdocstrings**, with the Python handler, adds those docstrings to the same build. Until `src/` exists, the build is the Markdown guide only.
  - The MkDocs configuration must not include `data/` or the protected suite.
  - The build writes `artifacts/docs/site`. A warning fails this build, and the site is not copied.
  - On the pull request pipeline, run it after stage B and copy `artifacts/docs/site` to the preview directory. A docs failure does not block the merge. Stage B remains the pull request gate. The failed stage stays visible on the build.
  - On the mainline pipeline, run it after stage C and copy `artifacts/docs/site` to the canonical directory. A failed build leaves the previous canonical site in place and does not revert the commit.
  - The release pipeline does not run this stage.
- `dev_set` stays a local work list. It is not a CI gate.

### 2) Secret and protected-data handling

- Provider keys and protected suite path/contents are managed in Jenkins credentials, not repository.
- Jobs access secrets only in stages that require them. The provider key is limited to stages B and C. The protected suite is limited to stage D. Checkout, Prepare, stage A, and Docs receive neither.
- Build logs must avoid printing secret values or restricted-case contents.

### 3) Artifacts and traceability

- Persist machine-readable evaluation artifacts per run (phase results, gate outcomes, timings).
- Include correlation metadata (`build_id`, commit SHA, branch, suite id, optional `trace_id` links).
- Retain enough history for regression trend inspection and incident forensics.

### 4) Code quality platform

SonarQube Community Edition (`sonarqube:lts-community`) is the code quality and coverage platform.
It runs as a container alongside the CI infrastructure. PostgreSQL is its database. Both containers
are long-running services; SonarQube exposes a health check so the Jenkins agent waits for it to
be ready before submitting analysis.

The SonarQube scanner (`sonar-scanner`) runs as the last step of Stage A and waits for the quality
gate result before Stage A is declared green. Coverage is collected by `pytest-cov` during the
unit test step; the scanner picks up the `coverage.xml` report. Project configuration lives in
`sonar-project.properties` at the repository root. The server URL and token are stored in Jenkins
credentials and are available in Stage A only.

Quality gate thresholds (new-code coverage, security hotspots reviewed, reliability and security
ratings) are calibrated once the project has sufficient code. Until then the gate runs in
report-only mode: the scanner submits the analysis and surfaces results without blocking the merge.

## Rationale

- Jenkins provides mature staged pipelines and secret handling patterns suitable for mixed local/CI
  workflows.
- Explicit stage boundaries mirror evaluation governance boundaries from ADR 0014.
- Protected-suite injection via credentials preserves hold-out isolation from repository access.
- The architecture site is published only after the gate for that pipeline is green. A docs failure skips publication and does not block the merge or revert `main`. The release job never builds the site.
- MkDocs keeps the guide in Markdown. mkdocstrings is the API-extraction step, and it stays in the same build as the guide.
- SonarQube Community Edition covers coverage trend analysis, security hotspot tracking, complexity,
  and duplication in a single quality gate. Per-commit tools (`bandit`, `pip-audit`) produce
  point-in-time results; SonarQube accumulates history across builds.

## Alternatives Considered

1. **Tool-agnostic CI only (no platform decision)**
   - Pros: flexibility.
   - Cons: delayed operational enforcement and ambiguous implementation ownership.
   - Rejected.

2. **GitHub Actions as initial platform**
   - Pros: tight GitHub integration and simpler hosted setup.
   - Cons: not selected as current organizational CI baseline for this repository.
   - Rejected for this system.

3. **Single-stage monolithic pipeline**
   - Pros: simple configuration.
   - Cons: poor visibility and weak separation of PR, mainline, and release controls.
   - Rejected.

4. **Sphinx as the documentation site tool**
   - Pros: mature API reference from docstrings.
   - Cons: its authoring format is reStructuredText. This guide is already Markdown and Mermaid, and the API reference is one later section of that guide.
   - Rejected.

5. **pdoc as the documentation site tool**
   - Pros: small API-page generator.
   - Cons: it generates API pages only and does not build the architecture guide.
   - Rejected.

6. **SonarCloud (hosted) instead of self-hosted SonarQube**
   - Pros: no infrastructure to maintain; free for public repositories.
   - Cons: the protected suite and governed data must not leave the local environment. A hosted
     platform requires careful exclusion rules and relies on a third-party service for a
     security-sensitive project.
   - Rejected.

7. **Coverage-only quality gate with `pytest-cov` threshold in Jenkinsfile**
   - Pros: zero additional infrastructure.
   - Cons: no security hotspot tracking, no complexity analysis, no trend history, no duplication
     detection. A single threshold is not a configurable quality gate.
   - Rejected.

## Consequences

- **Positive:** evaluation governance is enforceable in automated delivery flow.
- **Positive:** protected benchmark handling is explicit and isolated.
- **Positive:** the published architecture guide matches a commit that already passed its gate.
- **Positive:** unified quality gate covering coverage, security hotspots, complexity, and
  duplication in Stage A without a separate ADR.
- **Negative:** Jenkins operational maintenance overhead.
- **Negative:** additional work to optimize build time and agent caching.
- **Negative:** SonarQube and PostgreSQL containers increase the infrastructure footprint of the
  local and CI stack. SonarQube requires a warm-up period after container start.
- **Negative:** Material for MkDocs is in critical maintenance through 2027-05-05. Its successor, Zensical, is not the build tool yet.
- **Boundary:** this ADR does not redefine gate semantics (ADR 0014) or evaluator role boundaries
  (ADR 0015).
- **Follow-up:** add concrete Jenkinsfile/job templates and credentials mapping documentation.
- **Follow-up:** add `mkdocs`, `mkdocs-material`, and `mkdocstrings[python]` to the dev group, and add `mkdocs.yml`.
- **Follow-up:** name the preview and canonical directories on the Jenkins host.
- **Follow-up:** revisit Zensical when its stable line supports this MkDocs configuration, including mkdocstrings.
- **Follow-up:** add `import-linter`, `bandit`, and `pip-audit` to the dev group in `pyproject.toml` and configure `import-linter` contracts once the source layout is established.
- **Follow-up:** add SonarQube and PostgreSQL services to the infrastructure Compose file (ADR 0017).
- **Follow-up:** add `sonar-project.properties` to the repository root.
- **Follow-up:** configure quality gate thresholds and switch from report-only mode once the project has sufficient code coverage data.
