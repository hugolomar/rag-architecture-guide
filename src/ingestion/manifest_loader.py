"""Filesystem manifest loader for the ingestion pipeline.

Reads data/manifest.json from disk, delegates schema/lifecycle validation to the
pure domain layer, and verifies that referenced Markdown files exist on disk.
"""

import json
from pathlib import Path

from src.domain.manifest import validate_and_partition_manifest
from src.domain.models import ManifestRecord


def load_and_validate_manifest(
    manifest_path: Path,
    raw_dir: Path,
) -> tuple[list[ManifestRecord], list[ManifestRecord]]:
    """Load manifest.json from disk, validate domain rules, and verify file paths.

    Args:
        manifest_path: Path to the corpus governance manifest.json.
        raw_dir: Directory containing raw Markdown documents.

    Returns:
        A tuple (active_records, archived_records) validated against domain rules.

    Raises:
        FileNotFoundError: If manifest_path does not exist or a referenced
            relative_path is not found on disk.
        ValueError: If JSON is invalid or violates schema/closed catalogs.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Corpus governance manifest not found: {manifest_path}")

    try:
        content = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Corpus governance manifest is malformed JSON: {exc}") from exc

    active_records, archived_records = validate_and_partition_manifest(content)

    for record in (*active_records, *archived_records):
        target_file = raw_dir / record.relative_path
        if not target_file.is_file():
            raise FileNotFoundError(
                f"Document '{record.doc_id}' references file not present on disk: {target_file}"
            )

    return active_records, archived_records

