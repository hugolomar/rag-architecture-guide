"""Unit tests for domain enums, models, and boundary validation rules.

Enforces Constitution Article 4 (Closed governance catalogs, strict Pydantic v2
boundary validation, and prohibition of extra undocumented fields) and data-model.md.
"""

import pytest
from pydantic import ValidationError

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import (
    CanonicalDocument,
    GovernedChunk,
    ManifestRecord,
    VectorizedChunk,
)

pytestmark = pytest.mark.unit


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


def test_manifest_record_forbids_extra_fields() -> None:
    """Verify that undocumented extra fields are prohibited at boundaries (Article 4)."""
    with pytest.raises(ValidationError):
        ManifestRecord(
            doc_id="DOC-ENG-001",
            relative_path="eng/arch.md",
            department=Department.ENGINEERING,
            allowed_groups=[IdPGroup.ENGINEERING_CORE],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
            extra_field="malicious_payload",  # type: ignore[call-arg]
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


def test_canonical_document_forbids_extra_fields() -> None:
    """Verify that extra fields are forbidden on CanonicalDocument."""
    with pytest.raises(ValidationError):
        CanonicalDocument(
            doc_id="DOC-ENG-002",
            relative_path="eng/overview.md",
            department=Department.ENGINEERING,
            allowed_groups=[IdPGroup.ENGINEERING_CORE],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
            title="Overview",
            content="Content",
            unexpected_attr="prohibited",  # type: ignore[call-arg]
        )


def test_governed_chunk_instantiation_and_defaults() -> None:
    """Verify GovernedChunk inherits governance metadata and defaults is_tabular to False."""
    chunk = GovernedChunk(
        chunk_id="DOC-HR-001#c0",
        doc_id="DOC-HR-001",
        chunk_index=0,
        text="Remote work guidelines.",
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        department=Department.HR,
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )
    assert chunk.chunk_id == "DOC-HR-001#c0"
    assert chunk.is_tabular is False
    assert chunk.allowed_groups == [IdPGroup.ALL_EMPLOYEES]


def test_governed_chunk_negative_index_raises_validation_error() -> None:
    """Verify that chunk_index must be greater than or equal to 0 (ge=0)."""
    with pytest.raises(ValidationError):
        GovernedChunk(
            chunk_id="DOC-HR-001#c-1",
            doc_id="DOC-HR-001",
            chunk_index=-1,
            text="Invalid chunk.",
            allowed_groups=[IdPGroup.ALL_EMPLOYEES],
            department=Department.HR,
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
        )


def test_vectorized_chunk_instantiation() -> None:
    """Verify VectorizedChunk composition with dual vectors and underlying GovernedChunk."""
    chunk = GovernedChunk(
        chunk_id="DOC-SEC-001#c0",
        doc_id="DOC-SEC-001",
        chunk_index=0,
        text="Authentication secret key rotation.",
        allowed_groups=[IdPGroup.SECURITY_ONCALL],
        department=Department.SECURITY,
        classification=Classification.RESTRICTED,
        status=LifecycleStatus.CURRENT,
    )
    vchunk = VectorizedChunk(
        chunk=chunk,
        dense_vector=[0.1] * 1024,
        sparse_indices=[5, 12],
        sparse_values=[1.0, 2.5],
    )
    assert vchunk.chunk == chunk
    assert len(vchunk.dense_vector) == 1024
    assert vchunk.sparse_indices == [5, 12]
    assert vchunk.sparse_values == [1.0, 2.5]
