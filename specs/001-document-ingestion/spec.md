# Feature Specification: Governed Document Ingestion Pipeline

**Feature Branch**: `001-document-ingestion`  
**Created**: 2026-11-05  
**Status**: Draft  
**Input**: User description: "Define the specification and requirements for the Governed Document Ingestion Pipeline as a complete, observable, and containerized Data Plane vertical slice."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enforce Governance and Manifest Access Rules (Priority: P1)

As a security and governance officer, I want all enterprise documents to be validated against closed corporate taxonomies and assigned explicit access boundaries prior to indexing, so that unauthorized, unclassified, or obsolete information can never enter the searchable knowledge base.

**Why this priority**: Access control and data hygiene are the fundamental invariants of the system. If documents enter the index without strict governance validation or if archived documents are indexed, downstream retrieval and security trimming cannot guarantee confidentiality.

**Independent Test**: Can be tested independently by running the validation stage against valid, malformed, and out-of-catalog manifest records, verifying that valid documents proceed while invalid ones fail loud, and that archived documents are completely excluded.

**Acceptance Scenarios**:

1. **Given** a manifest record with valid department (`HR`), classification (`internal`), status (`current`), and allowed groups (`['all-employees']`),  
   **When** the validation stage runs,  
   **Then** the document is accepted as a canonical governed document and queued for processing.

2. **Given** a document marked with lifecycle status `archived` in the manifest,  
   **When** the ingestion lifecycle filter executes,  
   **Then** the document is completely withheld from chunking and indexing, leaving zero traces in the searchable index.

3. **Given** a document marked with lifecycle status `deprecated` alongside a `current` document,  
   **When** the ingestion lifecycle filter executes,  
   **Then** the document is processed and indexed with its status explicitly recorded as `deprecated` in its governance payload.

4. **Given** a manifest record containing a department, classification, status, or group outside the closed governance catalogs (e.g., department `Marketing` or group `admin`),  
   **When** boundary validation runs,  
   **Then** the pipeline rejects the record immediately, halts processing for that document, and raises an explicit validation error (*fail loud*).

---

### User Story 2 - Structure-Preserving Chunking & Dual-Representation Indexing (Priority: P1)

As an enterprise knowledge seeker, I want structured content (such as tabular policies and technical guides) to be chunked without breaking tables and indexed with both semantic and exact-token representations, so that queries can find information both by general meaning and by exact identifiers (flags, error codes, parameters).

**Why this priority**: Poor chunking fragments tables and separates data values from headers, making numerical or matrix policies unanswerable. Lack of exact-token indexing prevents technical discovery of flags and identifiers.

**Independent Test**: Can be tested by running the chunker and indexing engine against Markdown documents containing complex tables and technical flags, verifying that table rows preserve header context and that both semantic and lexical vectors are stored with governance metadata.

**Acceptance Scenarios**:

1. **Given** a Markdown document containing a multi-column data table,  
   **When** the chunking engine processes the document,  
   **Then** the table structure is preserved intact within a single chunk (headers and corresponding rows kept together) without splitting data cells across separate chunks.

2. **Given** a canonical document with access boundary `allowed_groups: ['engineering-core']` and `status: current`,  
   **When** the document is split into multiple chunks,  
   **Then** every resulting chunk inherits the parent document's `doc_id`, `allowed_groups`, and `status` inseparably.

3. **Given** a processed governed chunk,  
   **When** the indexing stage executes,  
   **Then** the chunk is stored in the retrieval index with its semantic representation, its exact written-token lexical representation, and its complete governance payload.

---

### User Story 3 - Spec-Driven Batch Observability & Telemetry Flush (Priority: P2)

As a system operator and SRE, I want the ingestion batch process to emit structured logs with a correlation run ID, stage-by-stage distributed traces, and progress metrics, ensuring all telemetry is completely flushed before termination, so that pipeline health, throughput, and potential failures can be audited without data loss.

**Why this priority**: Observability cannot be an afterthought. Because ingestion is an ephemeral batch job that terminates upon completion, unhandled telemetry leads to silent data loss and inability to diagnose indexing failures.

**Independent Test**: Can be tested by executing a batch run with a telemetry collector listener, confirming that structured JSON logs carry `run_id`, all stage spans close, chunk counters match processed totals, and exporters flush cleanly prior to process exit.

**Acceptance Scenarios**:

1. **Given** an ingestion batch execution is initiated,  
   **When** the process starts,  
   **Then** a unique `run_id` is generated and propagated to all structured JSON logs, spans, and metric events.

2. **Given** an active ingestion process moving through parsing, chunking, embedding, and indexing,  
   **When** each stage executes,  
   **Then** distinct trace spans are recorded for each stage with counts of processed documents and chunks.

3. **Given** the ingestion batch reaches completion (whether success or failure),  
   **When** the process prepares to terminate,  
   **Then** all telemetry buffers are explicitly flushed and closed before the process exits with an appropriate exit code (0 for success, non-zero for failure).

4. **Given** an ingestion process handling sensitive or restricted documents,  
   **When** telemetry signals (logs, traces, metrics) are emitted,  
   **Then** restricted document text and secret credentials are scrubbed and never appear in telemetry payloads.

---

### User Story 4 - Single-Command Containerized Deployment (Priority: P3)

As a platform engineer or developer, I want the retrieval store and the ingestion pipeline packaged as reproducible container images and orchestrated via a single command, so that the ingestion process can run consistently across local development and CI environments.

**Why this priority**: Ensures environmental consistency and eliminates multi-step manual setup procedures or dependencies on host-specific Python toolchains.

**Independent Test**: Can be tested by executing the container orchestration command in a clean environment, verifying that the storage service starts, the one-shot ingestion job runs to completion, populates the store, and exits cleanly.

**Acceptance Scenarios**:

1. **Given** a clean environment with container tooling installed,  
   **When** the single start command is executed,  
   **Then** the retrieval store container starts, and the one-shot ingestion container executes its batch process.

2. **Given** the one-shot ingestion container finishes indexing,  
   **When** all documents and chunks are persisted,  
   **Then** the ingestion container exits with code 0 while the retrieval storage service remains healthy and responsive.

---

### Edge Cases

- **Missing or Corrupted Manifest**: What happens when `data/manifest.json` is missing, unparseable, or references files not present on disk? The pipeline must abort immediately and log an explicit error without writing partial or corrupt states to the index.
- **Uncataloged Document on Disk**: What happens when a Markdown file exists in the directory but is absent from `data/manifest.json`? The system must refuse to index the uncataloged document, as uncataloged content lacks verified access control metadata.
- **Empty or Whitespace-Only Document**: How does the chunker handle documents with valid metadata but empty bodies? The system logs a warning, skips chunk generation for that file, and records a zero-chunk count without crashing the batch.
- **Overly Large Tables**: What happens when a single Markdown table exceeds the standard token limit of a single chunk? The system preserves row integrity by chunking across row boundaries while repeating table headers in subsequent chunks to maintain context.
- **Storage Connectivity Interruption**: What happens if the retrieval store becomes unreachable during upsert? The pipeline logs the failure with the active `run_id`, flushes error telemetry, and exits with a non-zero code to signal batch failure.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST validate the corpus governance manifest (`data/manifest.json`) against strict closed catalogs:
  - **Departments**: `HR`, `Engineering`, `Security`, `Finance`, `Legal`
  - **Classifications**: `public`, `internal`, `restricted`
  - **Lifecycle Statuses**: `current`, `deprecated`, `archived`
  - **Identity Provider Groups**: `all-employees`, `people-team`, `engineering-core`, `security-oncall`, `leadership`
- **FR-002**: The system MUST fail loud and reject any document that contains missing identifiers, invalid field schemas, or values outside the closed governance catalogs.
- **FR-003**: The system MUST exclude all documents marked as `archived` from chunking and indexing.
- **FR-004**: The system MUST index documents marked as `deprecated` and `current`, attaching their lifecycle status to the chunk governance metadata.
- **FR-005**: The system MUST parse raw Markdown documents, separating metadata frontmatter from document body content.
- **FR-006**: The system MUST implement structure-preserving chunking such that Markdown table structures (headers and associated data rows) remain together in a single chunk to preserve quantitative and relational meaning.
- **FR-007**: The system MUST enforce governance inheritance by attaching the parent document's `doc_id`, `allowed_groups`, and `status` to every chunk generated from that document.
- **FR-008**: The system MUST generate dual representations for every chunk: a dense vector for semantic search and a sparse lexical representation for exact written-token matching (flags, configuration keys, identifiers).
- **FR-009**: The system MUST persist all generated chunks into the retrieval storage collection, associating each chunk's dense vector, sparse lexical vector, and governance payload within a single searchable record.
- **FR-010**: The system MUST emit structured JSON logs on stdout carrying a consistent `run_id` across the batch execution.
- **FR-011**: The system MUST emit distributed trace spans covering each ingestion pipeline phase: parsing, chunking, embedding, and indexing.
- **FR-012**: The system MUST collect and report batch progress metrics, including count of documents parsed, chunks generated, and validation rejections.
- **FR-013**: The system MUST explicitly flush and shut down all telemetry exporters before process termination.
- **FR-014**: Telemetry signals MUST NOT include confidential document text, raw authorization tokens, or secrets.
- **FR-015**: The system MUST package the ingestion batch as a multi-stage container image using pinned dependency locking for build isolation.
- **FR-016**: The entire storage and ingestion stack MUST execute through a single container orchestration command without secondary manual steps.

---

### Key Entities

- **Canonical Document**: A validated, authoritative enterprise document containing an immutable identifier (`doc_id`), file path reference, owning department, classification level, lifecycle status, and the set of groups authorized to read it (`allowed_groups`).
- **Governed Chunk**: An individual text segment derived from a canonical document, containing the chunk text, its position metadata, and the inherited governance attributes (`doc_id`, `allowed_groups`, `status`).
- **Governance Catalog**: A closed, immutable taxonomy defining permissible departments, sensitivity classifications, lifecycle stages, and identity provider group names.
- **Dual Vector Record**: A composite data structure combining dense semantic vector weights, sparse lexical token weights, and the governed chunk payload for persistence in the retrieval index.
- **Ingestion Batch Run**: An execution lifecycle entity identified by a unique `run_id` that tracks processing stages, document throughput, operational metrics, and final exit status.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid documents in `data/manifest.json` marked as `current` or `deprecated` are successfully parsed, chunked, and indexed with both dense and sparse representations.
- **SC-002**: Exactly 0% of documents marked as `archived` are indexed in the retrieval store.
- **SC-003**: 100% of malformed manifest records or records referencing unapproved departments, classifications, statuses, or groups fail validation immediately before any storage write.
- **SC-004**: 100% of Markdown tables in the corpus remain intact within their respective chunks, preserving header row associations with data rows.
- **SC-005**: 100% of generated chunks carry valid, non-empty `doc_id`, `allowed_groups`, and `status` attributes matching their source canonical document.
- **SC-006**: 0% telemetry loss: all trace spans, log events, and execution metrics emitted during the batch run are received by the telemetry collector before process exit.
- **SC-007**: The complete ingestion workflow (storage startup, manifest validation, document processing, dual indexing, and clean shutdown) completes via a single automated command without manual intervention.

---

## Assumptions

- Source document files are stored in Markdown format under `data/raw/` with a corresponding governance catalog at `data/manifest.json`.
- The closed identity groups defined in the governance catalog match the groups configured in the enterprise identity authority.
- The retrieval storage service supports dual-vector indexing (dense and sparse) and metadata payload filtering.
- Local execution environments have container orchestration capabilities (Docker and Docker Compose) available.
