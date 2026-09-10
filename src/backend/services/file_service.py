"""Gemini File Management Service.

Handles uploading multimodal files via the modern google-genai SDK and safely
polling until files reach the ACTIVE state before inference.
"""

import asyncio
from collections.abc import AsyncIterator
import contextlib
import logging
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiFileError(Exception):
    """Base exception for Gemini file operations."""


class GeminiFileProcessingError(GeminiFileError):
    """Raised when file processing enters FAILED state."""


class GeminiFileTimeoutError(GeminiFileError):
    """Raised when file does not reach ACTIVE state within the timeout window."""


def _is_active(state: Any) -> bool:
    """Check if the given state represents an ACTIVE file."""
    if state is None:
        return False
    state_str = getattr(state, "name", str(state)).upper()
    return "ACTIVE" in state_str


def _is_failed(state: Any) -> bool:
    """Check if the given state represents a FAILED file."""
    if state is None:
        return False
    state_str = getattr(state, "name", str(state)).upper()
    return "FAILED" in state_str


def _is_processing(state: Any) -> bool:
    """Check if the given state represents a PROCESSING file."""
    if state is None:
        return False
    state_str = getattr(state, "name", str(state)).upper()
    return "PROCESSING" in state_str


class GeminiFileService:
    """Service encapsulating multimodal file uploads and state verification."""

    def __init__(
        self,
        api_key: str | None = None,
        client: genai.Client | None = None,
    ) -> None:
        """Initialize the Gemini File Service.

        Args:
            api_key: Optional API key. If omitted, google-genai falls back to GEMINI_API_KEY env var.
            client: Optional pre-configured genai.Client (useful for testing or shared instances).
        """
        self._client = client or genai.Client(api_key=api_key)

    @property
    def client(self) -> genai.Client:
        """Return the underlying GenAI client."""
        return self._client

    async def _upload_raw(
        self,
        file_path: str | Path,
        mime_type: str | None = None,
        display_name: str | None = None,
    ) -> types.File:
        """Internal helper to dispatch file upload."""
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found at path: {file_path}")

        upload_kwargs: dict[str, Any] = {"file": str(path_obj)}
        config_kwargs: dict[str, Any] = {}
        if mime_type:
            config_kwargs["mime_type"] = mime_type
        if display_name:
            config_kwargs["display_name"] = display_name

        if config_kwargs:
            upload_kwargs["config"] = types.UploadFileConfig(**config_kwargs)

        # Support both async client.aio.files and sync client.files (via threadpool)
        if hasattr(self._client, "aio") and hasattr(self._client.aio, "files"):
            return await self._client.aio.files.upload(**upload_kwargs)
        return await asyncio.to_thread(self._client.files.upload, **upload_kwargs)

    async def _get_raw(self, name: str) -> types.File:
        """Internal helper to retrieve file metadata."""
        if hasattr(self._client, "aio") and hasattr(self._client.aio, "files"):
            return await self._client.aio.files.get(name=name)
        return await asyncio.to_thread(self._client.files.get, name=name)

    async def _delete_raw(self, name: str) -> None:
        """Internal helper to delete a remote file."""
        if hasattr(self._client, "aio") and hasattr(self._client.aio, "files"):
            await self._client.aio.files.delete(name=name)
        else:
            await asyncio.to_thread(self._client.files.delete, name=name)

    async def upload_and_wait_until_active(
        self,
        file_path: str | Path,
        mime_type: str | None = None,
        display_name: str | None = None,
        initial_poll_interval: float = 2.0,
        max_poll_interval: float = 10.0,
        poll_backoff_factor: float = 1.5,
        timeout_seconds: float = 180.0,
    ) -> types.File:
        """Upload a file to Gemini Files API and poll until it reaches the ACTIVE state.

        Args:
            file_path: Local path to the file to upload.
            mime_type: Optional MIME type for the file.
            display_name: Optional human-readable display name.
            initial_poll_interval: Starting delay between status polling checks (seconds).
            max_poll_interval: Maximum delay between status polling checks (seconds).
            poll_backoff_factor: Multiplier applied to polling delay on each iteration.
            timeout_seconds: Maximum total duration to wait before timing out.

        Returns:
            The ACTIVE types.File resource from Gemini.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            GeminiFileProcessingError: If the remote file processing fails.
            GeminiFileTimeoutError: If the file does not become ACTIVE before timeout.
        """
        logger.info("Uploading file to Gemini Files API: %s", file_path)
        file_resource = await self._upload_raw(
            file_path=file_path,
            mime_type=mime_type,
            display_name=display_name,
        )
        logger.info(
            "File uploaded successfully. Remote name: %s, initial state: %s",
            file_resource.name,
            getattr(file_resource, "state", None),
        )

        # If already ACTIVE (e.g., fast image/text uploads), return immediately
        if _is_active(getattr(file_resource, "state", None)):
            logger.info("File %s is already ACTIVE. Returning immediately.", file_resource.name)
            return file_resource

        # Polling loop
        elapsed: float = 0.0
        current_interval = initial_poll_interval

        while elapsed < timeout_seconds:
            logger.debug(
                "Sleeping %.1fs before checking status of %s (elapsed: %.1fs/%.1fs)",
                current_interval,
                file_resource.name,
                elapsed,
                timeout_seconds,
            )
            await asyncio.sleep(current_interval)
            elapsed += current_interval

            file_resource = await self._get_raw(name=file_resource.name)
            current_state = getattr(file_resource, "state", None)
            logger.info("File %s status check: %s", file_resource.name, current_state)

            if _is_active(current_state):
                logger.info("File %s reached ACTIVE state after %.1fs.", file_resource.name, elapsed)
                return file_resource

            if _is_failed(current_state):
                error_msg = f"Gemini file processing failed for '{file_resource.name}' with state: {current_state}"
                logger.error(error_msg)
                raise GeminiFileProcessingError(error_msg)

            # Exponential backoff clamped to max_poll_interval
            current_interval = min(current_interval * poll_backoff_factor, max_poll_interval)

        timeout_msg = (
            f"File '{file_resource.name}' did not reach ACTIVE state within "
            f"{timeout_seconds} seconds (last state: {getattr(file_resource, 'state', None)})."
        )
        logger.error(timeout_msg)
        raise GeminiFileTimeoutError(timeout_msg)

    async def delete_file(self, name: str) -> None:
        """Safely delete a remote file resource from Gemini.

        Args:
            name: Remote file name identifier (e.g. 'files/xyz123').
        """
        try:
            logger.info("Deleting remote Gemini file: %s", name)
            await self._delete_raw(name=name)
            logger.info("Successfully deleted remote Gemini file: %s", name)
        except Exception as exc:
            logger.warning("Failed to delete remote Gemini file %s: %s", name, exc)

    @contextlib.asynccontextmanager
    async def managed_file(
        self,
        file_path: str | Path,
        mime_type: str | None = None,
        display_name: str | None = None,
        timeout_seconds: float = 180.0,
    ) -> AsyncIterator[types.File]:
        """Async context manager that uploads, waits for ACTIVE, and deletes on exit."""
        file_resource = await self.upload_and_wait_until_active(
            file_path=file_path,
            mime_type=mime_type,
            display_name=display_name,
            timeout_seconds=timeout_seconds,
        )
        try:
            yield file_resource
        finally:
            await self.delete_file(name=file_resource.name)
