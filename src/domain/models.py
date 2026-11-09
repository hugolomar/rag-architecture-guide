"""Domain models for governed enterprise documents and chunks.

In accordance with Constitution Articles 2, 3, and 5, this module defines the
canonical domain representations with strict boundary validation via Pydantic v2.
"""

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus


class ManifestRecord(BaseModel):
    """Represents an individual verified record in data/manifest.json.

    Validates identifiers against the corporate pattern and checks that
    departments, classifications, lifecycle statuses, and identity groups
    belong to strictly closed taxonomies (Constitution Article 5).
    """

    doc_id: str = Field(
        ...,
        pattern=r"^DOC-[A-Z]{2,4}-[0-9]{3}$",
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

    doc_id: str = Field(..., description="Unique corporate document ID.")
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

    In accordance with Constitution Article 5 and FR-007, every chunk carries
    the parent document's doc_id, allowed_groups, and status inseparably.
    """

    chunk_id: str = Field(..., description="Deterministic ID: {doc_id}#c{chunk_index}")
    doc_id: str = Field(..., description="Parent document identifier.")
    allowed_groups: list[IdPGroup] = Field(..., min_length=1, description="Inherited access groups.")
    status: LifecycleStatus = Field(..., description="Inherited lifecycle status.")
    department: Department = Field(..., description="Inherited owning department.")
    classification: Classification = Field(..., description="Inherited classification.")
    chunk_index: int = Field(..., ge=0, description="Sequential 0-indexed position within doc.")
    text: str = Field(..., description="Raw chunk text preserving Markdown tables and formatting.")
    is_tabular: bool = Field(default=False, description="True if chunk contains a Markdown table.")

    model_config = ConfigDict(extra="forbid")


class VectorizedChunk(BaseModel):
    """The enriched chunk containing dual vector embeddings prepared for storage.

    In accordance with Constitution Article 14, every chunk is represented
    by both a 1024-dimensional dense semantic vector and sparse BM25 token weights.
    """

    chunk: GovernedChunk = Field(..., description="The underlying governed chunk.")
    dense_vector: list[float] = Field(..., description="1024-dim dense embedding from FastEmbed BGE.")
    sparse_indices: list[int] = Field(..., description="BM25 token indices.")
    sparse_values: list[float] = Field(..., description="BM25 token weights.")

    model_config = ConfigDict(extra="forbid")
