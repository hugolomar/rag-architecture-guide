#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  Enterprise Governed RAG - Model Warmup"
echo "=========================================="
echo "Pre-caching FastEmbed ONNX models in ~/.cache/fastembed/..."

uv run python -c "from fastembed import TextEmbedding, SparseTextEmbedding; print('1/3 Dense BGE Large (BAAI/bge-large-en-v1.5)...'); TextEmbedding('BAAI/bge-large-en-v1.5'); print('2/3 Dense BGE Small (BAAI/bge-small-en-v1.5)...'); TextEmbedding('BAAI/bge-small-en-v1.5'); print('3/3 Sparse BM25 (Qdrant/bm25)...'); SparseTextEmbedding('Qdrant/bm25'); print('All embedding models successfully cached in local cache.')"

echo "=========================================="
echo "  Model Cache Initialization Complete!"
echo "=========================================="
