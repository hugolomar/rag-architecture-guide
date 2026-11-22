# Data Model: Governed Query API and RAG Runtime

**Feature**: `002-query-api`  
**Date**: 2026-11-21  
**Status**: Completed  
**Alignment**: Constitution Articles 1-4, ADRs 0003, 0004, 0007, 0009, 0010  

---

## 1. Domain Entities & Value Objects (`src/domain/queries.py`)

All models are strictly validated Pydantic v2 models with `extra="forbid"`, static type annotations, and closed enum fields per `.agents/rules/domain-modeling-contracts.md`.

Document-related entities (`ManifestRecord`, `CanonicalDocument`, `GovernedChunk`, `VectorizedChunk`) are housed in `src/domain/documents.py`. Query runtime entities are housed in `src/domain/queries.py` and re-exported via `src/domain/__init__.py`.

```python
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class BehaviorEnum(StrEnum):
    """Closed catalog of governed pipeline outcomes."""

    GROUND_ANSWER = "ground_answer"
    DENY_ACCESS = "deny_access"
    ABSTAIN = "abstain"
    CLARIFY = "clarify"


class Citation(BaseModel):
    """Attribution link to an authorized source chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str = Field(..., description="Document identifier, e.g. DOC-ENG-001")
    chunk_id: str = Field(..., description="Chunk identifier, e.g. DOC-ENG-001_0001")


class CallerContext(BaseModel):
    """Verified identity context resolved from authoritative token claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(..., description="Unique subject identifier from token sub claim")
    groups: set[str] = Field(
        ..., description="Authoritative group memberships from token groups claim"
    )


class RetrievedChunk(BaseModel):
    """Internal domain representation of an authorized candidate chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Parent document identifier")
    text: str = Field(..., description="Text content of the chunk")
    score: float = Field(..., description="Hybrid fusion relevance score")
    allowed_groups: list[str] = Field(
        ..., description="Document access groups inherited from manifest"
    )


class GenerationResult(BaseModel):
    """Result emitted by the generation adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str = Field(..., description="Synthesized answer text or governed refusal message")
    behavior: BehaviorEnum = Field(..., description="Resolved pipeline behavior")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
```

---

## 2. HTTP Presentation Contracts (`src/api/schemas.py`)

Public boundary contracts matching the versioned OpenAPI 3.1 schema.

```python
from pydantic import BaseModel, ConfigDict, Field
from src.domain import BehaviorEnum, Citation


class QueryRequest(BaseModel):
    """Public inbound query payload."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language user inquiry",
        examples=["Which awslogs options configure CloudWatch region and group?"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to retrieve",
        examples=[3],
    )


class QueryResponse(BaseModel):
    """Public outbound query response payload."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., description="Synthesized answer or governed explanation")
    behavior: BehaviorEnum = Field(..., description="Pipeline outcome classification")
    citations: list[Citation] = Field(
        ..., description="List of source citations (empty for refusals)"
    )
    trace_id: str = Field(..., description="Distributed OpenTelemetry trace identifier")
    latency_ms: float = Field(
        ..., ge=0.0, description="End-to-end execution latency in milliseconds"
    )


class ErrorResponse(BaseModel):
    """Standard HTTP error response payload."""

    model_config = ConfigDict(extra="forbid")

    detail: str = Field(..., description="Actionable error description")
    error_code: str = Field(..., description="Domain or transport error code")
```

---

## 3. Abstract Domain Ports (`src/domain/ports/`)

Cross-layer behavioral contracts defined as `abc.ABC` with nominal subtyping.

### `src/domain/ports/retrieval.py`
```python
import abc
from src.domain import RetrievedChunk


class RetrievalPort(abc.ABC):
    """Abstract port for security-trimmed hybrid vector retrieval."""

    @abc.abstractmethod
    def retrieve(self, query: str, caller_groups: set[str], top_k: int = 3) -> list[RetrievedChunk]:
        """Retrieve authorized candidate chunks using dense + sparse hybrid search.

        Must enforce pre-inference security trimming (allowed_groups and status != archived).
        """
        raise NotImplementedError
```

### `src/domain/ports/generation.py`
```python
import abc
from src.domain import GenerationResult, RetrievedChunk


class GenerationPort(abc.ABC):
    """Abstract port for evidence-grounded generation."""

    @abc.abstractmethod
    def generate(self, query: str, context: list[RetrievedChunk], user_id: str) -> GenerationResult:
        """Synthesize answer strictly from retrieved context and classify behavior.

        Must protect against prompt injection directives in context.
        """
        raise NotImplementedError
```

### `src/domain/ports/identity.py`
```python
import abc
from src.domain import CallerContext


class TokenValidatorPort(abc.ABC):
    """Abstract port for bearer token cryptographic verification."""

    @abc.abstractmethod
    def validate_token(self, token: str) -> CallerContext:
        """Validate bearer token signature, claims, and expiry, returning verified caller context.
        
        Raises:
            AuthenticationError: When token is missing, expired, or invalid.
        """
        raise NotImplementedError
```

---

## 4. Qdrant Payload Filter Mapping

Pre-inference filtering query generated by `QdrantRetrievalAdapter`:

```json
{
  "filter": {
    "must": [
      {
        "key": "allowed_groups",
        "match": {
          "any": ["all-employees", "engineering-core"]
        }
      }
    ],
    "must_not": [
      {
        "key": "status",
        "match": {
          "value": "archived"
        }
      }
    ]
  }
}
```
