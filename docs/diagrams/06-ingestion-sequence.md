# Ingestion sequence

Sequence view for one ingestion run. This is a one-shot Data Plane job from ADR 0005. The process
starts, writes/upserts points, flushes telemetry exporters, and exits. Qdrant stays up.

```mermaid
sequenceDiagram
  participant CLI as CLI (Composition Root)
  participant Pipeline as Ingestion Pipeline
  participant ManifestLoader as Manifest Loader
  participant Domain as Domain (Validation)
  participant Parser as Markdown Parser
  participant Chunker as Document Chunker
  participant FE as FastEmbed Adapter
  participant Q as Qdrant Adapter
  participant Obs as Telemetry Manager

  CLI->>Obs: Initialize telemetry (run_id)
  CLI->>Pipeline: Execute pipeline(config, embedder, storage, chunker)
  Pipeline->>ManifestLoader: load_and_validate_manifest(manifest_path, raw_dir)
  ManifestLoader->>Domain: validate_and_partition_manifest(data)
  Domain-->>ManifestLoader: active_records, archived_records
  ManifestLoader->>ManifestLoader: Verify active & archived files exist on disk
  ManifestLoader-->>Pipeline: active_records (archived dropped from processing)
  
  loop For each active record
    Pipeline->>Parser: parse_markdown_document(file_path, record)
    Parser-->>Pipeline: CanonicalDocument (body + frontmatter + governance)
  end

  loop For each canonical document
    Pipeline->>Chunker: chunk_document(doc)
    Chunker-->>Pipeline: GovernedChunks (tables preserved, governance inherited)
  end

  Pipeline->>FE: vectorize_chunks(all_chunks)
  FE-->>Pipeline: VectorizedChunks (dense + BM25 sparse)

  Pipeline->>Q: ensure_collection & upsert_chunks(collection, vectorized_chunks)
  Q-->>Pipeline: Points persisted count

  Pipeline-->>CLI: Batch summary results
  CLI->>Obs: flush_and_shutdown() (zero telemetry loss)
  CLI-->>CLI: Exit 0
```

  Note over Job,Q: Changing dense model means new collection + reindex run.
```
