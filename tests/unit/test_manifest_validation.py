"""Unit tests for domain manifest validation and ingestion filesystem loader.

Tests domain manifest validation, lifecycle filtering (active vs. archived),
and schema boundary enforcement.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from src.domain.enums import LifecycleStatus
from src.domain.manifest import validate_and_partition_manifest
from src.ingestion.manifest_loader import load_and_validate_manifest

pytestmark = pytest.mark.unit


# ==============================================================================
# Pure Domain Manifest Partitioning Tests (In-Memory, No I/O)
# ==============================================================================


def test_validate_manifest_excludes_archived_in_memory() -> None:
    """Verify domain rules retain current/deprecated and exclude archived without disk I/O."""
    manifest_data = [
        {
            "doc_id": "DOC-HR-001",
            "relative_path": "doc1.md",
            "department": "HR",
            "allowed_groups": ["all-employees"],
            "classification": "internal",
            "status": "current",
        },
        {
            "doc_id": "DOC-ENG-002",
            "relative_path": "doc2.md",
            "department": "Engineering",
            "allowed_groups": ["engineering-core"],
            "classification": "internal",
            "status": "deprecated",
        },
        {
            "doc_id": "DOC-SEC-003",
            "relative_path": "doc3.md",
            "department": "Security",
            "allowed_groups": ["security-oncall"],
            "classification": "restricted",
            "status": "archived",
        },
    ]

    active_docs, archived_docs = validate_and_partition_manifest(manifest_data)

    assert len(active_docs) == 2
    assert len(archived_docs) == 1
    assert active_docs[0].doc_id == "DOC-HR-001"
    assert active_docs[0].status == LifecycleStatus.CURRENT
    assert active_docs[1].doc_id == "DOC-ENG-002"
    assert active_docs[1].status == LifecycleStatus.DEPRECATED
    assert archived_docs[0].doc_id == "DOC-SEC-003"
    assert archived_docs[0].status == LifecycleStatus.ARCHIVED


def test_validate_manifest_empty_list_returns_empty_partitions() -> None:
    """Verify that an empty manifest partition yields empty active and archived lists."""
    active_docs, archived_docs = validate_and_partition_manifest([])
    assert active_docs == []
    assert archived_docs == []


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"doc_id": "DOC-HR-001"},  # Dict instead of list of records
        "DOC-HR-001",  # String scalar instead of list
        None,  # NoneType
        12345,  # Numeric scalar
    ],
)
def test_validate_manifest_rejects_non_list_payload(invalid_payload: Any) -> None:
    """Verify fail-loud behavior when raw manifest is not a JSON array."""
    with pytest.raises(ValueError, match="must be a JSON array of records"):
        validate_and_partition_manifest(invalid_payload)


def test_validate_manifest_fail_loud_on_invalid_catalog_value_in_memory() -> None:
    """Verify fail loud when a record references an unknown department or group."""
    manifest_data = [
        {
            "doc_id": "DOC-HR-001",
            "relative_path": "doc1.md",
            "department": "UnknownDepartment",
            "allowed_groups": ["all-employees"],
            "classification": "internal",
            "status": "current",
        }
    ]

    with pytest.raises(ValueError, match="UnknownDepartment"):
        validate_and_partition_manifest(manifest_data)


# ==============================================================================
# Filesystem Manifest Loader Tests (Ingestion Adapter, Disk I/O)
# ==============================================================================


def test_load_valid_manifest_from_disk(tmp_path: Path) -> None:
    """Verify filesystem loader reads manifest.json and checks referenced files."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
    (raw_dir / "doc2.md").write_text("# Doc 2", encoding="utf-8")

    manifest_data = [
        {
            "doc_id": "DOC-HR-001",
            "relative_path": "doc1.md",
            "department": "HR",
            "allowed_groups": ["all-employees"],
            "classification": "internal",
            "status": "current",
        },
        {
            "doc_id": "DOC-SEC-003",
            "relative_path": "doc2.md",
            "department": "Security",
            "allowed_groups": ["security-oncall"],
            "classification": "restricted",
            "status": "archived",
        },
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    active_docs, archived_docs = load_and_validate_manifest(manifest_file, raw_dir)

    assert len(active_docs) == 1
    assert len(archived_docs) == 1
    assert active_docs[0].doc_id == "DOC-HR-001"
    assert active_docs[0].status == LifecycleStatus.CURRENT
    assert archived_docs[0].doc_id == "DOC-SEC-003"
    assert archived_docs[0].status == LifecycleStatus.ARCHIVED


def test_load_manifest_fail_loud_on_missing_manifest_file(tmp_path: Path) -> None:
    """Verify fail loud when manifest.json itself does not exist on disk."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    non_existent_manifest = tmp_path / "missing_manifest.json"

    with pytest.raises(FileNotFoundError, match="Corpus governance manifest not found"):
        load_and_validate_manifest(non_existent_manifest, raw_dir)


def test_load_manifest_fail_loud_on_malformed_json(tmp_path: Path) -> None:
    """Verify fail loud when manifest.json contains corrupted or non-JSON content."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text("{corrupted_json: true,", encoding="utf-8")

    with pytest.raises(ValueError, match="Corpus governance manifest is malformed JSON"):
        load_and_validate_manifest(manifest_file, raw_dir)


def test_load_manifest_fail_loud_on_missing_referenced_file(tmp_path: Path) -> None:
    """Verify fail loud when manifest references a non-existent file on disk."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    manifest_data = [
        {
            "doc_id": "DOC-HR-001",
            "relative_path": "non-existent.md",
            "department": "HR",
            "allowed_groups": ["all-employees"],
            "classification": "internal",
            "status": "current",
        }
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="references file not present on disk"):
        load_and_validate_manifest(manifest_file, raw_dir)
