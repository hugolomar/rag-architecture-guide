"""Architectural contract tests enforcing Constitution Articles 3 and 12.

This module programmatically enforces clean hexagonal architecture contracts:
1. Cross-layer behavioral contracts must be abc.ABC classes with abstract methods.
2. Concrete adapters must explicitly inherit from their respective domain ports.

Layer boundaries and inward dependency direction are verified declaratively by
import-linter (lint-imports) per .importlinter in Stage A.
"""

import inspect
from abc import ABC

import pytest

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.storage import ChunkStorageWriterPort

pytestmark = pytest.mark.contract


@pytest.mark.parametrize(
    "port",
    [
        EmbedderPort,
        ChunkStorageWriterPort,
    ],
)
def test_behavioral_ports_are_abstract_classes(port: type) -> None:
    """Enforce Constitution Article 3: contracts must be abc.ABC with abstract methods."""
    assert inspect.isclass(port), f"{port} is not a class"
    assert issubclass(port, ABC), f"{port} must inherit from abc.ABC"
    assert hasattr(port, "__abstractmethods__"), f"{port} has no abstract methods"
    assert len(port.__abstractmethods__) > 0, f"{port} must declare at least one abstract method"


@pytest.mark.parametrize(
    ("adapter_cls", "port_cls"),
    [
        (FastEmbedAdapter, EmbedderPort),
        (QdrantStorageAdapter, ChunkStorageWriterPort),
    ],
)
def test_concrete_adapters_inherit_from_domain_ports(adapter_cls: type, port_cls: type) -> None:
    """Enforce Constitution Article 3: adapters must inherit from ports, duck typing is forbidden."""
    assert inspect.isclass(adapter_cls), f"{adapter_cls} is not a class"
    assert issubclass(adapter_cls, port_cls), (
        f"Architecture violation: {adapter_cls.__name__} must inherit from {port_cls.__name__}"
    )
