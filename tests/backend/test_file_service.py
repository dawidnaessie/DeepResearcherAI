"""Unit tests for GeminiFileService.

Validates upload dispatch, polling loop behavior, ACTIVE transition,
FAILED state exception handling, and timeout behavior using mock GenAI clients.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.backend.services.file_service import (
    GeminiFileProcessingError,
    GeminiFileService,
    GeminiFileTimeoutError,
)


@pytest.fixture
def temp_sample_file(tmp_path: Path) -> Path:
    """Create a temporary sample file for upload tests."""
    file = tmp_path / "sample_paper.pdf"
    file.write_text("Dummy academic paper content")
    return file


@pytest.mark.asyncio
async def test_upload_file_not_found() -> None:
    """Verify FileNotFoundError is raised if target path does not exist."""
    service = GeminiFileService(client=MagicMock())
    with pytest.raises(FileNotFoundError):
        await service.upload_and_wait_until_active("non_existent_file.pdf")


@pytest.mark.asyncio
async def test_upload_already_active(temp_sample_file: Path) -> None:
    """Verify immediate return if uploaded file is already in ACTIVE state."""
    mock_file = MagicMock()
    mock_file.name = "files/instant_123"
    mock_file.state = "ACTIVE"

    mock_client = MagicMock()
    mock_client.aio.files.upload = AsyncMock(return_value=mock_file)

    service = GeminiFileService(client=mock_client)
    result = await service.upload_and_wait_until_active(temp_sample_file)

    assert result.name == "files/instant_123"
    mock_client.aio.files.upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_polling_transitions_to_active(temp_sample_file: Path) -> None:
    """Verify polling loop queries until file transitions from PROCESSING to ACTIVE."""
    file_processing = MagicMock()
    file_processing.name = "files/async_123"
    file_processing.state = "PROCESSING"

    file_active = MagicMock()
    file_active.name = "files/async_123"
    file_active.state = "ACTIVE"

    mock_client = MagicMock()
    mock_client.aio.files.upload = AsyncMock(return_value=file_processing)
    # First get returns PROCESSING, second get returns ACTIVE
    mock_client.aio.files.get = AsyncMock(side_effect=[file_processing, file_active])

    service = GeminiFileService(client=mock_client)
    result = await service.upload_and_wait_until_active(
        temp_sample_file,
        initial_poll_interval=0.01,
        max_poll_interval=0.02,
        timeout_seconds=2.0,
    )

    assert result.state == "ACTIVE"
    assert mock_client.aio.files.get.await_count == 2


@pytest.mark.asyncio
async def test_upload_polling_handles_failed_state(temp_sample_file: Path) -> None:
    """Verify GeminiFileProcessingError is raised if file enters FAILED state."""
    file_processing = MagicMock()
    file_processing.name = "files/corrupt_123"
    file_processing.state = "PROCESSING"

    file_failed = MagicMock()
    file_failed.name = "files/corrupt_123"
    file_failed.state = "FAILED"

    mock_client = MagicMock()
    mock_client.aio.files.upload = AsyncMock(return_value=file_processing)
    mock_client.aio.files.get = AsyncMock(return_value=file_failed)

    service = GeminiFileService(client=mock_client)
    with pytest.raises(GeminiFileProcessingError):
        await service.upload_and_wait_until_active(
            temp_sample_file,
            initial_poll_interval=0.01,
            timeout_seconds=2.0,
        )


@pytest.mark.asyncio
async def test_upload_polling_timeout(temp_sample_file: Path) -> None:
    """Verify GeminiFileTimeoutError is raised if file stays in PROCESSING past timeout."""
    file_processing = MagicMock()
    file_processing.name = "files/slow_123"
    file_processing.state = "PROCESSING"

    mock_client = MagicMock()
    mock_client.aio.files.upload = AsyncMock(return_value=file_processing)
    mock_client.aio.files.get = AsyncMock(return_value=file_processing)

    service = GeminiFileService(client=mock_client)
    with pytest.raises(GeminiFileTimeoutError):
        await service.upload_and_wait_until_active(
            temp_sample_file,
            initial_poll_interval=0.01,
            max_poll_interval=0.02,
            timeout_seconds=0.05,
        )


@pytest.mark.asyncio
async def test_delete_file() -> None:
    """Verify delete file invokes client.aio.files.delete."""
    mock_client = MagicMock()
    mock_client.aio.files.delete = AsyncMock()

    service = GeminiFileService(client=mock_client)
    await service.delete_file("files/test_to_delete")
    mock_client.aio.files.delete.assert_awaited_once_with(name="files/test_to_delete")
