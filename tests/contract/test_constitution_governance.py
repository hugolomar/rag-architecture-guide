"""Contract test verifying repository constitution governance and amendment integrity.

In accordance with Constitution Article 12 (Executable architecture) and Section VII
(Articles 15-16 Governance), constitution integrity, synchronization impact reports,
and semantic versioning metadata are automatically verified before merges.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

CONSTITUTION_PATH = Path(".specify/memory/constitution.md")


@pytest.fixture(scope="module")
def constitution_content() -> str:
    """Load constitution content once for all governance tests."""
    assert CONSTITUTION_PATH.exists(), f"Constitution file {CONSTITUTION_PATH} is missing"
    content = CONSTITUTION_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "Constitution file cannot be empty"
    return content


def test_constitution_file_not_empty(constitution_content: str) -> None:
    """Verify that the constitution file is non-empty."""
    assert len(constitution_content.strip()) > 0, "Constitution file cannot be empty"


def test_constitution_sync_impact_report_present(constitution_content: str) -> None:
    """Verify that constitution has an up-to-date SYNC IMPACT REPORT header."""
    assert "SYNC IMPACT REPORT" in constitution_content, (
        "Constitution missing mandatory 'SYNC IMPACT REPORT' header comment"
    )

    version_change_match = re.search(
        r"Version change:\s*([^\s]+)\s*->\s*([^\s]+)", constitution_content
    )
    assert version_change_match is not None, (
        "SYNC IMPACT REPORT missing valid 'Version change: <old> -> <new>' declaration"
    )

    target_version = version_change_match.group(2)
    assert re.match(r"^\d+\.\d+\.\d+$", target_version), (
        f"Target version '{target_version}' in SYNC IMPACT REPORT must follow SemVer"
    )


def test_constitution_version_footer_matches_sync_report(constitution_content: str) -> None:
    """Verify that the footer **Version** matches the SYNC IMPACT REPORT target version."""
    version_change_match = re.search(
        r"Version change:\s*([^\s]+)\s*->\s*([^\s]+)", constitution_content
    )
    assert version_change_match is not None
    target_version = version_change_match.group(2)

    footer_match = re.search(r"\*\*Version\*\*:\s*([^\s|]+)", constitution_content)
    assert footer_match is not None, "Constitution footer missing '**Version**: X.Y.Z'"
    footer_version = footer_match.group(1).strip()

    assert footer_version == target_version, (
        f"Constitution version mismatch: SYNC IMPACT REPORT targets '{target_version}' "
        f"but footer declares '{footer_version}'"
    )

    last_amended_match = re.search(
        r"\*\*Last Amended\*\*:\s*(\d{4}-\d{2}-\d{2})", constitution_content
    )
    assert last_amended_match is not None, (
        "Constitution footer missing valid '**Last Amended**: YYYY-MM-DD'"
    )


@pytest.mark.parametrize(
    "required_article",
    [
        "Article 15 — Supremacy",
        "Article 16 — Amendment procedure, versioning, and compliance",
    ],
)
def test_constitution_governance_articles_intact(
    constitution_content: str, required_article: str
) -> None:
    """Verify that foundational Governance articles (Articles 15-16) are present."""
    assert required_article in constitution_content, (
        f"Constitution missing required governance clause: '{required_article}'"
    )
