"""Domain models for governed enterprise documents and chunks.

Defines canonical representations for documents, chunks, and manifest entries
with strict boundary validation via Pydantic v2.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus

DocId = Annotated[
    str,
    StringConstraints(
        pattern=r"^DOC-[A-Z]{2,4}-[0-9]{3}$",
    ),
]

ChunkId = Annotated[
    str,
    StringConstraints(
        pattern=r"^DOC-[A-Z]{2,4}-[0-9]{3}#c[0-9]+$",
    ),
]


class ManifestRecord(BaseModel):
    """Represents an individual verified record in data/manifest.json.

    Validates identifiers against the corporate pattern and checks that
    departments, classifications, lifecycle statuses, and identity groups
    belong to strictly closed taxonomies.
    """

    doc_id: DocId = Field(
        ...,
        description="Unique corporate identifier (e.g., DOC-HR-001, DOC-ENG-001).",
    )
    relative_path: str = Field(
        ...,
        description="Path relative to data/raw/ pointing to a Markdown file.",
    )
    department: Department = Field(
        ...,
        description="Owning department from the closed Department enum.",
    )
    allowed_groups: list[IdPGroup] = Field(
        ...,
        min_length=1,
        description="Non-empty list of authorized identity groups.",
    )
    classification: Classification = Field(
        ...,
        description="Information sensitivity classification.",
    )
    status: LifecycleStatus = Field(
        ...,
        description="Lifecycle status determining indexing eligibility.",
    )

    model_config = ConfigDict(extra="forbid")


class CanonicalDocument(BaseModel):
    """The canonical, parsed enterprise document ready for chunking.

    Carries metadata extracted from manifest and document frontmatter alongside
    the Markdown body content.
    """

    doc_id: DocId = Field(..., description="Unique corporate document ID.")
    relative_path: str = Field(..., description="Relative file path in corpus.")
    department: Department = Field(..., description="Owning department.")
    allowed_groups: list[IdPGroup] = Field(..., min_length=1, description="Authorized IdP groups.")
    classification: Classification = Field(..., description="Sensitivity classification.")
    status: LifecycleStatus = Field(..., description="Lifecycle status.")
    title: str = Field(..., description="Extracted from frontmatter or first markdown heading.")
    content: str = Field(..., description="Markdown body text without frontmatter.")
    keywords: list[str] = Field(
        default_factory=list,
        description="Tags or keywords extracted from frontmatter.",
    )

    model_config = ConfigDict(extra="forbid")


class GovernedChunk(BaseModel):
    """An indivisible segment of text that inherits its parent document governance.

    Every chunk carries the parent document's doc_id, allowed_groups, and status inseparably.
    """

    chunk_id: ChunkId = Field(..., description="Deterministic ID: {doc_id}#c{chunk_index}")
    doc_id: DocId = Field(..., description="Parent document identifier.")
    allowed_groups: list[IdPGroup] = Field(
        ..., min_length=1, description="Inherited access groups."
    )
    status: LifecycleStatus = Field(..., description="Inherited lifecycle status.")
    department: Department = Field(..., description="Inherited owning department.")
    classification: Classification = Field(..., description="Inherited classification.")
    chunk_index: int = Field(..., ge=0, description="Sequential 0-indexed position within doc.")
    text: str = Field(..., description="Raw chunk text preserving Markdown tables and formatting.")
    is_tabular: bool = Field(default=False, description="True if chunk contains a Markdown table.")

    model_config = ConfigDict(extra="forbid")


class VectorizedChunk(BaseModel):
    """The enriched chunk containing dual vector embeddings prepared for storage.

    Every chunk is represented by both a dense semantic vector and sparse lexical token weights.
    """

    chunk: GovernedChunk = Field(..., description="The underlying governed chunk.")
    dense_vector: list[float] = Field(..., description="Dense semantic embedding vector.")
    sparse_indices: list[int] = Field(..., description="Sparse token vocabulary indices.")
    sparse_values: list[float] = Field(..., description="Sparse BM25 token weight values.")

    model_config = ConfigDict(extra="forbid")
