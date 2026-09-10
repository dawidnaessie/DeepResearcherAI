"""Application configuration and environment settings.

Utilizes pydantic-settings to validate configuration parameters and load from .env.
"""

import os
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is loaded into environment variables
load_dotenv(override=True)


class Settings(BaseSettings):
    """Configuration settings for Multimodal Deep Researcher backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google Gemini API key required for the google-genai SDK.",
    )
    MODEL_NAME: str = Field(
        default="gemini-3.6-flash",
        description="Default Gemini multimodal model for intelligence extraction.",
    )
    BACKEND_HOST: str = Field(
        default="0.0.0.0",
        description="Host interface for the FastAPI backend service.",
    )
    BACKEND_PORT: int = Field(
        default=8000,
        description="Port for the FastAPI backend service.",
    )
    POLL_INITIAL_INTERVAL: float = Field(
        default=2.0,
        description="Initial delay in seconds for polling Gemini file processing status.",
    )
    POLL_MAX_INTERVAL: float = Field(
        default=10.0,
        description="Maximum backoff delay in seconds for file status polling.",
    )
    POLL_TIMEOUT_SECONDS: float = Field(
        default=180.0,
        description="Maximum seconds to wait for a file to reach the ACTIVE state.",
    )
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins for frontend-backend communication.",
    )


settings = Settings()

# Ensure GEMINI_API_KEY is synchronized with os.environ for SDK fallbacks
if settings.GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
