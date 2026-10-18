"""Pytest fixtures for the suite runners.

Loaders and assertions stay in ``evals.harness``. This module only supplies the
two callables a runner invokes. Both raise until a test overrides them with a
real pipeline or a fake. Returning an empty list or an empty answer is
forbidden: a ``deny_access`` or ``abstain`` case would pass without the system
having done anything.
"""

import pytest


@pytest.fixture
def retrieve_fn():
    """Return the phase 1 stub.

    Signature: ``retrieve_fn(query, user_id, top_k=5) -> dict`` with
    ``retrieved_doc_ids`` and ``indexed_doc_ids``. The stub raises
    ``NotImplementedError`` before it can return either.
    """

    def _stub_retrieve(query: str, user_id: str, top_k: int = 5) -> dict:
        raise NotImplementedError("Phase 1 retrieval pipeline not connected yet.")

    return _stub_retrieve


@pytest.fixture
def generate_fn():
    """Return the phase 2 stub.

    Signature: ``generate_fn(query, context_doc_ids, user_id) -> dict`` with
    ``answer`` and ``behavior``. The stub raises ``NotImplementedError``
    before it can return either.
    """

    def _stub_generate(query: str, context_doc_ids: list[str], user_id: str) -> dict:
        raise NotImplementedError("Phase 2 generation pipeline not connected yet.")

    return _stub_generate
