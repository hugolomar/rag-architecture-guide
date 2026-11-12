"""Unit tests for domain manifest validation and ingestion filesystem loader.

Tests acceptance scenarios for User Story 1 (Enforce Governance and Manifest
Access Rules).
"""

import json
from pathlib import Path

import pytest

from src.domain.enums import LifecycleStatus
from src.domain.manifest import validate_and_partition_manifest
from src.ingestion.manifest_loader import load_and_validate_manifest


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

    with pytest.raises(ValueError):
        validate_and_partition_manifest(manifest_data)


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


def test_load_manifest_fail_loud_on_missing_file(tmp_path: Path) -> None:
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

    with pytest.raises(FileNotFoundError):
        load_and_validate_manifest(manifest_file, raw_dir)

