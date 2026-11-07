"""Pipeline and environment configuration model.

In accordance with Constitution Article 27, container definitions and batch
processes are environment-agnostic; all runtime configuration is injected
exclusively via environment variables.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionConfig(BaseSettings):
    """Runtime configuration for the governed document ingestion pipeline.

    Loads values from environment variables or sensible defaults specified
    in contracts/ingestion-cli.md.
    """

    rag_data_dir: Path = Field(
        default=Path("data/raw"),
        description="Path to the directory containing raw Markdown documents.",
        alias="RAG_DATA_DIR",
    )
    rag_manifest_path: Path = Field(
        default=Path("data/manifest.json"),
        description="Path to the corpus governance manifest JSON file.",
        alias="RAG_MANIFEST_PATH",
    )
    qdrant_host: str = Field(
        default="localhost",
        description="Hostname or IP address of the Qdrant vector database.",
        alias="QDRANT_HOST",
    )
    qdrant_port: int = Field(
        default=6333,
        description="REST/HTTP port for Qdrant service.",
        alias="QDRANT_PORT",
    )
    qdrant_collection_name: str = Field(
        default="governed_docs",
        description="Target Qdrant collection name.",
        alias="QDRANT_COLLECTION_NAME",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4318",
        description="OpenTelemetry OTLP HTTP receiver endpoint.",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_service_name: str = Field(
        default="rag-ingestion",
        description="Service name reported in OpenTelemetry traces and metrics.",
        alias="OTEL_SERVICE_NAME",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR).",
        alias="LOG_LEVEL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

