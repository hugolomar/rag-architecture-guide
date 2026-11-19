"""Unit tests for the batch ingestion CLI entrypoint.

Verifies the composition root exit codes (0, 1, 2, 3, 4) and error handling
contracts per contracts/ingestion-cli.md.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.cli import main

pytestmark = pytest.mark.unit


# ==============================================================================
# CLI Entrypoint & Exit Code Contracts
# ==============================================================================


@patch("src.ingestion.cli.run_ingestion_pipeline")
@patch("src.ingestion.cli.TelemetryManager")
@patch("src.ingestion.cli.QdrantStorageAdapter")
@patch("src.ingestion.cli.FastEmbedAdapter")
def test_cli_main_success_returns_exit_code_0(
    mock_embedder_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_telemetry_cls: MagicMock,
    mock_run_pipeline: MagicMock,
) -> None:
    """Verify that successful pipeline execution returns exit code 0."""
    mock_embedder = MagicMock()
    mock_embedder.dimension = 128
    mock_embedder_cls.return_value = mock_embedder

    mock_telemetry = MagicMock()
    mock_telemetry_cls.return_value = mock_telemetry

    exit_code = main()

    assert exit_code == 0
    mock_run_pipeline.assert_called_once()
    mock_telemetry.flush_and_shutdown.assert_called_once()


@patch("src.ingestion.cli.run_ingestion_pipeline", side_effect=ValueError("Schema mismatch"))
@patch("src.ingestion.cli.TelemetryManager")
@patch("src.ingestion.cli.QdrantStorageAdapter")
@patch("src.ingestion.cli.FastEmbedAdapter")
def test_cli_main_manifest_validation_error_returns_exit_code_1(
    mock_embedder_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_telemetry_cls: MagicMock,
    mock_run_pipeline: MagicMock,
) -> None:
    """Verify that manifest schema/validation errors return exit code 1."""
    mock_telemetry = MagicMock()
    mock_telemetry_cls.return_value = mock_telemetry

    exit_code = main()

    assert exit_code == 1
    mock_telemetry.log.assert_called_with(
        "ERROR",
        "Manifest schema validation failure: Schema mismatch",
        stage="manifest",
    )
    mock_telemetry.flush_and_shutdown.assert_called_once()


@patch("src.ingestion.cli.run_ingestion_pipeline", side_effect=FileNotFoundError("Missing doc.md"))
@patch("src.ingestion.cli.TelemetryManager")
@patch("src.ingestion.cli.QdrantStorageAdapter")
@patch("src.ingestion.cli.FastEmbedAdapter")
def test_cli_main_file_not_found_returns_exit_code_2(
    mock_embedder_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_telemetry_cls: MagicMock,
    mock_run_pipeline: MagicMock,
) -> None:
    """Verify that missing corpus files return exit code 2."""
    mock_telemetry = MagicMock()
    mock_telemetry_cls.return_value = mock_telemetry

    exit_code = main()

    assert exit_code == 2
    mock_telemetry.log.assert_called_with(
        "ERROR",
        "Corpus file mismatch or missing file: Missing doc.md",
        stage="parse",
    )
    mock_telemetry.flush_and_shutdown.assert_called_once()


@patch("src.ingestion.cli.run_ingestion_pipeline", side_effect=ConnectionError("Qdrant offline"))
@patch("src.ingestion.cli.TelemetryManager")
@patch("src.ingestion.cli.QdrantStorageAdapter")
@patch("src.ingestion.cli.FastEmbedAdapter")
def test_cli_main_storage_connection_error_returns_exit_code_3(
    mock_embedder_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_telemetry_cls: MagicMock,
    mock_run_pipeline: MagicMock,
) -> None:
    """Verify that vector storage connection errors return exit code 3."""
    mock_telemetry = MagicMock()
    mock_telemetry_cls.return_value = mock_telemetry

    exit_code = main()

    assert exit_code == 3
    mock_telemetry.log.assert_called_with(
        "ERROR",
        "Vector store storage failure: Qdrant offline",
        stage="storage",
    )
    mock_telemetry.flush_and_shutdown.assert_called_once()


@patch("src.ingestion.cli.run_ingestion_pipeline", side_effect=RuntimeError("Unexpected error"))
@patch("src.ingestion.cli.TelemetryManager")
@patch("src.ingestion.cli.QdrantStorageAdapter")
@patch("src.ingestion.cli.FastEmbedAdapter")
def test_cli_main_unexpected_error_returns_exit_code_3(
    mock_embedder_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_telemetry_cls: MagicMock,
    mock_run_pipeline: MagicMock,
) -> None:
    """Verify that unhandled exceptions return exit code 3."""
    mock_telemetry = MagicMock()
    mock_telemetry_cls.return_value = mock_telemetry

    exit_code = main()

    assert exit_code == 3
    mock_telemetry.log.assert_called_with(
        "ERROR",
        "Unexpected batch ingestion failure: Unexpected error",
        stage="general",
    )
    mock_telemetry.flush_and_shutdown.assert_called_once()


@patch("src.ingestion.cli.run_ingestion_pipeline")
@patch("src.ingestion.cli.TelemetryManager")
@patch("src.ingestion.cli.QdrantStorageAdapter")
@patch("src.ingestion.cli.FastEmbedAdapter")
def test_cli_main_telemetry_flush_failure_returns_exit_code_4(
    mock_embedder_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_telemetry_cls: MagicMock,
    mock_run_pipeline: MagicMock,
) -> None:
    """Verify that telemetry flush failure overrides clean run with exit code 4."""
    mock_telemetry = MagicMock()
    mock_telemetry.flush_and_shutdown.side_effect = RuntimeError("Flush buffer timed out")
    mock_telemetry_cls.return_value = mock_telemetry

    exit_code = main()

    assert exit_code == 4
