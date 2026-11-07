"""Unit tests for manifest loader and lifecycle filtering.

Tests acceptance scenarios for User Story 1 (Enforce Governance and Manifest
Access Rules).
"""

import json
from pathlib import Path
import pytest
from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.manifest import load_and_validate_manifest


def test_load_valid_manifest_excludes_archived(tmp_path: Path) -> None:
    """Verify that current and deprecated docs are retained, while archived are excluded."""
    # Create sample docs in dummy raw dir
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")
    (raw_dir / "doc2.md").write_text("# Doc 2", encoding="utf-8")
    (raw_dir / "doc3.md").write_text("# Doc 3 (Archived)", encoding="utf-8")

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

    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    active_docs, archived_docs = load_and_validate_manifest(manifest_file, raw_dir)

    assert len(active_docs) == 2
    assert len(archived_docs) == 1
    assert active_docs[0].doc_id == "DOC-HR-001"
    assert active_docs[0].status == LifecycleStatus.CURRENT
    assert active_docs[1].doc_id == "DOC-ENG-002"
    assert active_docs[1].status == LifecycleStatus.DEPRECATED
    assert archived_docs[0].doc_id == "DOC-SEC-003"
    assert archived_docs[0].status == LifecycleStatus.ARCHIVED


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


def test_load_manifest_fail_loud_on_invalid_catalog_value(tmp_path: Path) -> None:
    """Verify fail loud when manifest references an unknown department or group."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "doc1.md").write_text("# Doc 1", encoding="utf-8")

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
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(ValueError):
        load_and_validate_manifest(manifest_file, raw_dir)

