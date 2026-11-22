"""Dependency injection providers for FastAPI composition root."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from qdrant_client import QdrantClient

from src.adapters.auth.oidc_validator import OIDCValidatorAdapter
from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.adapters.generation.litellm_adapter import LiteLLMGenerationAdapter
from src.adapters.generation.mock_adapter import MockGenerationAdapter
from src.adapters.retrieval.qdrant_retrieval import QdrantRetrievalAdapter
from src.api.config import APISettings
from src.domain.ports.generation import GenerationPort
from src.domain.ports.identity import TokenValidatorPort
from src.domain.ports.retrieval import RetrievalPort
from src.orchestration.query_orchestrator import QueryOrchestrator


@lru_cache
def get_settings() -> APISettings:
    """Provide cached application settings."""
    return APISettings()


def get_token_validator(
    settings: Annotated[APISettings, Depends(get_settings)],
) -> TokenValidatorPort:
    """Wire and provide the OIDC token validator adapter."""
    return OIDCValidatorAdapter(
        public_key=settings.oidc_public_key,
        expected_issuer=settings.oidc_expected_issuer,
        expected_audience=settings.oidc_expected_audience,
    )


def get_qdrant_client(
    settings: Annotated[APISettings, Depends(get_settings)],
) -> QdrantClient:
    """Wire Qdrant client connection."""
    if settings.qdrant_in_memory:
        return QdrantClient(":memory:")
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def get_retriever(
    settings: Annotated[APISettings, Depends(get_settings)],
    client: Annotated[QdrantClient, Depends(get_qdrant_client)],
) -> RetrievalPort:
    """Wire Qdrant hybrid retrieval adapter."""
    embedder = FastEmbedAdapter(
        dense_model_name=settings.dense_model_name,
        sparse_model_name=settings.sparse_model_name,
    )
    return QdrantRetrievalAdapter(
        client=client,
        embedder=embedder,
        collection_name=settings.qdrant_collection,
    )


def get_generator(
    settings: Annotated[APISettings, Depends(get_settings)],
) -> GenerationPort:
    """Wire generation adapter (Mock or LiteLLM)."""
    if settings.use_mock_generation:
        return MockGenerationAdapter()
    return LiteLLMGenerationAdapter(model_name=settings.llm_model_name)


def get_orchestrator(
    token_validator: Annotated[TokenValidatorPort, Depends(get_token_validator)],
    retriever: Annotated[RetrievalPort, Depends(get_retriever)],
    generator: Annotated[GenerationPort, Depends(get_generator)],
) -> QueryOrchestrator:
    """Wire the central application query orchestrator."""
    return QueryOrchestrator(
        token_validator=token_validator,
        retriever=retriever,
        generator=generator,
    )

