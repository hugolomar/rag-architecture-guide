"""Markdown parser for extracting frontmatter and body content.

Separates metadata frontmatter from document content in accordance with
FR-005 and constructs CanonicalDocument domain instances.
"""

from pathlib import Path
import frontmatter
from src.domain.models import CanonicalDocument, ManifestRecord


def parse_markdown_document(
    file_path: Path,
    record: ManifestRecord,
) -> CanonicalDocument:
    """Parse a Markdown file and build a CanonicalDocument instance.

    Args:
        file_path: Absolute path to the Markdown file on disk.
        record: Associated ManifestRecord containing validated governance metadata.

    Returns:
        CanonicalDocument populated with metadata, title, tags, and cleaned body.

    Raises:
        FileNotFoundError: If file_path does not exist.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Markdown file does not exist: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw_text)

    # Title extraction precedence: frontmatter title -> first # heading -> file stem
    title = post.metadata.get("title")
    if not title:
        for line in post.content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.lstrip("# ").strip()
                break
    if not title:
        title = file_path.stem.replace("-", " ").replace("_", " ").title()

    # Extract keywords/tags from metadata if available
    raw_keywords = post.metadata.get("keywords") or post.metadata.get("tags") or []
    if isinstance(raw_keywords, str):
        keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
    elif isinstance(raw_keywords, list):
        keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
    else:
        keywords = []

    return CanonicalDocument(
        doc_id=record.doc_id,
        relative_path=record.relative_path,
        department=record.department,
        allowed_groups=record.allowed_groups,
        classification=record.classification,
        status=record.status,
        title=title,
        content=post.content.strip(),
        keywords=keywords,
    )

