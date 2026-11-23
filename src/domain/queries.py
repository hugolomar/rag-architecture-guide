"""Domain entities for queries, identity context, and evidence synthesis.

Defines Pydantic v2 models representing the query runtime lifecycle, verified
caller context, candidate evidence chunks, and synthesis results.
"""

from pydantic import BaseModel, ConfigDict, Field

from src.domain.documents import ChunkId, DocId
from src.domain.enums import BehaviorEnum


class Citation(BaseModel):
    """Attribution link to an authorized source chunk."""

    doc_id: DocId = Field(..., description="Document identifier, e.g. DOC-ENG-001")
    chunk_id: ChunkId = Field(..., description="Chunk identifier, e.g. DOC-ENG-001#c0")

    model_config = ConfigDict(extra="forbid", frozen=True)


class CallerContext(BaseModel):
    """Verified identity context resolved from authoritative token claims."""

    user_id: str = Field(..., description="Unique subject identifier from token sub claim")
    groups: set[str] = Field(
        ..., description="Authoritative group memberships from token groups claim"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class RetrievedChunk(BaseModel):
    """Internal domain representation of an authorized candidate chunk."""

    chunk_id: ChunkId = Field(..., description="Unique chunk identifier")
    doc_id: DocId = Field(..., description="Parent document identifier")
    text: str = Field(..., description="Text content of the chunk")
    score: float = Field(..., description="Hybrid fusion relevance score")
    allowed_groups: list[str] = Field(
        ..., description="Document access groups inherited from manifest"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationResult(BaseModel):
    """Result emitted by the generation adapter."""

    answer: str = Field(..., description="Synthesized answer text or governed refusal message")
    behavior: BehaviorEnum = Field(..., description="Resolved pipeline behavior")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")

    model_config = ConfigDict(extra="forbid", frozen=True)
