"""Contract test validating data/manifest.json against its schema.

In accordance with Constitution Article 17, the corpus governance manifest
is verified against its canonical schema. Divergences or values outside
closed catalogs fail before ingestion begins.
"""

import json
from pathlib import Path
from src.domain.enums import Classification, Department, IdPGroup, LifecycleStatus
from src.domain.models import ManifestRecord


def test_manifest_file_exists() -> None:
    """Verify that data/manifest.json exists on disk."""
    manifest_path = Path("data/manifest.json")
    assert manifest_path.exists(), "data/manifest.json is missing"


def test_manifest_records_conform_to_contract() -> None:
    """Verify that every record in data/manifest.json conforms to ManifestRecord schema."""
    manifest_path = Path("data/manifest.json")
    raw_content = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(raw_content, list), "data/manifest.json must be a JSON array"
    assert len(raw_content) > 0, "data/manifest.json cannot be empty"

    for entry in raw_content:
        record = ManifestRecord.model_validate(entry)
        assert record.doc_id.startswith("DOC-")
        assert record.department in Department
        assert record.classification in Classification
        assert record.status in LifecycleStatus
        for group in record.allowed_groups:
            assert group in IdPGroup


def test_manifest_referenced_files_exist() -> None:
    """Verify that every relative_path in data/manifest.json exists in data/raw/."""
    manifest_path = Path("data/manifest.json")
    raw_content = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_dir = Path("data/raw")

    for entry in raw_content:
        rel_path = entry.get("relative_path")
        assert rel_path, f"Entry {entry.get('doc_id')} missing relative_path"
        file_path = raw_dir / rel_path
        assert file_path.exists(), f"Manifest references missing file on disk: {file_path}"

