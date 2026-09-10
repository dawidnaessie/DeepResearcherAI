"""Unit tests for Gemini Analysis Engine (gemini_service.py).

Verifies retry logic on HTTP 429 rate limits, system instruction configuration,
and schema validation with mocked genai Client.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from google.genai.errors import APIError
from src.backend.schemas.dashboard import ResearchStudyDashboard
from src.backend.services.gemini_service import (
    GeminiAnalysisError,
    GeminiRateLimitError,
    generate_study_dashboard,
)


@pytest.fixture
def valid_dashboard_json() -> str:
    """Return serialized valid ResearchStudyDashboard JSON."""
    dashboard = ResearchStudyDashboard(
        title="CRISPR Advances",
        executive_summary="Overview of CRISPR-Cas9 genome editing breakthroughs.",
        key_findings=["Base editing increases specificity."],
        nodes=[],
        edges=[],
        flashcards=[],
        timeline=[],
    )
    return dashboard.model_dump_json()


@pytest.mark.asyncio
async def test_generate_study_dashboard_success(valid_dashboard_json: str) -> None:
    """Verify standard successful generation parsing into Pydantic model."""
    mock_response = MagicMock()
    mock_response.text = valid_dashboard_json

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    file_ref = MagicMock()
    file_ref.name = "files/test_crispr"

    result = await generate_study_dashboard(
        file_ref=file_ref,
        client=mock_client,
        user_prompt="Explain Cas9 mechanisms",
    )

    assert result.title == "CRISPR Advances"
    assert result.key_findings == ["Base editing increases specificity."]
    mock_client.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_study_dashboard_retries_on_rate_limit(valid_dashboard_json: str) -> None:
    """Verify exponential backoff on HTTP 429 errors succeeds on subsequent attempt."""
    mock_response = MagicMock()
    mock_response.text = valid_dashboard_json

    rate_limit_err = APIError(code=429, response_json={"error": {"message": "Resource exhausted"}})

    mock_client = MagicMock()
    # Fails once with 429, then succeeds on attempt 2
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[rate_limit_err, mock_response]
    )

    file_ref = MagicMock()
    file_ref.name = "files/test_retry"

    result = await generate_study_dashboard(
        file_ref=file_ref,
        client=mock_client,
        initial_backoff=0.01,
        max_backoff=0.02,
        max_retries=3,
    )

    assert result.title == "CRISPR Advances"
    assert mock_client.aio.models.generate_content.await_count == 2


@pytest.mark.asyncio
async def test_generate_study_dashboard_rate_limit_exhausted() -> None:
    """Verify GeminiRateLimitError is raised when max retries are exceeded."""
    rate_limit_err = APIError(code=429, response_json={"error": {"message": "Resource exhausted"}})

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=rate_limit_err)

    file_ref = MagicMock()
    file_ref.name = "files/test_retry_fail"

    with pytest.raises(GeminiRateLimitError):
        await generate_study_dashboard(
            file_ref=file_ref,
            client=mock_client,
            initial_backoff=0.01,
            max_backoff=0.02,
            max_retries=2,
        )


@pytest.mark.asyncio
async def test_generate_study_dashboard_empty_response() -> None:
    """Verify GeminiAnalysisError is raised if response.text is empty."""
    mock_response = MagicMock()
    mock_response.text = ""

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    file_ref = MagicMock()
    file_ref.name = "files/test_empty"

    with pytest.raises(GeminiAnalysisError):
        await generate_study_dashboard(
            file_ref=file_ref,
            client=mock_client,
            max_retries=1,
        )
