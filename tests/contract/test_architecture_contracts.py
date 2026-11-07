"""Architectural contract tests enforcing Constitution Articles 2, 4, and 19.

This module programmatically enforces clean hexagonal architecture boundaries:
1. Domain layer must have zero imports from adapters, ingestion, or third-party infrastructure.
2. Cross-layer behavioral contracts must be abc.ABC classes with abstract methods.
"""

import ast
import inspect
from abc import ABC
from pathlib import Path
import pytest
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.storage import ChunkStorageWriterPort


def test_domain_has_zero_infrastructure_imports() -> None:
    """Enforce Constitution Articles 2 and 19 via AST analysis.

    Scans every Python file in src/domain/ and asserts that no import references
    src.adapters, src.ingestion, qdrant_client, fastembed, or opentelemetry.
    """
    domain_dir = Path("src/domain")
    assert domain_dir.exists(), "src/domain directory does not exist"

    forbidden_roots = {"src.adapters", "adapters", "src.ingestion", "ingestion", "qdrant_client", "fastembed", "opentelemetry"}

    for py_file in domain_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert alias.name not in forbidden_roots and root not in forbidden_roots, (
                        f"Architecture violation in {py_file}: forbidden import '{alias.name}'"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    assert node.module not in forbidden_roots and root not in forbidden_roots, (
                        f"Architecture violation in {py_file}: forbidden from-import '{node.module}'"
                    )


def test_behavioral_ports_are_abstract_classes() -> None:
    """Enforce Constitution Article 4: contracts must be abc.ABC with abstract methods."""
    ports = [EmbedderPort, ChunkStorageWriterPort]

    for port in ports:
        assert inspect.isclass(port), f"{port} is not a class"
        assert issubclass(port, ABC), f"{port} must inherit from abc.ABC"
        assert hasattr(port, "__abstractmethods__"), f"{port} has no abstract methods"
        assert len(port.__abstractmethods__) > 0, f"{port} must declare at least one abstract method"
