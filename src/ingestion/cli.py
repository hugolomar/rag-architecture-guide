"""Batch Ingestion Pipeline CLI Entrypoint.

Composition Root for data plane document ingestion. Wires concrete infrastructure
adapters (FastEmbed, Qdrant, OpenTelemetry) and executes the ingestion pipeline
with strict exit code handling.
"""

import sys

from src.adapters.embeddings.fastembed_adapter import FastEmbedAdapter
from src.adapters.storage.qdrant_adapter import QdrantStorageAdapter
from src.adapters.telemetry.otel_emitter import TelemetryManager
from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion_pipeline


def main() -> int:
    """CLI Entrypoint with explicit exit codes and guaranteed telemetry flush."""
    config = IngestionConfig()
    telemetry = TelemetryManager(
        service_name=config.otel_service_name,
        log_level=config.log_level,
    )

    exit_code = 0
    try:
        # NOTE(Architecture): As the Composition Root, this entrypoint wires baseline
        # concrete adapters (FastEmbedAdapter per ADR 0005, QdrantStorageAdapter per ADR 0006).
        # To test or benchmark alternative adapters (e.g. Postgres or OpenAI), wire the new
        # instance directly here. The core orchestrator (src.ingestion.pipeline) requires zero modifications.
        embedder = FastEmbedAdapter()
        storage = QdrantStorageAdapter(
            host=config.qdrant_host,
            port=config.qdrant_port,
            vector_size=embedder.dimension,
        )

        run_ingestion_pipeline(
            config=config,
            embedder=embedder,
            storage=storage,
            telemetry=telemetry,
        )
        exit_code = 0
    except ValueError as exc:
        # Schema / manifest validation failure (Exit Code 1)
        telemetry.log("ERROR", f"Manifest schema validation failure: {exc}", stage="manifest")
        exit_code = 1
    except FileNotFoundError as exc:
        # Corpus file mismatch / missing file (Exit Code 2)
        telemetry.log("ERROR", f"Corpus file mismatch or missing file: {exc}", stage="parse")
        exit_code = 2
    except ConnectionError as exc:
        # Vector store connection / operation failure (Exit Code 3)
        telemetry.log("ERROR", f"Vector store storage failure: {exc}", stage="storage")
        exit_code = 3
    except Exception as exc:
        # Generic failure
        telemetry.log("ERROR", f"Unexpected batch ingestion failure: {exc}", stage="general")
        exit_code = 3
    finally:
        try:
            telemetry.flush_and_shutdown()
        except Exception as flush_exc:
            sys.stderr.write(f"Failed to flush telemetry: {flush_exc}\n")
            if exit_code == 0:
                exit_code = 4

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

