"""Unit tests for Markdown parser and frontmatter extraction.

Tests separation of metadata frontmatter from document body content.
"""

from pathlib import Path

import pytest

from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import ManifestRecord
from src.ingestion.parser import parse_markdown_document

pytestmark = pytest.mark.unit


# ==============================================================================
# Frontmatter Extraction & Title Precedence Tests
# ==============================================================================


def test_parse_markdown_with_frontmatter_precedence(tmp_path: Path) -> None:
    """Verify frontmatter title takes precedence over markdown headings."""
    doc_path = tmp_path / "test_doc.md"
    doc_path.write_text(
        "---\n"
        "title: Security Incident Response Guide\n"
        "keywords: [security, incident, oncall]\n"
        "---\n"
        "# Secondary Body Heading\n"
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
    assert canonical.relative_path == "test_doc.md"
    assert canonical.title == "Security Incident Response Guide"
    assert canonical.keywords == ["security", "incident", "oncall"]
    assert canonical.content.startswith("# Secondary Body Heading")
    assert canonical.department == Department.SECURITY
    assert canonical.allowed_groups == [IdPGroup.SECURITY_ONCALL]
    assert canonical.classification == Classification.RESTRICTED
    assert canonical.status == LifecycleStatus.CURRENT


def test_parse_markdown_without_frontmatter_fallback_heading(tmp_path: Path) -> None:
    """Verify title fallback to first H1 heading when frontmatter is omitted."""
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
    assert canonical.keywords == []


def test_parse_markdown_subheading_ignored_fallback_to_file_stem(tmp_path: Path) -> None:
    """Verify H2 subheadings (##) do not count as titles, falling back to formatted file stem."""
    doc_path = tmp_path / "employee-onboarding_checklist.md"
    doc_path.write_text(
        "## Section Overview\nChecklist content without H1 heading.\n",
        encoding="utf-8",
    )

    record = ManifestRecord(
        doc_id="DOC-HR-003",
        relative_path="employee-onboarding_checklist.md",
        department=Department.HR,
        allowed_groups=[IdPGroup.ALL_EMPLOYEES],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )

    canonical = parse_markdown_document(doc_path, record)

    # Hyphens and underscores are replaced by spaces and title-cased
    assert canonical.title == "Employee Onboarding Checklist"
    assert canonical.content == "## Section Overview\nChecklist content without H1 heading."
    assert canonical.keywords == []


# ==============================================================================
# Keywords and Tags Normalization Tests
# ==============================================================================


def test_parse_markdown_with_comma_separated_tags_sanitization(tmp_path: Path) -> None:
    """Verify comma-separated string tags are trimmed and empty tokens discarded."""
    doc_path = tmp_path / "tags_doc.md"
    doc_path.write_text(
        "---\n"
        "title: DevOps Runbook\n"
        "tags: 'kubernetes, , terraform , aws , '\n"
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


def test_parse_markdown_unexpected_keywords_type_defaults_empty(tmp_path: Path) -> None:
    """Verify non-string non-list keywords types cleanly default to an empty list."""
    doc_path = tmp_path / "invalid_kw_doc.md"
    doc_path.write_text(
        "---\ntitle: Numeric Keywords Doc\nkeywords: 12345\n---\nContent body.\n",
        encoding="utf-8",
    )

    record = ManifestRecord(
        doc_id="DOC-ENG-004",
        relative_path="invalid_kw_doc.md",
        department=Department.ENGINEERING,
        allowed_groups=[IdPGroup.ENGINEERING_CORE],
        classification=Classification.INTERNAL,
        status=LifecycleStatus.CURRENT,
    )

    canonical = parse_markdown_document(doc_path, record)

    assert canonical.title == "Numeric Keywords Doc"
    assert canonical.keywords == []


# ==============================================================================
# Filesystem Error Handling Tests
# ==============================================================================


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

    with pytest.raises(FileNotFoundError, match="Markdown file does not exist"):
        parse_markdown_document(missing_file, record)
