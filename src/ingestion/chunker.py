"""Pluggable Markdown chunking strategy and structure-preserving implementation.

Defines the abstract DocumentChunker strategy contract and the TablePreservingChunker
baseline, which identifies Markdown tables and keeps them intact within single chunks,
repeating table headers across continuation chunks if a table exceeds the target chunk size.
"""

from abc import ABC, abstractmethod

from src.domain.models import CanonicalDocument, GovernedChunk


class DocumentChunker(ABC):
    """Abstract strategy contract for splitting canonical documents into governed chunks."""

    @abstractmethod
    def chunk_document(self, doc: CanonicalDocument) -> list[GovernedChunk]:
        """Split a canonical document into a sequence of governed chunks.

        Args:
            doc: CanonicalDocument with validated governance attributes.

        Returns:
            List of GovernedChunk instances in reading order.
        """
        raise NotImplementedError


class TablePreservingChunker(DocumentChunker):
    """Chunks Markdown documents while strictly preserving table integrity.

    Assigns inherited governance metadata to each generated GovernedChunk.
    """

    def __init__(self, target_chunk_tokens: int = 600) -> None:
        """Initialize the chunker with a target token budget per chunk.

        Args:
            target_chunk_tokens: Approximate target tokens per chunk (~4 chars/token).
        """
        self.target_chunk_tokens = target_chunk_tokens
        self.target_chunk_chars = target_chunk_tokens * 4

    def chunk_document(self, doc: CanonicalDocument) -> list[GovernedChunk]:
        """Split a canonical document into a sequence of governed chunks.

        Args:
            doc: CanonicalDocument with validated governance attributes.

        Returns:
            List of GovernedChunk instances in reading order.
        """
        raw_blocks = self._split_into_blocks(doc.content)
        raw_chunks: list[tuple[str, bool]] = []  # (text, is_tabular)

        current_text_blocks: list[str] = []
        current_len = 0

        for block, is_table in raw_blocks:
            if is_table:
                # Flush any pending prose blocks
                if current_text_blocks:
                    flushed_text = "\n\n".join(current_text_blocks).strip()
                    if flushed_text:
                        raw_chunks.append((flushed_text, False))
                    current_text_blocks = []
                    current_len = 0

                # Process the table block
                table_chunks = self._chunk_table_block(block)
                for tc in table_chunks:
                    raw_chunks.append((tc, True))
            else:
                block_len = len(block)
                if current_len + block_len > self.target_chunk_chars and current_text_blocks:
                    flushed_text = "\n\n".join(current_text_blocks).strip()
                    if flushed_text:
                        raw_chunks.append((flushed_text, False))
                    current_text_blocks = [block]
                    current_len = block_len
                else:
                    current_text_blocks.append(block)
                    current_len += block_len

        if current_text_blocks:
            flushed_text = "\n\n".join(current_text_blocks).strip()
            if flushed_text:
                raw_chunks.append((flushed_text, False))

        # Build GovernedChunk models with governance inheritance
        governed_chunks: list[GovernedChunk] = []
        for idx, (text, is_tabular) in enumerate(raw_chunks):
            governed_chunks.append(
                GovernedChunk(
                    chunk_id=f"{doc.doc_id}#c{idx}",
                    doc_id=doc.doc_id,
                    allowed_groups=doc.allowed_groups,
                    status=doc.status,
                    department=doc.department,
                    classification=doc.classification,
                    chunk_index=idx,
                    text=text,
                    is_tabular=is_tabular,
                )
            )

        return governed_chunks

    def _split_into_blocks(self, content: str) -> list[tuple[str, bool]]:
        """Separate Markdown into tabular blocks and standard prose blocks.

        Guarantees that lines inside fenced code blocks (```) are never misidentified
        as Markdown tables, and table rows are recognized even if trailing pipes are omitted.
        """
        lines = content.splitlines()
        blocks: list[tuple[str, bool]] = []
        current_lines: list[str] = []
        in_table = False
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # Track fenced code blocks to prevent confusing bash pipes with tables
            if stripped.startswith("```"):
                in_code_block = not in_code_block

            # Table row heuristic: requires pipe and not inside a code block
            is_table_line = (
                not in_code_block
                and stripped.startswith("|")
                and (stripped.endswith("|") or "|" in stripped[1:])
            )

            if is_table_line:
                if not in_table:
                    if current_lines:
                        text = "\n".join(current_lines).strip()
                        if text:
                            blocks.append((text, False))
                        current_lines = []
                    in_table = True
                current_lines.append(line)
            else:
                if in_table:
                    text = "\n".join(current_lines).strip()
                    if text:
                        blocks.append((text, True))
                    current_lines = []
                    in_table = False
                current_lines.append(line)

        if current_lines:
            text = "\n".join(current_lines).strip()
            if text:
                blocks.append((text, in_table))

        return blocks

    def _chunk_table_block(self, table_text: str) -> list[str]:
        """Chunk a table block, repeating headers if table exceeds target limit."""
        lines = [line for line in table_text.splitlines() if line.strip()]
        if len(lines) <= 2:
            return [table_text]

        # Extract header and separator
        header_lines = lines[:2]
        header_text = "\n".join(header_lines) + "\n"
        data_rows = lines[2:]

        # If entire table fits within budget, keep it intact
        if len(table_text) <= self.target_chunk_chars:
            return [table_text]

        # Otherwise, split across row boundaries and repeat headers
        chunks: list[str] = []
        current_rows: list[str] = []
        current_len = len(header_text)

        for row in data_rows:
            row_len = len(row) + 1
            if current_len + row_len > self.target_chunk_chars and current_rows:
                chunk_str = header_text + "\n".join(current_rows)
                chunks.append(chunk_str)
                current_rows = [row]
                current_len = len(header_text) + row_len
            else:
                current_rows.append(row)
                current_len += row_len

        if current_rows:
            chunk_str = header_text + "\n".join(current_rows)
            chunks.append(chunk_str)

        return chunks
