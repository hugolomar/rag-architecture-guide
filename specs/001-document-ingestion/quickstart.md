# Quickstart & Validation Guide: Governed Document Ingestion Pipeline

**Feature**: `001-document-ingestion`  
**Purpose**: Step-by-step instructions to run, verify, and validate the ingestion batch pipeline locally.

---

## 1. Prerequisites

Ensure you have the following installed and running:
- **Python**: 3.14 (managed via `uv`)
- **Container Tooling**: Docker and Docker Compose (to run Qdrant locally)

Verify requirements:
```bash
python --version   # Must be >= 3.14
docker --version
```

### Pre-Cache Embedding Models (Required for host integration tests)
Production Docker containers bake model weights directly into the image (`Dockerfile.ingestion`). If you plan to execute vectorization integration tests directly on the host machine, pre-cache FastEmbed weights in `~/.cache/fastembed/` once:
```bash
bash scripts/warmup_models.sh
```
*(Note: In air-gapped or network-isolated environments where model weights are not pre-cached, vectorization integration tests detect their absence and automatically mark themselves as `SKIPPED` with an actionable message. This graceful degradation can be verified by running: `FASTEMBED_CACHE_PATH=/tmp/empty HF_HUB_OFFLINE=1 uv run pytest tests/integration/test_fastembed_adapter.py`).*

---

## 2. Start Storage Dependencies

Start a local Qdrant instance via Docker:
```bash
docker run -d --name qdrant-dev \
  -p 6333:6333 -p 6334:6334 \
  qdrant/qdrant:latest
```

Verify that Qdrant is healthy:
```bash
curl http://localhost:6333/healthz
# Response: 200 OK (health check passes)
```

---

## 3. Verify Architecture & Run Ingestion Tests

Before running the batch process, verify architectural boundaries and ensure all unit, contract, and integration tests pass:

```bash
# Run all automated quality gates (Ruff lint/format, Mypy, Import-Linter, Unit & Contract tests)
bash scripts/check.sh

# Run offline integration tests (Qdrant in-memory, Telemetry flush lifecycle)
uv run pytest tests/integration/test_qdrant_writer.py tests/integration/test_telemetry_flush.py -v

# Run full integration tests with model embeddings (requires pre-cached models or warmup)
uv run pytest tests/integration/test_fastembed_adapter.py tests/integration/test_ingestion_e2e.py -v
```

### Simular entorno offline / validación de skip sin modelos
Para comprobar de forma no destructiva que los tests de integración se saltan limpiamente (`SKIPPED`) con su mensaje explicativo cuando no hay pesos locales (sin necesidad de borrar `~/.cache/fastembed/`):
```bash
FASTEMBED_CACHE_PATH=/tmp/empty HF_HUB_OFFLINE=1 uv run pytest tests/integration/test_fastembed_adapter.py tests/integration/test_ingestion_e2e.py
```

---

## 4. Execute the Ingestion Batch Pipeline

Run the batch ingestion CLI on the host:
```bash
uv run python -m src.ingestion.cli
```

Or execute via Docker Compose:
```bash
docker compose -f docker/docker-compose.yml run --rm ingestion
```

### Expected Output
The process outputs structured JSON logs to stdout:
```json
{"timestamp": "2026-11-05T17:35:01Z", "level": "INFO", "run_id": "run-b7a2e", "stage": "manifest", "message": "Validated 36 documents in manifest.json"}
{"timestamp": "2026-11-05T17:35:02Z", "level": "INFO", "run_id": "run-b7a2e", "stage": "filter", "message": "Filtered out DOC-CORP-004 (archived)"}
{"timestamp": "2026-11-05T17:35:10Z", "level": "INFO", "run_id": "run-b7a2e", "stage": "chunk", "message": "Generated 312 governed chunks (tables preserved)"}
{"timestamp": "2026-11-05T17:35:28Z", "level": "INFO", "run_id": "run-b7a2e", "stage": "embed", "message": "Computed dual vectors (BGE dense + BM25 sparse)"}
{"timestamp": "2026-11-05T17:35:32Z", "level": "INFO", "run_id": "run-b7a2e", "stage": "storage", "message": "Upserted 312 points to Qdrant collection 'governed_docs'"}
{"timestamp": "2026-11-05T17:35:33Z", "level": "INFO", "run_id": "run-b7a2e", "stage": "telemetry", "message": "Telemetry flushed and shut down cleanly"}
```
The process terminates with exit code `0`.

---

## 5. Verify Qdrant Points & Payloads

### Verify collection point count:
```bash
curl http://localhost:6333/collections/governed_docs | jq '.result.points_count'
# Expected: > 300 points
```

### Verify dual vectors and governance payload on a point:
```bash
curl -X POST http://localhost:6333/collections/governed_docs/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 1, "with_vector": true, "with_payload": true}' | jq '.result.points[0]'
```

Verify that the returned point contains:
1. `vector.dense`: array of 1024 floats.
2. `vector.sparse`: object with `indices` and `values`.
3. `payload.allowed_groups`: non-empty array of valid groups.
4. `payload.status`: either `"current"` or `"deprecated"`.

### Verify archived exclusion:
Query specifically for any chunk with status `archived`:
```bash
curl -X POST http://localhost:6333/collections/governed_docs/points/count \
  -H "Content-Type: application/json" \
  -d '{"filter": {"must": [{"key": "status", "match": {"value": "archived"}}]}}' | jq '.result.count'
```
**Expected count**: `0`.

