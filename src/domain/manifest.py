"""Manifest loader and lifecycle filtering service.

Validates data/manifest.json against closed taxonomies and partitions records
according to document lifecycle invariants (FR-001, FR-002, FR-003, FR-004).
"""

import json
from pathlib import Path

from src.domain.enums import LifecycleStatus
from src.domain.models import ManifestRecord


def load_and_validate_manifest(
    manifest_path: Path,
    raw_dir: Path,
) -> tuple[list[ManifestRecord], list[ManifestRecord]]:
    """Load, validate, and partition corpus manifest records.

    Args:
        manifest_path: Path to the corpus governance manifest.json.
        raw_dir: Directory containing raw Markdown documents.

    Returns:
        A tuple (active_records, archived_records) where active_records contains
        documents with status 'current' or 'deprecated', and archived_records
        contains excluded 'archived' documents.

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

    if not isinstance(content, list):
        raise ValueError("Corpus governance manifest must be a JSON array of records.")

    active_records: list[ManifestRecord] = []
    archived_records: list[ManifestRecord] = []

    for item in content:
        try:
            record = ManifestRecord.model_validate(item)
        except Exception as exc:
            raise ValueError(f"Manifest record validation failed for item {item}: {exc}") from exc

        target_file = raw_dir / record.relative_path
        if not target_file.is_file():
            raise FileNotFoundError(
                f"Document '{record.doc_id}' references file not present on disk: {target_file}"
            )

        if record.status == LifecycleStatus.ARCHIVED:
            archived_records.append(record)
        else:
            active_records.append(record)

    return active_records, archived_records

