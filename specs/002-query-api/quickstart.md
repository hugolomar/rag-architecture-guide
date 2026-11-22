# Quickstart Guide: Governed Query API and RAG Runtime

**Feature**: `002-query-api`  
**Date**: 2026-11-21  
**Status**: Ready  

---

## 1. Prerequisites & Environment Setup

Ensure the virtual environment is locked and required dependencies are installed:

```bash
# Verify environment and dependencies
uv sync

# Ensure offline embedding models are cached locally
bash scripts/warmup_models.sh
```

---

## 2. Running Local Verification Suites

Execute the test pyramid according to `.agents/rules/testing-standards.md`:

```bash
# 1. Run pure unit tests (domain models, schema validation, isolated adapters)
uv run pytest tests/unit/ -m unit

# 2. Run contract tests (OpenAPI drift test against contracts/openapi.yaml)
uv run pytest tests/contract/test_openapi_drift.py -m contract

# 3. Run evaluation development suite (14 cases via evals/harness.py)
uv run pytest evals/runners/test_retrieval_dev.py -m dev

# 4. Run PR validation gate suite (6 blocking cases)
uv run pytest evals/runners/test_regression_val.py -m validation
```

---

## 3. Starting the Local Query API Service

To run the FastAPI server locally in development mode:

```bash
# Start Uvicorn composition root
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Testing Endpoints via cURL

### 4.1. Authorized Query (`ground_answer`)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <VALID_ENGINEERING_TOKEN>" \
  -d '{
    "query": "Which awslogs log options set the CloudWatch region and the log group name?",
    "top_k": 3
  }'
```

**Expected Response (200 OK):**
```json
{
  "answer": "The awslogs-region option sets the CloudWatch region and the awslogs-group option sets the log group name.",
  "behavior": "ground_answer",
  "citations": [
    {
      "doc_id": "DOC-ENG-001",
      "chunk_id": "DOC-ENG-001_0001"
    }
  ],
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "latency_ms": 312.4
}
```

### 4.2. Unauthorized Query / Restricted Document (`deny_access`)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <VALID_ENGINEERING_TOKEN>" \
  -d '{
    "query": "What are the confidential executive salary compensation bands?",
    "top_k": 3
  }'
```

**Expected Response (200 OK):**
```json
{
  "answer": "Access denied. You do not have permission to view the requested information.",
  "behavior": "deny_access",
  "citations": [],
  "trace_id": "6a9e2f3577b34da6a3ce929d0e0e8821",
  "latency_ms": 145.2
}
```

### 4.3. Missing / Invalid Authentication (`401 Unauthorized`)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello world"}'
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Missing or invalid authorization token",
  "error_code": "AUTH_INVALID_TOKEN"
}
```

---

## 5. OpenAPI Contract Linting

Verify that the OpenAPI specification complies with Spectral linting rules:

```bash
npx @stoplight/spectral-cli lint specs/002-query-api/contracts/openapi.yaml --fail-severity=error
```
