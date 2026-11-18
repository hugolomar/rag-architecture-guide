"""Contract test validating data/manifest.json against its schema.

The corpus governance manifest is verified against its canonical schema.
Divergences or values outside closed catalogs fail before ingestion begins.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from src.domain.models import ManifestRecord

pytestmark = pytest.mark.contract

MANIFEST_PATH = Path("data/manifest.json")
RAW_DATA_DIR = Path("data/raw")


# ==============================================================================
# Manifest File Existence & Fixture
# ==============================================================================


def test_manifest_file_exists() -> None:
    """Verify that data/manifest.json exists on disk."""
    assert MANIFEST_PATH.exists(), f"{MANIFEST_PATH} is missing"


@pytest.fixture(scope="module")
def raw_manifest() -> Sequence[dict[str, Any]]:
    """Load and parse data/manifest.json once for the suite."""
    assert MANIFEST_PATH.exists(), f"{MANIFEST_PATH} is missing"
    content = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(content, list), f"{MANIFEST_PATH} must be a JSON array"
    assert len(content) > 0, f"{MANIFEST_PATH} cannot be empty"
    return content


# ==============================================================================
# Schema Conformance & Referential Integrity Tests
# ==============================================================================


def test_manifest_records_conform_to_contract(raw_manifest: Sequence[dict[str, Any]]) -> None:
    """Verify that every record conforms strictly to ManifestRecord schema and closed catalogs."""
    records = TypeAdapter(list[ManifestRecord]).validate_python(raw_manifest)
    assert len(records) == len(raw_manifest)


def test_manifest_referenced_files_exist(raw_manifest: Sequence[dict[str, Any]]) -> None:
    """Verify that every relative_path referenced in manifest exists in data/raw/."""
    missing_files = [
        RAW_DATA_DIR / entry["relative_path"]
        for entry in raw_manifest
        if not (RAW_DATA_DIR / entry.get("relative_path", "")).exists()
    ]
    assert not missing_files, f"Manifest references missing files on disk: {missing_files}"
