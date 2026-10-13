# RAG Architecture Guide (RAG²)


> **Reference architecture and implementation guide for governed, access-aware, and production-grade Retrieval-Augmented Generation (RAG) systems.**

Moving beyond naive proof-of-concept scripts, this repository demonstrates how to architect a complete enterprise RAG pipeline. It bridges the gap between basic vector search and a resilient production service by implementing document governance, hybrid retrieval, pre-inference security trimming, provider decoupling, and continuous evaluation.

---

## 🎯 The Motivation

A common failure mode in generative AI is treating RAG merely as connecting a vector database to an LLM. In enterprise scenarios, hallucinations, silent errors, and security breaches often stem from architectural gaps rather than model limitations:
1. **Ungoverned Document Ingestion:** Lack of data ownership, stale versions, and unstructured chunking.
2. **Semantic-Only Search Blind Spots:** Vector similarity struggles with exact codes, IDs, and tabular structures.
3. **Context & Data Leakage:** Relying on the LLM to decide whether a user is authorized to see retrieved confidential data.
4. **Monolithic Evaluations:** Failing to decouple retrieval failures from generation inaccuracies.

This repository implements the solutions to these challenges across three architectural planes.

---

## 🏗️ Architectural Overview

```text
[ Data Plane: Offline Ingestion ]
Documents + Metadata ──► Semantic Chunking ──► Dual Index (ChromaDB + BM25)
                                                      │
[ Runtime Plane: Query Orchestration ]                 │
User (with Role) ──► Query Rewriting ──► Hybrid Search (RRF)
                                             │
                                    Security Trimming (ACLs)
                                             │
                                    Cross-Encoder Reranker
                                             │
                                    Grounded Context Builder
                                             │
                                    Model Gateway (LiteLLM) ──► LLM
                                             │
                                    Validated Output + Citations
                                             │
[ Control Plane: Cross-Cutting ]             ▼
            Continuous Evals (DeepEval/Pytest) + Tracing (Phoenix)

## 📂 Repository Structure
├── data/                  # Sample business documents with frontmatter metadata
├── src/
│   ├── ingestion/         # Parsing, chunking, and dual-indexing pipeline
│   ├── retrieval/         # Hybrid search & cross-encoder reranker
│   ├── security/          # Security trimming and ACL filters
│   ├── gateway/           # LiteLLM gateway with fallback logic
│   └── api/               # FastAPI runtime orchestration endpoints
├── evals/                 # Golden dataset & evaluation suites (pytest + DeepEval/Ragas)
├── docs/adr/              # Architectural Decision Records
└── docker-compose.yml     # Local orchestration (FastAPI, VectorStore, Phoenix UI)