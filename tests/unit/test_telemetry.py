"""Unit tests for telemetry formatting and data hygiene (Article 13, US3).

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


def test_telemetry_hygiene_masks_sensitive_data() -> None:
    """Verify that credentials, tokens, and api keys are scrubbed from telemetry signals (Article 13)."""
    raw_messages = [
        "Connecting with Bearer eyJhbGciOiJIUzI1Ni... token payload",
        "Database auth with password=supersecret123 on host localhost",
        "Gateway call with api_key: secret_key_abc999",
        "Header Authorization: token my_auth_token_value",
    ]

    for raw in raw_messages:
        sanitized = mask_sensitive_data(raw)
        assert "supersecret123" not in sanitized
        assert "secret_key_abc999" not in sanitized
        assert "my_auth_token_value" not in sanitized
        assert "[REDACTED]" in sanitized


def test_telemetry_manager_generates_run_id() -> None:
    """Verify that TelemetryManager generates a unique run_id with 'run-' prefix."""
    mgr = TelemetryManager(service_name="rag-ingestion-test")
    assert mgr.run_id.startswith("run-")
    assert len(mgr.run_id) > 8


def test_telemetry_manager_accepts_explicit_run_id() -> None:
    """Verify that TelemetryManager respects explicitly passed run_id."""
    mgr = TelemetryManager(service_name="rag-ingestion-test", run_id="custom-run-007")
    assert mgr.run_id == "custom-run-007"
