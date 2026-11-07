# Ingestion Batch CLI Contract

**Interface Type**: Command Line Interface / Container Entrypoint  
**Module**: `src.ingestion.cli`  

---

## 1. Invocation

### Host execution (via uv)
```bash
uv run python -m src.ingestion.cli
```

### Container execution (Production / Compose)
```bash
docker compose run --rm ingestion
```

---

## 2. Environment Variables

All configuration is environment-driven (per Constitution Article 27):

| Variable | Default Value | Required | Description |
| :--- | :--- | :---: | :--- |
| `RAG_DATA_DIR` | `data/raw` | No | Path to raw Markdown documents directory |
| `RAG_MANIFEST_PATH` | `data/manifest.json` | No | Path to the corpus governance manifest JSON |
| `QDRANT_HOST` | `localhost` | No | Hostname of the Qdrant service |
| `QDRANT_PORT` | `6333` | No | REST/gRPC port for Qdrant |
| `QDRANT_COLLECTION_NAME`| `governed_docs` | No | Target Qdrant collection name |
| `OTEL_EXPORTER_OTLP_ENDPOINT`| `http://localhost:4318` | No | OTLP HTTP receiver endpoint |
| `OTEL_SERVICE_NAME` | `rag-ingestion` | No | Service name reported in traces |
| `LOG_LEVEL` | `INFO` | No | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 3. Exit Codes

The ingestion process is a one-shot batch command (Article 27). Progress is audited through OpenTelemetry signals, not health check endpoints.

| Exit Code | Meaning | Conditions |
| :---: | :--- | :--- |
| **`0`** | **Success** | All valid documents parsed, chunked, embedded, and stored; telemetry flushed cleanly. |
| **`1`** | **Manifest / Schema Failure** | `manifest.json` missing, corrupt, or referencing unknown departments/groups. |
| **`2`** | **Corpus File Mismatch** | Manifest references a file not present on disk, or raw file contains unparseable frontmatter. |
| **`3`** | **Vector Store Failure** | Unable to connect to Qdrant or collection creation/upsert failed. |
| **`4`** | **Telemetry Failure** | Failed to flush telemetry exporters before process exit. |

---

## 4. Standard Output (Stdout) Contract

Stdout produces newline-delimited structured JSON log lines:

```json
{"timestamp": "2026-11-05T17:30:00.123Z", "level": "INFO", "run_id": "run-4f81-a9c1", "stage": "manifest", "message": "Manifest validated successfully", "total_docs": 36}
{"timestamp": "2026-11-05T17:30:01.450Z", "level": "INFO", "run_id": "run-4f81-a9c1", "stage": "filter", "message": "Excluded archived documents", "archived_count": 1, "active_count": 35}
{"timestamp": "2026-11-05T17:30:15.980Z", "level": "INFO", "run_id": "run-4f81-a9c1", "stage": "index", "message": "Batch indexing complete", "chunks_indexed": 312}
```

