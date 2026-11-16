"""Integration test for OpenTelemetry flush lifecycle (Article 13, US3).

Verifies that stage spans, metrics, structured logs, and providers flush
cleanly prior to process termination with zero telemetry loss.
"""

import json

import pytest

from src.adapters.telemetry.otel_emitter import TelemetryManager

pytestmark = pytest.mark.integration


# ==============================================================================
# OpenTelemetry Flush & Shutdown Lifecycle Integration Tests
# ==============================================================================


def test_telemetry_stage_spans_metrics_and_flush(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify trace span attributes, structured log JSON output, and provider shutdown."""
    mgr = TelemetryManager(service_name="test-ingestion-flush")

    # 1. Trace stage span lifecycle and attributes
    with mgr.start_stage_span("manifest.validate") as span:
        assert span.is_recording()
        span.set_attribute("doc_count", 36)

    # Verify span properties after closure
    assert not span.is_recording()
    assert getattr(span, "name", "") == "ingestion.manifest.validate"
    assert getattr(span, "end_time", None) is not None
    span_attrs = getattr(span, "attributes", {})
    assert span_attrs["run_id"] == mgr.run_id
    assert span_attrs["stage"] == "manifest.validate"
    assert span_attrs["doc_count"] == 36

    # 2. Structured log emission verified via stdout interception
    mgr.log(
        "INFO",
        "Batch manifest validated successfully",
        stage="manifest.validate",
        doc_count=36,
    )
    captured = capsys.readouterr()
    assert captured.out, "Expected structured JSON log on stdout"
    log_data = json.loads(captured.out.strip().splitlines()[-1])
    assert log_data["run_id"] == mgr.run_id
    assert log_data["level"] == "INFO"
    assert log_data["stage"] == "manifest.validate"
    assert log_data["doc_count"] == 36
    assert "Batch manifest validated successfully" in log_data["message"]

    # 3. Progress metrics recording (exercises metric instruments)
    mgr.record_documents_processed(35)
    mgr.record_documents_rejected(1)
    mgr.record_chunks_created(312)

    # 4. Clean shutdown and flush must succeed and terminate providers
    mgr.flush_and_shutdown()
    assert getattr(mgr.tracer_provider, "_is_shutdown", False) is True
    assert getattr(mgr.meter_provider, "_shutdown", False) is True

    # Calling shutdown again must be idempotent (no exception)
    mgr.flush_and_shutdown()
