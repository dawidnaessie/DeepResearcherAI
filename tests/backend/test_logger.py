"""Unit tests for the production-grade Loguru logging subsystem."""

import json
from pathlib import Path
from loguru import logger

from src.backend.core.logger import get_logger, setup_logging


def test_logger_sinks_creation(tmp_path: Path) -> None:
    """Verify setup_logging creates app.log and error.log sinks and writes records."""
    test_logs_dir = tmp_path / "logs"
    setup_logging(log_dir=test_logs_dir)

    log = get_logger("test_module")
    log.info("Test telemetry message", job_id="job_123", file_size_mb=4.2)

    app_log = test_logs_dir / "app.log"
    assert app_log.exists()

    # Read and parse structured JSON line
    with open(app_log, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) >= 1
    last_line = lines[-1]
    parsed = json.loads(last_line)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test telemetry message"
    assert "timestamp" in parsed
    assert "extra" in parsed
    assert parsed["extra"]["job_id"] == "job_123"
    assert parsed["extra"]["file_size_mb"] == 4.2


def test_error_log_sink(tmp_path: Path) -> None:
    """Verify error.log captures exceptions and stack traces."""
    test_logs_dir = tmp_path / "logs"
    setup_logging(log_dir=test_logs_dir)

    log = get_logger()
    try:
        raise ValueError("Simulated pipeline failure")
    except ValueError:
        log.exception("Pipeline failed unexpectedly", execution_stage="synthesis")

    error_log = test_logs_dir / "error.log"
    assert error_log.exists()

    with open(error_log, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ERROR" in content
    assert "Pipeline failed unexpectedly" in content
    assert "ValueError: Simulated pipeline failure" in content


def test_get_logger_binding() -> None:
    """Verify get_logger returns a valid bound logger."""
    bound_logger = get_logger("custom_context")
    assert bound_logger is not None
