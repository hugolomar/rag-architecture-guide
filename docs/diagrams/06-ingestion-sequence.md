# Ingestion sequence

Sequence view for one ingestion run. This is a one-shot Data Plane job from ADR 0005. The process
starts, writes/upserts points, flushes telemetry exporters, and exits. Qdrant stays up.

```mermaid
sequenceDiagram
  participant Job as Ingestion job
  participant Files as data/raw/*.md
  participant Manifest as data/manifest.json
  participant Parser as Markdown parser
  participant Merge as Governance merge
  participant Validate as Pydantic validation
  participant Chunker as Chunker
  participant FE as FastEmbed
  participant Q as Qdrant
  participant Obs as Telemetry exporter

  Job->>Files: Read source documents
  Job->>Manifest: Read governance metadata
  Job->>Parser: Parse front matter + body
  Parser-->>Job: source metadata + text
  Job->>Merge: Join by relative_path
  Merge-->>Job: governed document
  Job->>Validate: Validate canonical model
  Validate-->>Job: valid record / fail closed
  Job->>Job: Drop archived, keep current+deprecated
  Job->>Chunker: Split into chunks
  Chunker-->>Job: chunks + inherited governance
  Job->>FE: Build dense vectors (configured model)
  Job->>FE: Build sparse lexical vectors (BM25)
  FE-->>Job: vectors per chunk
  Job->>Q: Upsert point (dense+sparse+payload)
  Q-->>Job: write result
  Job->>Obs: force_flush/shutdown
  Job-->>Job: Exit

  Note over Job,Q: Changing dense model means new collection + reindex run.
```
