"""Unit tests for backend configuration settings."""

from src.backend.config import Settings


def test_default_settings() -> None:
    """Verify default settings values and properties."""
    settings = Settings()
    assert settings.MODEL_NAME == "gemini-2.5-flash"
    assert settings.BACKEND_HOST == "0.0.0.0"
    assert settings.BACKEND_PORT == 8000
    assert settings.POLL_TIMEOUT_SECONDS == 180.0
    assert "*" in settings.CORS_ORIGINS
