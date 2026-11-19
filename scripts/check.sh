#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  Enterprise Governed RAG - Quality Gates"
echo "=========================================="

echo "[1/4] Running Ruff (Lint & Formatting)..."
uv run ruff check .
uv run ruff format --check .

echo "[2/4] Running Mypy (Strict Static Typing)..."
uv run mypy src tests

echo "[3/4] Running Import Linter (Hexagonal Boundary Verification)..."
uv run lint-imports

echo "[4/4] Running Unit & Contract Tests..."
uv run pytest tests/unit tests/contract -v

echo "=========================================="
echo "  All Quality Gates Passed Successfully!"
echo "=========================================="

