# ADR 0017: Local Deployment and Container Packaging

- Status: Accepted
- Date: 2026-10-26

## Context

ADR 0016 decides how a change is checked. This ADR decides how the system is started.

Several decisions already fix what a process is. Ingestion is a one-shot batch: it reads, indexes, flushes telemetry, and exits (ADR 0005). LiteLLM runs inside the API process (ADR 0008). Keycloak runs in its own container for local and CI integration (ADR 0010). The observability stack is operated with Docker Compose (ADR 0012). A container image, when built, installs with `uv sync` from `uv.lock` (ADR 0002). Secrets do not live in source (ADR 0009). Ingestion emits stage telemetry and must flush exporters before exit (ADR 0011).

What is open is the packaging of that set. There is no Dockerfile and no Compose file yet. Without one start path, each process can grow its own run instructions.

## Decision

Package deployable processes as containers and start the system with one command.

### 1) What is a deployable process

A deployable process is a program that runs. It is not a layer inside the hexagonal boundary.

- **API.** One image. The process is the stateless FastAPI runtime. LiteLLM stays inside that process. There is no proxy container for the model gateway.
- **Ingestion.** One image. The process is the one-shot job from ADR 0005. It exits when the run is finished.
- **Qdrant, Keycloak, and the observability stack.** Each keeps its own container, as already required by ADR 0006's storage choice, ADR 0010, and ADR 0012.

The shared domain package and the evaluation harness are not deployable units. The harness calls ports. It does not run as a service in this stack.

### 2) One command

Dockerfiles define the images. Compose defines the long-running processes and the ingestion job.

The operator runs one command. If Compose can express every step, that command is Compose. If a step needs something Compose does not express, such as importing the Keycloak realm or starting ingestion only after the store is ready, that step lives in one script. The script calls Compose. The script is the command. It is not a second procedure beside Compose.

Configuration comes from the environment. Credentials, tokens, and keys are not written into Dockerfiles or into tracked Compose files.

An image this project builds uses a multi-stage Dockerfile. The build stage installs the Python environment with `uv sync` from `uv.lock` (ADR 0002). The runtime stage copies that environment and starts it with the environment's Python, not with `uv run`. Install-only tools, including `uv` and any compiler, stay in the build stage. The embedding model is copied into the runtime stage, because the API and ingestion need it while they run. Both stages use the same Python series. Upstream images are consumed as published. This project does not rebuild them.

### 3) Health and the ingestion job

Long-running processes expose a health check so Compose can tell whether they are up before it starts what depends on them. That includes the API, Qdrant, and Keycloak. The API health check reports that the process is up. It does not grant access and it does not skip retrieval.

Ingestion does not expose a health endpoint. A process that must exit would fail that check when the run succeeds. A process that is stuck can still answer that it is alive.

While ingestion runs, progress is the telemetry ADR 0011 already requires. A stage span that does not close, or a chunk counter that stops moving, means the job is stuck. The result of the job is its exit code, after the telemetry exporters have been flushed and shut down.

## Rationale

- One start command is the operational counterpart of the single CI pipeline. ADR 0016 checks a change. This ADR starts the system those checks describe.
- Containers follow process boundaries that are already decided. Putting LiteLLM in its own container would reopen ADR 0008. Giving ingestion a service health check would reopen ADR 0005.
- A script that calls Compose keeps the extra setup in one place without inventing a second way to start the stack.
- Exit status plus stage telemetry distinguishes a finished ingestion run from a hung one. A health endpoint does not.
- The runtime image contains the process and the model it needs. It does not contain the installer.

## Alternatives Considered

1. **Compose only for infrastructure; API and ingestion via `uv run` on the host**
   - Pros: faster edit loop for Python code.
   - Cons: two start paths, and the host environment drifts from the image.
   - Rejected.

2. **One container for the whole system**
   - Pros: a single image to run.
   - Cons: Qdrant, Keycloak, and the API would share a lifecycle. A finished ingestion run would take the API down with it.
   - Rejected.

3. **Health endpoint on ingestion**
   - Pros: the same check as the long-running processes.
   - Cons: success looks like failure once the job exits, and a hung process can still report that it is alive.
   - Rejected.

4. **Single-stage Dockerfiles for images this project builds**
   - Pros: one stage is shorter to read.
   - Cons: `uv` and any install-only compiler ship inside the process that serves requests or indexes documents.
   - Rejected.

5. **A setup script that does not call Compose**
   - Pros: room for arbitrary steps.
   - Cons: a second procedure, which is the outcome this ADR exists to avoid.
   - Rejected.

## Consequences

- **Positive:** the processes that already have a lifecycle get one packaging rule and one start command.
- **Positive:** ingestion keeps the batch lifecycle from ADR 0005, including the flush-before-exit rule.
- **Negative:** Dockerfiles, the Compose file, and any wrapper script still have to be written.
- **Negative:** an image build is slower than `uv run` on the host for a one-line change.
- **Boundary:** this ADR does not change gate semantics (ADR 0014, ADR 0016), the retrieval store (ADR 0006), or the in-process gateway (ADR 0008).
- **Follow-up:** add the multi-stage Dockerfiles for the API and ingestion, the Compose file, and the single start command. Add the wrapper script only if a step cannot be expressed in Compose.
- **Follow-up:** add the API health route to the OpenAPI contract when the runtime image exists. The route reports process liveness only.
- **Follow-up:** add the SonarQube (`sonarqube:lts-community`) and PostgreSQL containers to the infrastructure Compose file (ADR 0016, section 4).
