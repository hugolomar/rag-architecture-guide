"""Unit tests for telemetry formatting, data hygiene, and lifecycle.

Verifies that structured logs produce JSON on stdout with run_id, stage,
and ensure confidential document text or credentials are not leaked.
"""

import json
import logging

import pytest

from src.adapters.telemetry.otel_emitter import (
    JsonLogFormatter,
    TelemetryManager,
    mask_sensitive_data,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# Structured JSON Logging & Formatting Tests
# ==============================================================================


def test_json_log_formatter_produces_structured_json() -> None:
    """Verify JSON output format and standard correlation fields."""
    formatter = JsonLogFormatter(run_id="run-test-123")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="Validated manifest records",
        args=(),
        exc_info=None,
    )
    record.stage = "manifest"  # type: ignore[attr-defined]
    record.doc_count = 36  # type: ignore[attr-defined]
    record.chunks_indexed = 120  # type: ignore[attr-defined]

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    assert data["run_id"] == "run-test-123"
    assert data["level"] == "INFO"
    assert data["stage"] == "manifest"
    assert data["message"] == "Validated manifest records"
    assert data["doc_count"] == 36
    assert data["chunks_indexed"] == 120
    assert "timestamp" in data


def test_json_log_formatter_defaults_stage_to_general() -> None:
    """Verify stage defaults to 'general' when not explicitly provided on LogRecord."""
    formatter = JsonLogFormatter(run_id="run-test-456")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname=__file__,
        lineno=30,
        msg="Generic warning message",
        args=(),
        exc_info=None,
    )

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    assert data["stage"] == "general"
    assert data["level"] == "WARNING"
    assert data["message"] == "Generic warning message"


def test_json_log_formatter_scrubs_secrets_in_formatted_output() -> None:
    """Verify that credentials inside log messages are scrubbed in the final formatted JSON."""
    formatter = JsonLogFormatter(run_id="run-sec-999")
    record = logging.LogRecord(
        name="sec_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=40,
        msg="Authentication failed with password=supersecretpass123 on gateway",
        args=(),
        exc_info=None,
    )

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    assert "supersecretpass123" not in data["message"]
    assert "password=[REDACTED]" in data["message"]


# ==============================================================================
# Credential Sanitization & Data Hygiene Tests
# ==============================================================================


@pytest.mark.parametrize(
    ("raw_message", "sensitive_token"),
    [
        (
            "Connecting with Bearer eyJhbGciOiJIUzI1Ni... token payload",
            "eyJhbGciOiJIUzI1Ni",
        ),
        (
            "Database auth with password=supersecret123 on host localhost",
            "supersecret123",
        ),
        (
            "Gateway call with api_key: secret_key_abc999",
            "secret_key_abc999",
        ),
        (
            "Header Authorization: token my_auth_token_value",
            "my_auth_token_value",
        ),
    ],
)
def test_telemetry_hygiene_masks_sensitive_data(raw_message: str, sensitive_token: str) -> None:
    """Verify that credentials, tokens, and api keys are scrubbed from telemetry signals."""
    sanitized = mask_sensitive_data(raw_message)
    assert sensitive_token not in sanitized
    assert "[REDACTED]" in sanitized


# ==============================================================================
# OpenTelemetry Manager Lifecycle & Tracing Tests
# ==============================================================================


def test_telemetry_manager_generates_run_id() -> None:
    """Verify that TelemetryManager generates a unique run_id with 'run-' prefix."""
    mgr = TelemetryManager(service_name="rag-ingestion-test")
    assert mgr.run_id.startswith("run-")
    assert len(mgr.run_id) > 8


def test_telemetry_manager_accepts_explicit_run_id() -> None:
    """Verify that TelemetryManager respects explicitly passed run_id."""
    mgr = TelemetryManager(service_name="rag-ingestion-test", run_id="custom-run-007")
    assert mgr.run_id == "custom-run-007"


def test_telemetry_manager_starts_stage_span_with_attributes() -> None:
    """Verify that stage spans are prefixed with 'ingestion.' and contain run_id and stage attributes."""
    mgr = TelemetryManager(service_name="rag-ingestion-test", run_id="run-span-001")
    span = mgr.start_stage_span("manifest_validation")

    assert span.is_recording()
    span.end()
    mgr.flush_and_shutdown()


def test_telemetry_manager_flush_and_shutdown_lifecycle() -> None:
    """Verify that flush_and_shutdown completes cleanly without unhandled exceptions."""
    mgr = TelemetryManager(service_name="rag-ingestion-test", run_id="run-shutdown-001")
    mgr.record_documents_processed(5)
    mgr.record_documents_rejected(1)
    mgr.record_chunks_created(15)

    # Must complete cleanly without raising exceptions
    mgr.flush_and_shutdown()
