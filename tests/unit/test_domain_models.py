"""Unit tests for domain enums, models, and boundary validation rules.

Enforces Constitution Article 4 (Closed governance catalogs, strict Pydantic v2
boundary validation, and prohibition of extra undocumented fields) and data-model.md.
"""

from typing import Any

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


# ==============================================================================
# Closed Catalogs Tests (Article 4)
# ==============================================================================


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


# ==============================================================================
# ManifestRecord Validation & Boundary Tests
# ==============================================================================


# The corporate identifier regex ^DOC-[A-Z]{2,4}-[0-9]{3}$ has multiple independent
# logical branches: 2-4 uppercase department letters, hyphen delimiters, and exactly 3 digits.
# We test positive boundary partitions (2, 3, and 4 letters, min/max 3-digit sequences)
# to ensure valid edge cases are never falsely rejected.
@pytest.mark.parametrize(
    "valid_id",
    [
        "DOC-HR-001",  # 2 department letters (minimum length boundary)
        "DOC-ENG-042",  # 3 department letters (nominal length)
        "DOC-CORP-999",  # 4 department letters (maximum length boundary)
        "DOC-IT-000",  # Minimum 3-digit numeric sequence (000)
        "DOC-LEGL-999",  # Maximum 3-digit numeric sequence (999)
    ],
)
def test_manifest_record_valid_doc_id_boundaries(valid_id: str) -> None:
    """Verify that valid doc_id boundary partitions pass regex validation."""
    record = ManifestRecord(
        doc_id=valid_id,
        relative_path="corp/doc.md",
        department=Department.HR,
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )
    assert record.doc_id == valid_id
    assert record.department == Department.HR
    assert record.allowed_groups == [IdPGroup.ALL_EMPLOYEES]


# Negative boundary testing: Each partition isolates a specific regex violation
# (acronym too short, too long, lowercase, digit count mismatch, missing prefixes, or whitespace).
@pytest.mark.parametrize(
    "invalid_id",
    [
        "INVALID-ID",  # Completely unformatted string
        "DOC-A-001",  # Department acronym too short (< 2 uppercase characters)
        "DOC-TOOLONG-001",  # Department acronym too long (> 4 uppercase characters)
        "doc-hr-001",  # Lowercase characters are strictly prohibited
        "DOC-hr-001",  # Mixed case characters are strictly prohibited
        "DOC-HR-01",  # Too few digits (< 3 required)
        "DOC-HR-0001",  # Too many digits (> 3 required)
        "HR-001",  # Missing DOC- corporate prefix
        "DOC_HR_001",  # Underscore delimiter instead of hyphen
        "DOC-HR-ABC",  # Non-numeric sequential identifier
        " DOC-HR-001 ",  # Untrimmed leading/trailing whitespace
    ],
)
def test_manifest_record_invalid_doc_id_regex(invalid_id: str) -> None:
    """Verify fail-loud behavior across all negative regex equivalence partitions."""
    with pytest.raises(ValidationError, match="doc_id"):
        ManifestRecord(
            doc_id=invalid_id,
            relative_path="file.md",
            department=Department.HR,
            allowed_groups=[IdPGroup.ALL_EMPLOYEES],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("department", "Marketing"),
        ("classification", "top-secret"),
        ("status", "draft"),
        ("allowed_groups", ["unauthorized-external-group"]),
    ],
)
def test_manifest_record_invalid_enum_values(field_name: str, invalid_value: Any) -> None:
    """Verify fail-loud validation when closed taxonomy enums receive unapproved values."""
    base_kwargs: dict[str, Any] = {
        "doc_id": "DOC-ENG-001",
        "relative_path": "eng/arch.md",
        "department": Department.ENGINEERING,
        "allowed_groups": [IdPGroup.ALL_EMPLOYEES],
        "classification": Classification.INTERNAL,
        "status": LifecycleStatus.CURRENT,
    }
    base_kwargs[field_name] = invalid_value
    with pytest.raises(ValidationError, match=field_name):
        ManifestRecord(**base_kwargs)


def test_manifest_record_empty_allowed_groups() -> None:
    """Verify fail-loud validation when allowed_groups is empty (min_length=1)."""
    with pytest.raises(ValidationError, match="allowed_groups"):
        ManifestRecord(
            doc_id="DOC-SEC-001",
            relative_path="sec/keys.md",
            department=Department.SECURITY,
            allowed_groups=[],
            classification=Classification.RESTRICTED,
            status=LifecycleStatus.CURRENT,
        )


def test_manifest_record_forbids_extra_fields() -> None:
    """Verify that undocumented extra fields are prohibited at boundaries (Article 4)."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ManifestRecord(
            doc_id="DOC-ENG-001",
            relative_path="eng/arch.md",
            department=Department.ENGINEERING,
            allowed_groups=[IdPGroup.ENGINEERING_CORE],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
            extra_field="malicious_payload",  # type: ignore[call-arg]
        )


def test_manifest_record_serialization_round_trip() -> None:
    """Verify serialization to dict and parsing from raw primitive dictionary."""
    payload: dict[str, Any] = {
        "doc_id": "DOC-FIN-001",
        "relative_path": "fin/budget.md",
        "department": "Finance",
        "allowed_groups": ["leadership"],
        "classification": "restricted",
        "status": "current",
    }
    record = ManifestRecord.model_validate(payload)
    assert record.department == Department.FINANCE
    assert record.allowed_groups == [IdPGroup.LEADERSHIP]
    assert record.model_dump(mode="json") == payload


# ==============================================================================
# CanonicalDocument Validation Tests
# ==============================================================================


def test_canonical_document_instantiation_and_keywords_default() -> None:
    """Verify CanonicalDocument construction and keywords default_factory behavior."""
    # When keywords is omitted, it must default to an empty list
    doc_without_keywords = CanonicalDocument(
        doc_id="DOC-ENG-002",
        relative_path="eng/overview.md",
        department=Department.ENGINEERING,
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
        title="Architecture Overview",
        content="# Overview",
    )
    assert doc_without_keywords.keywords == []

    # When keywords are provided, they must be preserved
    doc_with_keywords = doc_without_keywords.model_copy(
        update={"keywords": ["architecture", "docker"]}
    )
    assert doc_with_keywords.keywords == ["architecture", "docker"]


def test_canonical_document_empty_allowed_groups() -> None:
    """Verify that CanonicalDocument rejects empty allowed_groups (min_length=1)."""
    with pytest.raises(ValidationError, match="allowed_groups"):
        CanonicalDocument(
            doc_id="DOC-ENG-002",
            relative_path="eng/overview.md",
            department=Department.ENGINEERING,
            allowed_groups=[],
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
            title="Overview",
            content="Content",
        )


def test_canonical_document_forbids_extra_fields() -> None:
    """Verify that extra fields are forbidden on CanonicalDocument (Article 4)."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
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


# ==============================================================================
# GovernedChunk Validation Tests
# ==============================================================================


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
    assert chunk.chunk_index == 0  # Lower boundary test (ge=0)
    assert chunk.is_tabular is False

    # Explicit is_tabular override
    tabular_chunk = chunk.model_copy(update={"is_tabular": True})
    assert tabular_chunk.is_tabular is True


def test_governed_chunk_empty_allowed_groups() -> None:
    """Verify that GovernedChunk rejects empty allowed_groups (min_length=1)."""
    with pytest.raises(ValidationError, match="allowed_groups"):
        GovernedChunk(
            chunk_id="DOC-HR-001#c0",
            doc_id="DOC-HR-001",
            chunk_index=0,
            text="Remote work guidelines.",
            allowed_groups=[],
            department=Department.HR,
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
        )


def test_governed_chunk_negative_index_raises_validation_error() -> None:
    """Verify that chunk_index must be greater than or equal to 0 (ge=0)."""
    with pytest.raises(ValidationError, match="chunk_index"):
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


def test_governed_chunk_forbids_extra_fields() -> None:
    """Verify that extra fields are forbidden on GovernedChunk (Article 4)."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GovernedChunk(
            chunk_id="DOC-HR-001#c0",
            doc_id="DOC-HR-001",
            chunk_index=0,
            text="Text",
            allowed_groups=[IdPGroup.ALL_EMPLOYEES],
            department=Department.HR,
            classification=Classification.INTERNAL,
            status=LifecycleStatus.CURRENT,
            extra_field="prohibited",  # type: ignore[call-arg]
        )


# ==============================================================================
# VectorizedChunk Validation Tests
# ==============================================================================


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


def test_vectorized_chunk_forbids_extra_fields() -> None:
    """Verify that extra fields are forbidden on VectorizedChunk (Article 4)."""
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
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        VectorizedChunk(
            chunk=chunk,
            dense_vector=[0.1] * 1024,
            sparse_indices=[5, 12],
            sparse_values=[1.0, 2.5],
            extra_field="prohibited",  # type: ignore[call-arg]
        )
