"""Architectural contract tests enforcing Constitution Articles 4 and 19.

This module programmatically enforces clean hexagonal architecture contracts:
1. Cross-layer behavioral contracts must be abc.ABC classes with abstract methods.
2. Concrete adapters must explicitly inherit from their respective domain ports.

Layer boundaries and inward dependency direction are verified declaratively by
import-linter (lint-imports) per .importlinter in Stage A.
"""

import inspect
from abc import ABC

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.domain.ports.embeddings import EmbedderPort
from src.domain.ports.storage import ChunkStorageWriterPort


def test_behavioral_ports_are_abstract_classes() -> None:
    """Enforce Constitution Article 4: contracts must be abc.ABC with abstract methods."""
    ports = [EmbedderPort, ChunkStorageWriterPort]

    for port in ports:
        assert inspect.isclass(port), f"{port} is not a class"
        assert issubclass(port, ABC), f"{port} must inherit from abc.ABC"
        assert hasattr(port, "__abstractmethods__"), f"{port} has no abstract methods"
        assert len(port.__abstractmethods__) > 0, f"{port} must declare at least one abstract method"


def test_concrete_adapters_inherit_from_domain_ports() -> None:
    """Enforce Constitution Article 4: adapters must inherit from ports, duck typing is forbidden."""
    adapter_port_pairs = [
        (FastEmbedAdapter, EmbedderPort),
        (QdrantStorageAdapter, ChunkStorageWriterPort),
    ]

    for adapter_cls, port_cls in adapter_port_pairs:
        assert inspect.isclass(adapter_cls), f"{adapter_cls} is not a class"
        assert issubclass(adapter_cls, port_cls), (
            f"Architecture violation: {adapter_cls.__name__} must inherit from {port_cls.__name__}"
        )
