# Note 01: Dataset purpose

**Date:** 2026-10-15 · **Status:** second draft. The governance fields are decided in note 02.

## 1. Goal

Build a test RAG to evaluate three things: the *chunking* strategy (documents with tables and code), data *freshness* (obsolete versions vs. current ones) and *access control* (RBAC) by department and confidentiality level.

## 2. Core decision: documents on one side, metadata on the other

The dataset consists of two separate pieces:

| Piece | What it contains | Modified? |
|---|---|---|
| **Documents** (`data/raw/`) | The content exactly as a source system would provide it | No |
| **Manifest** (`data/manifest.*`) | Governance metadata that is not in the document itself | Yes, this is what we adjust during testing |

The Docker documents are kept **unaltered**, with their original front matter. The metadata that does not come with them (department, who can see them, whether they are still valid) lives in the manifest.

## 3. Why we do it this way

**It simulates a real project.** In a company, a document's text and its governance metadata rarely travel together. The text sits in SharePoint, Drive or Confluence, while permissions, owner and status come from the source system itself or from a catalog. Our RAG will receive, as in production, the content on one side and the metadata on the other. Since we have no real corporate source, the manifest stands in for it.

**It keeps governance out of the documents and out of the paths.** If we embedded permissions inside the files, or encoded them in file names or folders (`restricted/`, `hr/`), we would be testing the path and not the RAG's filter, and we would have two sources of truth that can diverge. Folders therefore describe only **provenance** (real or synthetic), never access or department.

**It enables clean experiments.** We can change the chunking strategy without touching the metadata, and change permissions or statuses without touching the documents. Comparisons stay fair.

**It separates responsibilities.** The parser reads formats; the manifest governs. Neither needs to know about the other until the moment they are merged.

## 4. Structure

```
data/
├── raw/
│   ├── docker/               # real documents, as downloaded, unaltered
│   └── synthetic/            # invented documents (legal, HR, security)
├── manifest.json             # governance metadata
├── users.json                # test users and their permissions
├── eval/questions.jsonl      # evaluation questions
└── processed/                # chunks and indexes, not versioned
```

The path under `raw/docker/` reproduces the docs.docker.com URL to avoid name collisions. Department, access level and status of every document, including the Docker pages (which stand in for internal engineering documentation), are defined only in the manifest.

## 5. Three layers of metadata

| Layer | Origin | Examples | Where it comes from |
|---|---|---|---|
| **Source** | The document itself | `title`, `description`, `keywords`, last-updated date | Front matter, extracted by the parser |
| **Governance** | Catalog or source system | `doc_id`, department, access level, status, validity | Manifest |
| **Evaluation** | Only our test bench | freshness pairs (`pair_id`, `superseded_by`), `expected_docs`, `forbidden_docs` | Manifest or `eval/` |

The first two exist in any real project. The third is test scaffolding and has no production equivalent. To stay closer to a real setup, it can live in a separate file (`eval/ground_truth`).

## 6. Ingestion flow

```
[ original .md document ] ──► parser ──► clean text + source metadata ──┐
                                                                        ▼
                                                        merge (pipeline) ──► CanonicalDocument ──► chunker ──► indexes
                                                                        ▲
[ manifest ] ───────────────────────────────────────────────────────────┘
```

1. **Parser.** Separates the front matter from the text and extracts the useful metadata. It knows nothing about roles or catalogs.
2. **Merge.** Combines that metadata with the manifest. For security and lifecycle fields, **the manifest takes precedence**.
3. **Canonical model.** It is validated (for example with Pydantic), so a document without an identifier or permissions fails at ingestion and not at query time.
4. **Chunker and indexes.** Each chunk inherits its document's metadata. The access filter is applied **before** the search.

## 7. What it would look like in a real project

| In this dataset | In a real project |
|---|---|
| `raw/` folder | Connector to SharePoint, Drive, Confluence, a docs repository... |
| Manifest | Metadata and ACLs delivered by the connector (owner, groups with access, modification date, URL) or a data catalog |
| `users.json` | Identity provider (company directory, SSO) |
| Changing a document's access in the manifest | A permission change at the source, which must propagate to the index |
| Running ingestion by hand | Periodic or event-driven sync, re-ingesting what changed |

In production the ingestion service runs under a service identity with read access to the sources it indexes, and it collects each document's ACL. The people building the system usually do not have access to all of the content (HR and legal in particular), so in development they work with samples or synthetic data and test the access logic with fictional users, as we do here.

Two aspects that are critical in production and worth simulating: that **a permission change at the source reaches the index** (otherwise content that should no longer be visible keeps being served), and that **a deleted or archived document disappears** from the results.

## 8. The synthetic documents

There are 16 English documents in `data/raw/synthetic/`, written for this project (fictional company, fictional customer). Each exists for a specific reason:

| Purpose | Documents |
|---|---|
| **Freshness pairs** (same topic, old and current version, contradicting figures) | Remote work policy v1 (2022) and v2 (2025); platform SLA v1 (2022) and v2 (2025); travel and expenses policy v2 (2023) and v3 (2026) |
| **Access control, clearly sensitive** | Salary bands, bonus plan, disciplinary procedure, master services agreement, data processing agreement, security incident response runbook |
| **Access control, public documents with similar vocabulary** (stress the filter) | Privacy policy (vs. the data processing agreement), employee security guidelines (vs. the incident runbook), leave policy (vs. the bonus plan), supplier code of conduct |
| **Multi-document questions** | The master services agreement points to the SLA and the DPA; breach notification deadlines are spread over the DPA (24 h), the privacy policy (72 h) and the supplier code (48 h) |

Design rules:

- Older versions **do not declare themselves obsolete** in the text; that information belongs in the manifest. Newer versions include a revision history, as real documents often do.
- Documents are longer and more complex than a typical template: several sections, definitions, exceptions, tables, worked examples and cross-references, so that they also exercise chunking.

## 9. What the synthetic data can and cannot tell us

**Mechanics (what it is for).** Pass/fail checks on whether the pipeline works: metadata attached to every chunk, a user without permission never receiving a restricted chunk, the current version winning over the obsolete one for a given question, tables not split mid-row, a permission change reaching the index. One well-chosen case is enough to expose a bug, and a single leak of restricted content is already a failure.

**Statistics (what it is not for).** Measuring how well the system performs in general, for example comparing recall between two chunking strategies. That needs many questions and a large, varied corpus: with 30 questions, one question moves a result by 3.3 points, so a difference of a few points is noise. Our 16 synthetic documents are also homogeneous (written by one author in one style) and surrounded by few distractors, which makes retrieval easier than in real life.

For chunking comparisons we therefore rely on the Docker corpus, which is larger and real, with a bigger set of evaluation questions.

## 10. Decisions made

- Docker documents stay unaltered; the front matter is read by the parser, not edited.
- `title`, `description` and `keywords` from the front matter become metadata. The remaining site-rendering fields (`aliases`, `weight`...) are discarded.
- The manifest takes precedence over the front matter for access, status and validity.
- Folders under `raw/` indicate provenance only. Department, access level and status live only in the manifest.
- Synthetic documents are in English, like the Docker corpus, so that language does not interfere with retrieval.
- All documentation in the repository is written in English.

## 11. Limitations

- Neither the manifest nor the field names are an industry standard; they are our own choices.
- The front matter's update date tells us when the page was last edited, not since when it has been valid or when it became obsolete. For freshness, the status in the manifest decides.
- A manually maintained manifest does not scale; in a real project the catalog is fed automatically.
- Synthetic documents are more homogeneous than real ones (see section 9). Evaluation questions about them should not reuse the documents' exact wording.

## 12. Open decisions

Note 02 closes the manifest format, the access model, where the evaluation fields live, and the fate of the old `raw/legal/` and `raw/hr/` files (they are not part of this corpus).

Still open:

- How to store `keywords` in the vector index, depending on what the database version supports, and whether to also include them in the text indexed by BM25.