#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  Enterprise Governed RAG - Model Warmup"
echo "=========================================="
echo "Pre-caching FastEmbed ONNX models in ~/.cache/fastembed/..."

uv run python -c "from fastembed import TextEmbedding, SparseTextEmbedding; print('1/2 Downloading Dense BGE model (BAAI/bge-large-en-v1.5)...'); TextEmbedding('BAAI/bge-large-en-v1.5'); print('2/2 Downloading Sparse BM25 model (Qdrant/bm25)...'); SparseTextEmbedding('Qdrant/bm25'); print('All embedding models successfully cached in ~/.cache/fastembed/.')"

echo "=========================================="
echo "  Model Cache Initialization Complete!"
echo "=========================================="
