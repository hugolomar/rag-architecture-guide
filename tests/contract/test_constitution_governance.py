"""Contract test verifying repository constitution governance and amendment integrity.

In accordance with Constitution Article 19 (Executable architecture) and Section IX
(Articles 28-31 Governance), constitution integrity, synchronization impact reports,
and semantic versioning metadata are automatically verified before merges.
"""

import re
import unittest
from pathlib import Path


class TestConstitutionGovernance(unittest.TestCase):
    """Verifies that constitution amendments strictly follow the governance protocol."""

    def setUp(self) -> None:
        self.constitution_path = Path(".specify/memory/constitution.md")
        self.assertTrue(
            self.constitution_path.exists(),
            "Constitution file .specify/memory/constitution.md is missing",
        )
        self.content = self.constitution_path.read_text(encoding="utf-8")

    def test_constitution_file_not_empty(self) -> None:
        """Verify that the constitution file is non-empty."""
        self.assertGreater(len(self.content.strip()), 0, "Constitution file cannot be empty")

    def test_constitution_sync_impact_report_present(self) -> None:
        """Verify that constitution has an up-to-date SYNC IMPACT REPORT header."""
        self.assertIn(
            "SYNC IMPACT REPORT",
            self.content,
            "Constitution missing mandatory 'SYNC IMPACT REPORT' header comment",
        )

        version_change_match = re.search(r"Version change:\s*([^\s]+)\s*->\s*([^\s]+)", self.content)
        self.assertIsNotNone(
            version_change_match,
            "SYNC IMPACT REPORT missing valid 'Version change: <old> -> <new>' declaration",
        )

        target_version = version_change_match.group(2)  # type: ignore[union-attr]
        self.assertRegex(
            target_version,
            r"^\d+\.\d+\.\d+$",
            f"Target version '{target_version}' in SYNC IMPACT REPORT must follow SemVer",
        )

    def test_constitution_version_footer_matches_sync_report(self) -> None:
        """Verify that the footer **Version** matches the SYNC IMPACT REPORT target version."""
        version_change_match = re.search(r"Version change:\s*([^\s]+)\s*->\s*([^\s]+)", self.content)
        self.assertIsNotNone(version_change_match)
        target_version = version_change_match.group(2)  # type: ignore[union-attr]

        footer_match = re.search(r"\*\*Version\*\*:\s*([^\s|]+)", self.content)
        self.assertIsNotNone(footer_match, "Constitution footer missing '**Version**: X.Y.Z'")
        footer_version = footer_match.group(1).strip()  # type: ignore[union-attr]

        self.assertEqual(
            footer_version,
            target_version,
            f"Constitution version mismatch: SYNC IMPACT REPORT targets '{target_version}' "
            f"but footer declares '{footer_version}'",
        )

        last_amended_match = re.search(r"\*\*Last Amended\*\*:\s*(\d{4}-\d{2}-\d{2})", self.content)
        self.assertIsNotNone(
            last_amended_match,
            "Constitution footer missing valid '**Last Amended**: YYYY-MM-DD'",
        )

    def test_constitution_governance_articles_intact(self) -> None:
        """Verify that foundational Governance articles (Articles 15-16) are present."""
        required_articles = [
            "Article 15 — Supremacy",
            "Article 16 — Amendment procedure, versioning, and compliance",
        ]

        for article in required_articles:
            self.assertIn(
                article,
                self.content,
                f"Constitution missing required governance clause: '{article}'",
            )


if __name__ == "__main__":
    unittest.main()
