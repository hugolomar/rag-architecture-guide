# Ingestion components

C4 level 3, inside the ingestion container from the container diagram. The process is one-shot (ADR 0005). It starts, runs the components below, flushes its telemetry, and exits. Qdrant stays up. The collection outlives the process.

The parser reads Markdown and does not know groups. The merge joins a file to its manifest row by `relative_path`. For access and status, the manifest wins. A document that fails validation does not continue. `archived` documents are dropped after validation. `current` and `deprecated` are chunked. The chunk strategy is not chosen. Each chunk inherits its document's governance.

FastEmbed builds both vectors before the write. The dense model is not chosen. The sparse vector is BM25, for a written token such as an option name, a flag, or an identifier. The writer upserts one Qdrant point per chunk: dense vector, sparse vector, and governance payload. The model name and the dimensions are recorded with the collection. Ingestion does not read the identity provider.

```mermaid
graph TD
  subgraph Ingest["Ingestion · Python 3.14 · one-shot"]
    Parser["Parser<br/>Splits front matter from body<br/>Keeps title, description, keywords"]
    Merge["Merge<br/>Joins on relative_path<br/>Manifest wins for access and status"]
    Canon["Canonical document<br/>Pydantic<br/>Stops a record without doc_id or groups"]
    Chunker["Chunker<br/>Strategy not chosen<br/>Chunk inherits document governance"]
    Vectors["FastEmbed<br/>Dense model not chosen<br/>Sparse BM25 for the written token"]
    Writer["Qdrant writer<br/>One point per chunk"]
  end

  Docs["Document sources<br/>Markdown"]
  Catalog["Governance catalog<br/>allowed_groups, status, ownership"]
  Qdrant[("Qdrant<br/>Collection outlives this process")]

  Docs -- "Supplies Markdown" --> Parser
  Parser -- "Text and source metadata" --> Merge
  Catalog -- "Supplies the manifest row" --> Merge
  Merge -- "Governed document" --> Canon
  Canon -- "current and deprecated only" --> Chunker
  Chunker -- "Chunk plus governance" --> Vectors
  Vectors -- "Dense vector and sparse vector" --> Writer
  Writer -- "Upserts the point" --> Qdrant

  style Parser fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Merge fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Canon fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Chunker fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Vectors fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Writer fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px
  style Docs fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Catalog fill:#999999,stroke:#666666,color:#ffffff,stroke-width:2px
  style Qdrant fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px
```
