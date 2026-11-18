"""Unit tests for structure-preserving chunking.

Verifies that tables remain intact in single chunks, oversized tables
split across rows with repeated headers, code blocks with pipes are preserved,
and chunks inherit governance metadata.
"""

import pytest

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import CanonicalDocument, GovernedChunk
from src.ingestion.chunker import DocumentChunker, TablePreservingChunker

pytestmark = pytest.mark.unit


def _build_doc(content: str, doc_id: str = "DOC-ENG-001") -> CanonicalDocument:
    """Helper to construct a CanonicalDocument with valid governance metadata."""
    return CanonicalDocument(
        doc_id=doc_id,
        relative_path="eng/guide.md",
        department=Department.ENGINEERING,
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
        title="Guide with Tables",
        content=content,
        keywords=["table", "docker"],
    )


# ==============================================================================
# Strategy Contract & Interface Tests
# ==============================================================================


def test_document_chunker_is_abstract_interface() -> None:
    """Verify that DocumentChunker cannot be instantiated directly without implementation."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        DocumentChunker()  # type: ignore[abstract]


def test_table_preserving_chunker_satisfies_contract() -> None:
    """Verify that TablePreservingChunker implements the DocumentChunker strategy."""
    chunker = TablePreservingChunker()
    assert isinstance(chunker, DocumentChunker)


def test_custom_chunker_strategy_can_be_implemented() -> None:
    """Verify that custom chunking strategies can implement DocumentChunker."""

    class SingleChunkStrategy(DocumentChunker):
        def chunk_document(self, doc: CanonicalDocument) -> list[GovernedChunk]:
            return []

    custom = SingleChunkStrategy()
    assert isinstance(custom, DocumentChunker)
    doc = _build_doc("Sample content")
    assert custom.chunk_document(doc) == []


# ==============================================================================
# Table Integrity & Governance Inheritance Tests
# ==============================================================================


def test_chunker_preserves_table_intact_with_reading_order() -> None:
    """Verify small table is preserved intact with strictly ordered sequential chunks."""
    content = (
        "## Configuration Options\n\n"
        "Here is the parameter table:\n\n"
        "| Parameter | Type | Default |\n"
        "|---|---|---|\n"
        "| timeout | int | 30 |\n"
        "| retries | int | 3 |\n"
        "| debug | bool | false |\n\n"
        "Following paragraph explaining configuration."
    )

    chunker = TablePreservingChunker(target_chunk_tokens=600)
    doc = _build_doc(content)
    chunks = chunker.chunk_document(doc)

    # Must preserve reading order: Prose (chunk 0) -> Table (chunk 1) -> Prose (chunk 2)
    assert len(chunks) == 3
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert [c.chunk_id for c in chunks] == ["DOC-ENG-001#c0", "DOC-ENG-001#c1", "DOC-ENG-001#c2"]

    # Chunk 0: Preceding prose
    assert chunks[0].is_tabular is False
    assert "Configuration Options" in chunks[0].text

    # Chunk 1: The entire intact table
    table_chunk = chunks[1]
    assert table_chunk.is_tabular is True
    assert "| Parameter | Type | Default |" in table_chunk.text
    assert "| timeout | int | 30 |" in table_chunk.text
    assert "| debug | bool | false |" in table_chunk.text

    # Chunk 2: Following prose
    assert chunks[2].is_tabular is False
    assert "Following paragraph explaining configuration." in chunks[2].text

    # Verify governance inheritance on table chunk
    assert table_chunk.doc_id == "DOC-ENG-001"
    assert table_chunk.department == Department.ENGINEERING
    assert table_chunk.allowed_groups == [IdPGroup.ENGINEERING_CORE]
    assert table_chunk.classification == Classification.INTERNAL
    assert table_chunk.status == LifecycleStatus.CURRENT


def test_chunker_repeats_headers_on_oversized_table() -> None:
    """Verify that an oversized table repeats headers across split chunks."""
    header = "| Metric ID | Service | SLA Target | Escalation Tier |\n|---|---|---|---|\n"
    rows = "\n".join(
        f"| METRIC-{i:03d} | svc-{i} | 99.{i % 9}9% | Tier {i % 3 + 1} |" for i in range(40)
    )
    content = f"# SLA Catalog\n\n{header}{rows}\n"

    chunker = TablePreservingChunker(target_chunk_tokens=100)
    doc = _build_doc(content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 1
    tabular_chunks = [c for c in chunks if c.is_tabular]
    assert len(tabular_chunks) > 1

    # Every chunk derived from the table must be tabular and contain the full header
    for chunk in tabular_chunks:
        assert chunk.is_tabular is True
        assert "| Metric ID | Service | SLA Target | Escalation Tier |" in chunk.text
        assert "|---|---|---|---|" in chunk.text
        assert chunk.doc_id == "DOC-ENG-001"
        assert chunk.allowed_groups == [IdPGroup.ENGINEERING_CORE]


# ==============================================================================
# Code Block Heuristics & Edge Cases Tests
# ==============================================================================


def test_chunker_does_not_treat_fenced_code_pipes_as_tables() -> None:
    """Verify that pipes inside fenced code blocks (```) are never treated as Markdown tables."""
    content = (
        "## Deployment Script\n\n"
        "Run the following pipeline command:\n\n"
        "```bash\n"
        "cat logs.txt | grep 'ERROR' | awk '{print $1, $2}' | sort | uniq -c\n"
        "| pipeline | stage-1 | run |\n"
        "```\n\n"
        "The command processes pipeline outputs."
    )

    chunker = TablePreservingChunker(target_chunk_tokens=600)
    doc = _build_doc(content)
    chunks = chunker.chunk_document(doc)

    # Must NOT have any tabular chunks despite pipes inside ```
    assert len(chunks) >= 1
    assert all(c.is_tabular is False for c in chunks)
    # The code block content must be preserved in the chunk text
    full_text = "\n".join(c.text for c in chunks)
    assert "cat logs.txt | grep 'ERROR'" in full_text


@pytest.mark.parametrize(
    "empty_content",
    [
        "",  # Pure empty string
        "   ",  # Whitespace spaces
        "\t\t\n\n  \r\n",  # Mixed tabs, newlines, and spaces
    ],
)
def test_chunker_empty_or_whitespace_document_returns_empty_list(empty_content: str) -> None:
    """Verify that chunking an empty or whitespace-only document returns an empty list."""
    chunker = TablePreservingChunker()
    doc = _build_doc(empty_content)
    assert chunker.chunk_document(doc) == []


# ==============================================================================
# Pure Prose Splitting & Sequential Indexing Tests
# ==============================================================================


def test_chunker_splits_pure_prose_without_tables() -> None:
    """Verify that pure prose text is chunked into non-tabular blocks with sequential indices."""
    paragraphs = [f"Paragraph {i}: Detailed explanation of system architecture." for i in range(20)]
    content = "\n\n".join(paragraphs)

    chunker = TablePreservingChunker(target_chunk_tokens=50)
    doc = _build_doc(content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk.is_tabular is False
        assert chunk.chunk_index == i
        assert chunk.doc_id == "DOC-ENG-001"
        assert chunk.chunk_id == f"DOC-ENG-001#c{i}"
