"""Application settings and configuration for the Runtime Plane."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """FastAPI runtime configuration loaded from environment variables."""

    # OIDC Configuration
    oidc_public_key: str = ""
    oidc_expected_issuer: str = "https://idp.crateexpectations.example/realms/enterprise"
    oidc_expected_audience: str = "rag-query-api"

    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "governed_documents"
    qdrant_in_memory: bool = False

    # Embedding Model Configuration
    dense_model_name: str = "BAAI/bge-small-en-v1.5"
    sparse_model_name: str = "Qdrant/bm25"

    # Generation Model Configuration
    llm_model_name: str = "gemini/gemini-1.5-flash"
    use_mock_generation: bool = False

    # Operational Limits & Telemetry
    timeout_budget_seconds: float = 10.0
    otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "rag-query-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
