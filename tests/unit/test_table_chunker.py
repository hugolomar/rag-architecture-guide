"""Unit tests for structure-preserving chunking (FR-006, User Story 2).

Verifies that tables remain intact in single chunks, oversized tables
split across rows with repeated headers, and chunks inherit governance metadata.
"""

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import CanonicalDocument, GovernedChunk
from src.ingestion.chunker import DocumentChunker, TablePreservingChunker


def test_table_preserving_chunker_satisfies_contract() -> None:
    """Verify that TablePreservingChunker implements the DocumentChunker strategy."""
    chunker = TablePreservingChunker()
    assert isinstance(chunker, DocumentChunker)


def _build_doc(content: str) -> CanonicalDocument:
    return CanonicalDocument(
        doc_id="DOC-ENG-001",
        relative_path="eng/guide.md",
        department=Department.ENGINEERING,
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
        title="Guide with Tables",
        content=content,
        keywords=["table", "docker"],
    )


def test_chunker_preserves_table_intact() -> None:
    """Verify that a small table is preserved intact within a single chunk."""
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

    assert len(chunks) >= 1
    # Check that at least one chunk has is_tabular=True and contains the entire table
    tabular_chunks = [c for c in chunks if c.is_tabular]
    assert len(tabular_chunks) == 1
    table_chunk = tabular_chunks[0]
    assert "| Parameter | Type | Default |" in table_chunk.text
    assert "| timeout | int | 30 |" in table_chunk.text
    assert "| debug | bool | false |" in table_chunk.text

    # Verify governance inheritance (FR-007)
    assert table_chunk.doc_id == "DOC-ENG-001"
    assert table_chunk.allowed_groups == [IdPGroup.ENGINEERING_CORE]
    assert table_chunk.status == LifecycleStatus.CURRENT
    assert table_chunk.chunk_id == f"DOC-ENG-001#c{table_chunk.chunk_index}"


def test_chunker_repeats_headers_on_oversized_table() -> None:
    """Verify that an oversized table repeats headers across split chunks."""
    # Build a table with 40 rows that exceeds a small chunk token target
    header = "| Metric ID | Service | SLA Target | Escalation Tier |\n|---|---|---|---|\n"
    rows = "\n".join(f"| METRIC-{i:03d} | svc-{i} | 99.{i%9}9% | Tier {i%3 + 1} |" for i in range(40))
    content = f"# SLA Catalog\n\n{header}{rows}\n"

    chunker = TablePreservingChunker(target_chunk_tokens=100)
    doc = _build_doc(content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 1
    tabular_chunks = [c for c in chunks if c.is_tabular]
    assert len(tabular_chunks) > 1
    # Every chunk derived from the table must be tabular and contain the header
    for chunk in tabular_chunks:
        assert chunk.is_tabular
        assert "| Metric ID | Service | SLA Target | Escalation Tier |" in chunk.text
        assert "|---|---|---|---|" in chunk.text
        assert chunk.doc_id == "DOC-ENG-001"


def test_custom_chunker_strategy_can_be_implemented() -> None:
    """Verify that custom chunking strategies can implement DocumentChunker."""

    class SingleChunkStrategy(DocumentChunker):
        def chunk_document(self, doc: CanonicalDocument) -> list[GovernedChunk]:
            return []

    custom = SingleChunkStrategy()
    assert isinstance(custom, DocumentChunker)
    doc = _build_doc("Sample content")
    assert custom.chunk_document(doc) == []
