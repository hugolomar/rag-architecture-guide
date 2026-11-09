"""Unit tests for domain enums, models, and validation rules.

Enforces Constitution Article 5 (Closed governance catalogs and fail-loud
boundary validation) and data-model.md specifications.
"""

import pytest
from pydantic import ValidationError

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import CanonicalDocument, ManifestRecord


def test_closed_catalogs_values() -> None:
    """Verify that closed governance catalogs contain exactly the approved values."""
    assert {d.value for d in Department} == {"HR", "Engineering", "Security", "Finance", "Legal"}
    assert {c.value for c in Classification} == {"public", "internal", "restricted"}
    assert {s.value for s in LifecycleStatus} == {"current", "deprecated", "archived"}
    assert {g.value for g in IdPGroup} == {
        "all-employees",
        "people-team",
        "engineering-core",
        "security-oncall",
        "leadership",
    }


def test_manifest_record_valid() -> None:
    """Verify that a valid manifest record instantiates successfully."""
    record = ManifestRecord(
        doc_id="DOC-HR-001",
        relative_path="hr/remote-work.md",
        department=Department.HR,
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )
    assert record.doc_id == "DOC-HR-001"
    assert record.department == Department.HR
    assert record.allowed_groups == [IdPGroup.ALL_EMPLOYEES]


def test_manifest_record_invalid_doc_id_regex() -> None:
    """Verify fail-loud behavior on invalid doc_id regex."""
    with pytest.raises(ValidationError):
        ManifestRecord(
            doc_id="INVALID-ID",
            relative_path="file.md",
            department=Department.HR,
            allowed_groups=[IdPGroup.ALL_EMPLOYEES],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
        )


def test_manifest_record_empty_allowed_groups() -> None:
    """Verify fail-loud validation when allowed_groups is empty (minItems: 1)."""
    with pytest.raises(ValidationError):
        ManifestRecord(
            doc_id="DOC-SEC-001",
            relative_path="sec/keys.md",
            department=Department.SECURITY,
            allowed_groups=[],
            classification=Classification.RESTRICTED,
            status=LifecycleStatus.CURRENT,
        )


def test_manifest_record_invalid_enum_values() -> None:
    """Verify fail loud when unknown departments or groups are passed."""
    with pytest.raises(ValidationError):
        ManifestRecord(
            doc_id="DOC-ENG-001",
            relative_path="eng/arch.md",
            department="Marketing",  # type: ignore[arg-type]
            allowed_groups=[IdPGroup.ALL_EMPLOYEES],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
        )


def test_canonical_document_instantiation() -> None:
    """Verify canonical document construction and attributes."""
    doc = CanonicalDocument(
        doc_id="DOC-ENG-002",
        relative_path="eng/overview.md",
        department=Department.ENGINEERING,
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
        title="Engineering Architecture Overview",
        content="# Overview\nThis is architecture content.",
        keywords=["architecture", "docker"],
    )
    assert doc.doc_id == "DOC-ENG-002"
    assert doc.title == "Engineering Architecture Overview"
    assert "architecture" in doc.keywords

