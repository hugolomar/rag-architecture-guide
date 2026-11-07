# Data Model Specification: Governed Document Ingestion Pipeline

**Feature**: `001-document-ingestion`  
**Date**: 2026-11-05  
**Status**: Completed  

---

## 1. Closed Governance Catalogs (Domain Enums)

All classification and security taxonomies are strictly closed catalogs defined as standard Python `Enum` classes inheriting from `str`. Any value outside these enumerations is rejected at validation boundaries.

```python
from enum import Enum

class Department(str, Enum):
    """Owning department of the document. Does not grant access on its own."""
    HR = "HR"
    ENGINEERING = "Engineering"
    SECURITY = "Security"
    FINANCE = "Finance"
    LEGAL = "Legal"

class Classification(str, Enum):
    """Sensitivity classification of the document. Does not grant access on its own."""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"

class LifecycleStatus(str, Enum):
    """Document lifecycle state governing indexing and freshness."""
    CURRENT = "current"       # Indexed; primary grounding evidence
    DEPRECATED = "deprecated" # Indexed; historical context, superseded by current
    ARCHIVED = "archived"     # Excluded from indexing completely

class IdPGroup(str, Enum):
    """Identity provider groups that cross the access boundary."""
    ALL_EMPLOYEES = "all-employees"
    PEOPLE_TEAM = "people-team"
    ENGINEERING_CORE = "engineering-core"
    SECURITY_ONCALL = "security-oncall"
    LEADERSHIP = "leadership"
```

---

## 2. Core Domain Entities

### 2.1 Manifest Record (`ManifestRecord`)
Represents an individual entry in `data/manifest.json`.

| Field | Type | Required | Description & Validation Rules |
| :--- | :--- | :---: | :--- |
| `doc_id` | `str` | Yes | Unique business identifier (e.g., `DOC-HR-001`, `DOC-ENG-002`). Regex: `^DOC-[A-Z]{2,4}-[0-9]{3}$`. |
| `relative_path` | `str` | Yes | Path relative to `data/raw/` (e.g., `docker/bridge.md`). Must correspond to an existing `.md` file. |
| `department` | `Department` | Yes | Must belong to closed catalog `Department`. |
| `allowed_groups` | `list[IdPGroup]` | Yes | Non-empty list of groups authorized to read this document. Must be valid `IdPGroup` values. |
| `classification` | `Classification` | Yes | Must belong to closed catalog `Classification`. |
| `status` | `LifecycleStatus` | Yes | Must belong to closed catalog `LifecycleStatus`. |

---

### 2.2 Canonical Document (`CanonicalDocument`)
Represents the merged, validated enterprise document ready for chunking.

```python
from pydantic import BaseModel, Field

class CanonicalDocument(BaseModel):
    doc_id: str
    relative_path: str
    department: Department
    allowed_groups: list[IdPGroup]
    classification: Classification
    status: LifecycleStatus
    title: str = Field(description="Extracted from frontmatter or first markdown heading")
    content: str = Field(description="Markdown body without frontmatter")
    keywords: list[str] = Field(default_factory=list, description="Extracted tags/keywords")
```

---

### 2.3 Governed Chunk (`GovernedChunk`)
An indivisible segment of text that inherits its parent document's governance metadata.

```python
class GovernedChunk(BaseModel):
    chunk_id: str = Field(description="Deterministic ID: {doc_id}#c{chunk_index}")
    doc_id: str
    allowed_groups: list[IdPGroup]
    status: LifecycleStatus
    department: Department
    classification: Classification
    chunk_index: int
    text: str = Field(description="Raw chunk text preserving Markdown structure and tables")
    is_tabular: bool = Field(default=False, description="True if chunk contains a table")
```

---

### 2.4 Vectorized Chunk (`VectorizedChunk`)
The enriched chunk containing dual vector embeddings prepared for Qdrant upsert.

```python
class VectorizedChunk(BaseModel):
    chunk: GovernedChunk
    dense_vector: list[float] = Field(description="1024-dim dense embedding from FastEmbed BGE")
    sparse_indices: list[int] = Field(description="BM25 token indices")
    sparse_values: list[float] = Field(description="BM25 token weights")
```

---

## 3. Storage Model (Qdrant Point Struct)

Each `VectorizedChunk` maps to a Qdrant point struct as follows:

```json
{
  "id": "e4d909c2-9012-4c2f-b44a-9528f11ec438", 
  "vector": {
    "dense": [0.0123, -0.0456, "... (1024 floats) ..."],
    "sparse": {
      "indices": [45, 1204, 8932],
      "values": [1.45, 0.82, 2.11]
    }
  },
  "payload": {
    "chunk_id": "DOC-HR-001#c0",
    "doc_id": "DOC-HR-001",
    "allowed_groups": ["all-employees"],
    "status": "current",
    "department": "HR",
    "classification": "internal",
    "chunk_index": 0,
    "text": "### Remote Work Policy\nEmployees are eligible for remote work..."
  }
}
```

---

## 4. Entity State Transitions

```mermaid
stateDiagram-v2
    [*] --> ManifestValidation: Read manifest.json
    ManifestValidation --> Corrupted: Invalid schema / unknown enum
    Corrupted --> [*]: Fail Loud (Exit code 1)
    
    ManifestValidation --> FilterLifecycle: Valid Canonical Record
    FilterLifecycle --> ArchivedDropped: status == archived
    ArchivedDropped --> [*]: Excluded from storage
    
    FilterLifecycle --> Parsing: status in [current, deprecated]
    Parsing --> Chunking: Markdown parsed
    Chunking --> Embedding: GovernedChunks generated (tables preserved)
    Embedding --> Indexing: Dual vectors computed (Dense + BM25)
    Indexing --> [*]: Upserted to Qdrant (Exit code 0)
```

