# Note 05: Local ingestion boundary and source port evolution

**Date:** 2026-11-12 · **Status:** decided

ADRs 0003, 0005, and 0006 establish hexagonal boundaries for outbound infrastructure (embedding providers and vector storage) so orchestration and domain logic remain provider-agnostic. This note records why the inbound document source does not introduce a port for local-only ingestion, how domain purity is preserved in the meantime, and how to evolve the boundary when external or multiple document sources are added.

---

## 1. Current boundary: pure domain, local ingestion

In the initial data plane slice, the corpus lives exclusively on the local filesystem (`data/manifest.json` and Markdown files under `data/raw/`). In accordance with Article 6 (Simplicity and proportionality), responsibilities are split without speculative interfaces:

* **Pure domain (`src/domain/manifest.py`):** `validate_and_partition_manifest` validates parsed manifest entries against `ManifestRecord` and enforces lifecycle partitioning (`current` / `deprecated` retained; `archived` excluded) strictly in memory, with zero filesystem or JSON I/O imports.
* **Local ingestion (`src/ingestion/`):** `manifest_loader.py` reads `data/manifest.json` from disk and verifies file existence against `raw_dir`, while `parser.py` reads Markdown files from disk and builds `CanonicalDocument` instances.

---

## 2. Why no inbound source port is defined yet

Unlike outbound infrastructure (`EmbedderPort` and `ChunkStorageWriterPort` in `src/domain/ports/`), local document reading is not wrapped in an abstract port today:

1. **Zero third-party infrastructure:** Reading local files with Python's standard `json` and `pathlib` modules introduces no external SDKs, network calls, or credentials that need isolation or mocking in unit tests (standard `tmp_path` fixtures suffice for loader tests, while domain validation tests run purely in memory).
2. **Single concrete source:** Designing an abstract port before a second real implementation exists often bakes local-filesystem assumptions (such as `relative_path` or a single `manifest.json`) into the contract, which later break when an API-backed source uses `file_id`, document export endpoints, or native ACLs.
3. **Domain purity already achieved:** Moving disk I/O out of `src/domain/manifest.py` keeps `src/domain/` decoupled from the filesystem without adding single-implementation boilerplate.

---

## 3. Evolution path

### Replacing local disk with an external source (e.g., Google Drive, S3, SharePoint)

Even when only a single source remains active, introducing a third-party SDK, network transport, and authentication warrants an explicit port (for the same reasons as Qdrant or FastEmbed):

1. Define `DocumentSourcePort(ABC)` in `src/domain/ports/`.
2. Move SDK calls, credential handling, and document export/download logic into a concrete adapter under `src/adapters/sources/` (e.g., `GoogleDriveSourceAdapter`).
3. Update `parser.py` to accept in-memory `raw_text: str` instead of `file_path: Path`, and inject the port into `run_ingestion_pipeline(...)` from the `cli.py` composition root so pipeline orchestration remains testable with an in-memory fake.

### Supporting multiple sources concurrently (e.g., local disk + Google Drive + SharePoint)

Multiple sources do **not** require a separate port per provider. Instead, they share **one common port** with **one adapter per source**:

1. **One port (`DocumentSourcePort`):** Exposes a uniform domain contract (e.g., returning validated `CanonicalDocument` instances or `(ManifestRecord, raw_text)` pairs).
2. **One adapter per technology (`src/adapters/sources/`):** Each adapter absorbs source-specific mechanics—reading `manifest.json` and `.md` files locally, or querying Drive/SharePoint APIs and mapping native permissions into `allowed_groups`—and translates them into canonical domain models.
3. **Composition root (`cli.py`):** Instantiates the active source adapters from configuration and passes `sources: Sequence[DocumentSourcePort]` into `run_ingestion_pipeline(...)`.
4. **Pipeline (`pipeline.py`):** Iterates over `sources` in a single loop and runs the remainder of the pipeline (`chunker` → `embedder` → `storage`) unchanged.
