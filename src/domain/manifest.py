"""Domain validation and lifecycle filtering for manifest records.

Validates raw manifest entries against closed taxonomies and partitions records
according to document lifecycle invariants (active vs archived).
"""

from src.domain.enums import LifecycleStatus
from src.domain.models import ManifestRecord


def validate_and_partition_manifest(
    raw_records: object,
) -> tuple[list[ManifestRecord], list[ManifestRecord]]:
    """Validate raw manifest records in memory and partition by lifecycle status.

    Args:
        raw_records: Parsed manifest payload expected to be a list of record dicts.

    Returns:
        A tuple (active_records, archived_records) where active_records contains
        documents with status 'current' or 'deprecated', and archived_records
        contains excluded 'archived' documents.

    Raises:
        ValueError: If raw_records is not a list or any entry violates schema/closed catalogs.
    """
    if not isinstance(raw_records, list):
        raise ValueError("Corpus governance manifest must be a JSON array of records.")

    active_records: list[ManifestRecord] = []
    archived_records: list[ManifestRecord] = []

    for item in raw_records:
        try:
            record = ManifestRecord.model_validate(item)
        except Exception as exc:
            raise ValueError(f"Manifest record validation failed for item {item}: {exc}") from exc

        if record.status == LifecycleStatus.ARCHIVED:
            archived_records.append(record)
        else:
            active_records.append(record)

    return active_records, archived_records
