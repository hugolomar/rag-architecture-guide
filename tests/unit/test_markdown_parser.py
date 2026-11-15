"""Unit tests for Markdown parser and frontmatter extraction.

Tests separation of metadata frontmatter from document body content
(FR-005, User Story 1).
"""

from pathlib import Path

import pytest

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import ManifestRecord
from src.ingestion.parser import parse_markdown_document

pytestmark = pytest.mark.unit


def test_parse_markdown_with_frontmatter(tmp_path: Path) -> None:
    """Verify parsing of document with YAML frontmatter."""
    doc_path = tmp_path / "test_doc.md"
    doc_path.write_text(
        "---\n"
        "title: Security Incident Response Guide\n"
        "keywords: [security, incident, oncall]\n"
        "---\n"
        "# Incident Guide\n"
        "This is the body content of the security guide.\n",
        encoding="utf-8",
    )

    record = ManifestRecord(
        doc_id="DOC-SEC-001",
        relative_path="test_doc.md",
        department=Department.SECURITY,
        allowed_groups=[IdPGroup.SECURITY_ONCALL],
        classification=Classification.RESTRICTED,
        status=LifecycleStatus.CURRENT,
    )

    canonical = parse_markdown_document(doc_path, record)

    assert canonical.doc_id == "DOC-SEC-001"
    assert canonical.title == "Security Incident Response Guide"
    assert "security" in canonical.keywords
    assert canonical.content.startswith("# Incident Guide")
    assert canonical.department == Department.SECURITY
    assert canonical.allowed_groups == [IdPGroup.SECURITY_ONCALL]


def test_parse_markdown_with_comma_separated_keywords(tmp_path: Path) -> None:
    """Verify parsing when keywords in frontmatter are comma-delimited string."""
    doc_path = tmp_path / "tags_doc.md"
    doc_path.write_text(
        "---\n"
        "title: DevOps Runbook\n"
        "tags: 'kubernetes, terraform, aws'\n"
        "---\n"
        "Runbook text content.\n",
        encoding="utf-8",
    )

    record = ManifestRecord(
        doc_id="DOC-ENG-003",
        relative_path="tags_doc.md",
        department=Department.ENGINEERING,
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )

    canonical = parse_markdown_document(doc_path, record)

    assert canonical.title == "DevOps Runbook"
    assert canonical.keywords == ["kubernetes", "terraform", "aws"]


def test_parse_markdown_without_frontmatter_fallback_heading(tmp_path: Path) -> None:
    """Verify title fallback to first heading when frontmatter is omitted."""
    doc_path = tmp_path / "plain_doc.md"
    doc_path.write_text(
        "# Remote Work Policy 2026\nEmployees may work remotely up to 3 days per week.\n",
        encoding="utf-8",
    )

    record = ManifestRecord(
        doc_id="DOC-HR-002",
        relative_path="plain_doc.md",
        department=Department.HR,
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )

    canonical = parse_markdown_document(doc_path, record)

    assert canonical.title == "Remote Work Policy 2026"
    assert "Employees may work remotely" in canonical.content


def test_parse_markdown_without_heading_fallback_file_stem(tmp_path: Path) -> None:
    """Verify title fallback to formatted file stem when no frontmatter or heading exists."""
    doc_path = tmp_path / "vacation_policy_guide.md"
    doc_path.write_text(
        "Standard vacation accrual is 2 days per calendar month.\n",
        encoding="utf-8",
    )

    record = ManifestRecord(
        doc_id="DOC-HR-003",
        relative_path="vacation_policy_guide.md",
        department=Department.HR,
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )

    canonical = parse_markdown_document(doc_path, record)

    assert canonical.title == "Vacation Policy Guide"
    assert canonical.content == "Standard vacation accrual is 2 days per calendar month."


def test_parse_markdown_fail_loud_on_missing_file(tmp_path: Path) -> None:
    """Verify fail loud with FileNotFoundError when document file does not exist on disk."""
    missing_file = tmp_path / "does_not_exist.md"
    record = ManifestRecord(
        doc_id="DOC-HR-004",
        relative_path="does_not_exist.md",
        department=Department.HR,
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )

    with pytest.raises(FileNotFoundError):
        parse_markdown_document(missing_file, record)
