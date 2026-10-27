# Note 04: Next steps and pipeline evolution

**Date:** 2026-10-27 · **Status:** roadmap

Notes 01–03 establish the corpus, the governance manifest, and the evaluation-first baseline. ADRs 0001–0017 establish the technology choices, clean hexagonal boundaries, and CI delivery platform. 

This note outlines the evolutionary roadmap for the RAG pipeline beyond the initial baseline. In accordance with Article 6 (Simplicity and proportionality) and Article 13 (The suites are the specification), complexity is introduced in measured, data-driven phases: each technique is evaluated against baseline metrics before becoming permanent.

---

## 1. Roadmap overview

The evolution is structured into three progressive phases, ordered by operational return on investment (ROI), architectural complexity, and feedback loops:

| Phase | Technique | Primary Goal | Latency & Compute Profile | Complexity |
|---|---|---|---|---|
| **Phase 1** | **Semantic Reranking** | Precision boost (top-k relevance) | Low (in-process ONNX, +25–45ms CPU) | Low |
| **Phase 2** | **Query Rewriting & Expansion** | Recall boost & ambiguity resolution | Moderate (fast model call, +400–800ms) | Moderate |
| **Phase 3** | **Corrective RAG (CRAG)** | Reliability, confidence & fallback control | High (branching evaluation, multi-step) | High (Agentic flow) |

---

## 2. Phase 1: In-process Semantic Reranking

### Why it comes first
Semantic reranking provides the highest immediate quality gain with the lowest architectural complexity. It does not introduce external API dependencies or network latency; it runs entirely in-process.

### Architecture and placement
The reranker lives exclusively inside the **retrieval adapter** (`src/adapters/retrieval.py`). The domain port signature (`retrieve_fn(query, user_id, top_k=5)`) remains unchanged.

The execution sequence is strictly ordered:
1. **Candidate retrieval:** Qdrant performs hybrid search (Dense + BM25 with Reciprocal Rank Fusion) retrieving an expanded window of candidates (e.g. `limit=20`).
2. **Security trimming (MANDATORY FIRST):** The candidate chunks are filtered against the caller's identity groups (`allowed_groups`). Chunks the user is not allowed to read are eliminated immediately.
3. **Cross-encoder reranking:** A lightweight cross-encoder (such as `bge-reranker-base` or `ms-marco-MiniLM` via FastEmbed / ONNX runtime) scores only the authorized candidates against the query and selects the final `top_k=5`.
4. **Result emission:** Top-k authorized chunks are returned to the domain orchestrator with ranking metadata.

> **Security Invariant:** The reranker never processes unauthorized documents. Security trimming always precedes reranking.

### Feature flag and empirical comparison
The reranker is toggleable via configuration (`RERANKER_ENABLED=true|false` in `.env` / Pydantic Settings).

This enables automated A/B evaluation benchmarking:
- **Baseline execution:** `RERANKER_ENABLED=false uv run pytest evals/` generates `artifacts/evals/baseline_results.json`.
- **Reranker execution:** `RERANKER_ENABLED=true uv run pytest evals/` generates `artifacts/evals/reranker_results.json`.
- **Comparison:** Results are compared in Langfuse Datasets & Experiments and documented in an ADR with concrete delta metrics (Mean Reciprocal Rank, Context Precision, and P95 latency).

---

## 3. Phase 2: Query Rewriting and Expansion

### Why it comes second
Once the retrieval and ranking engine is calibrated with exact and semantic matching, the remaining retrieval failures stem from human query ambiguity: vague phrasing, missing context in follow-up questions, acronyms, or misalignment with the vocabulary of the corpus.

### Architecture and placement
Query rewriting operates as an optional pre-retrieval stage in the application orchestration layer, before calling the retrieval port:
1. **Input analysis:** The raw user query is evaluated.
2. **Rewriting / Expansion:** A small, fast LLM (or prompt template via LiteLLM) produces a **rewrite artifact**:
   - The rewritten canonical question (resolving pronouns and expanding acronyms).
   - Generated sub-queries or keyword lists for hybrid search.
3. **Telemetry capture:** As mandated by Article 21, the AI trace in Langfuse records both the original user query and the rewrite artifact. If retrieval fails, audit forensics distinguish whether the search failed or the rewriter misinterpreted the question.

### Verification
Query rewriting is evaluated specifically against complex and colloquial test cases in `evals/`, measuring whether retrieval recall improves without drifting intent or altering the security boundary.

---

## 4. Phase 3: Corrective RAG (CRAG) and Fallback Control

### Why it is a distinct, advanced phase
Corrective RAG (CRAG) transitions the pipeline from a linear request-response flow to an **agentic, reflective architecture**. Because it introduces branching logic, self-assessment, and potential fallback loops, it requires a fully mature evaluation and observability baseline before implementation.

### Architecture and workflow
Instead of unconditionally passing retrieved chunks to the generation model, CRAG introduces an intermediate **Retrieval Quality Evaluator**:

1. **Relevance evaluation:** The retrieved and reranked chunks are scored for confidence and topical relevance against the query.
2. **Conditional branching:**
   - **Correct (High confidence):** Chunks are highly relevant. Strip irrelevant sentences and proceed directly to standard grounded generation (`ground_answer`).
   - **Ambiguous (Moderate confidence):** Chunks contain partial or contradictory evidence. The pipeline combines cautious synthesis with explicit caveats, or triggers targeted query reformulation.
   - **Incorrect / Irrelevant (Low confidence):** The retrieved chunks do not answer the question. The system does not attempt to hallucinate or generate an ungrounded response.
3. **Integration with domain behaviors:**
   CRAG maps directly to the four domain response behaviors required by Article 13:
   - When evidence is verified and adequate: `ground_answer`.
   - When evidence is insufficient or completely absent: formal `abstain`.
   - When the question conflicts between multiple domains or requires missing parameters: structured `clarify`.
   - When the user lacks permissions: deterministic `deny_access` (which short-circuits before CRAG evaluation).

### When to trigger Phase 3
Phase 3 is triggered when evaluation metrics on the validation suite demonstrate that linear generation produces hallucinations on edge cases where retrieval confidence is low, and when automated abstention or clarification is needed to satisfy production reliability SLAs.
