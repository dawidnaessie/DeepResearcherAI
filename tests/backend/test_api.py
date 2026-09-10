"""Integration tests for FastAPI endpoints in src/backend/main.py.

Uses FastAPI TestClient and mocks out remote Gemini service calls.
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import pytest

from src.backend.main import app
from src.backend.schemas.dashboard import (
    Flashcard,
    MindMapEdge,
    MindMapNode,
    ResearchStudyDashboard,
    TimelineEvent,
)
from src.backend.services.file_service import (
    GeminiFileProcessingError,
    GeminiFileTimeoutError,
)
from src.backend.services.gemini_service import (
    GeminiRateLimitError,
)

client = TestClient(app)


@pytest.fixture
def mock_dashboard_payload() -> ResearchStudyDashboard:
    """Fixture providing a complete validated ResearchStudyDashboard."""
    return ResearchStudyDashboard(
        title="Neuromorphic Computing Architectures",
        executive_summary="Exploration of spiking neural networks on memristive crossbar arrays.",
        key_findings=[
            "100x energy efficiency improvement over conventional Von Neumann hardware.",
            "Spike-timing-dependent plasticity enabled on-chip unsupervised learning.",
        ],
        nodes=[
            MindMapNode(
                id="n1",
                label="Memristor",
                description="Non-volatile memory resistor device mimicking synaptic plasticity.",
                category="hardware",
                importance=5,
            ),
            MindMapNode(
                id="n2",
                label="Spiking Neural Network",
                description="Bio-inspired neural network processing temporal event spikes.",
                category="architecture",
                importance=4,
            ),
        ],
        edges=[
            MindMapEdge(
                source="n1",
                target="n2",
                relationship="physically implements synapses for",
            )
        ],
        flashcards=[
            Flashcard(
                id="fc1",
                question="What physical property enables memristor resistance switching?",
                answer="Oxygen vacancy migration and conductive filament formation.",
                difficulty="medium",
                topic="Device Physics",
                source_reference="Section 2.1, Page 4",
            )
        ],
        timeline=[
            TimelineEvent(
                id="te1",
                date_or_period="1971",
                title="Memristor Theorized",
                summary="Leon Chua mathematically formulates the fourth passive circuit element.",
                significance="Foundational theory enabling modern neuromorphic hardware.",
                sources=["IEEE Transactions on Circuit Theory"],
            )
        ],
    )


def test_health_check_endpoint() -> None:
    """Verify GET /health returns 200 and valid status payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


def test_analyze_endpoint_success(mock_dashboard_payload: ResearchStudyDashboard) -> None:
    """Verify POST /api/analyze uploads file, runs generation, cleans up, and returns 200."""
    mock_file_resource = AsyncMock()
    mock_file_resource.name = "files/mock_upload_999"

    with patch(
        "src.backend.main.file_service.upload_and_wait_until_active",
        new=AsyncMock(return_value=mock_file_resource),
    ) as mock_upload, patch(
        "src.backend.main.generate_study_dashboard",
        new=AsyncMock(return_value=mock_dashboard_payload),
    ) as mock_generate, patch(
        "src.backend.main.file_service.delete_file",
        new=AsyncMock(),
    ) as mock_delete:
        test_content = b"%PDF-1.4 Mock PDF binary data for research paper"
        files = {
            "file": ("neuromorphic_study.pdf", test_content, "application/pdf")
        }
        data = {"prompt": "Focus on memristive crossbars"}

        response = client.post("/api/analyze", files=files, data=data)

        assert response.status_code == 200
        payload = response.json()

        assert payload["title"] == "Neuromorphic Computing Architectures"
        assert len(payload["nodes"]) == 2
        assert payload["nodes"][0]["label"] == "Memristor"
        assert len(payload["edges"]) == 1
        assert len(payload["flashcards"]) == 1
        assert len(payload["timeline"]) == 1

        mock_upload.assert_awaited_once()
        mock_generate.assert_awaited_once()
        mock_delete.assert_awaited_once_with("files/mock_upload_999")


def test_analyze_endpoint_gemini_timeout() -> None:
    """Verify POST /api/analyze returns 504 when file upload times out."""
    with patch(
        "src.backend.main.file_service.upload_and_wait_until_active",
        side_effect=GeminiFileTimeoutError("File timed out after 180s"),
    ):
        files = {
            "file": ("large_video.mp4", b"video data", "video/mp4")
        }
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]


def test_analyze_endpoint_file_processing_error() -> None:
    """Verify POST /api/analyze returns 422 when remote Gemini file state is FAILED."""
    with patch(
        "src.backend.main.file_service.upload_and_wait_until_active",
        side_effect=GeminiFileProcessingError("File encoding corrupted"),
    ):
        files = {
            "file": ("corrupt.mp3", b"bad audio", "audio/mp3")
        }
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 422
        assert "processing failed" in response.json()["detail"].lower()


def test_analyze_endpoint_rate_limit() -> None:
    """Verify POST /api/analyze returns 429 when Gemini quota/rate limits are exceeded."""
    mock_file_resource = AsyncMock()
    mock_file_resource.name = "files/test_rate_limit"

    with patch(
        "src.backend.main.file_service.upload_and_wait_until_active",
        new=AsyncMock(return_value=mock_file_resource),
    ), patch(
        "src.backend.main.generate_study_dashboard",
        side_effect=GeminiRateLimitError("Quota limit hit"),
    ), patch(
        "src.backend.main.file_service.delete_file",
        new=AsyncMock(),
    ):
        files = {
            "file": ("paper.pdf", b"data", "application/pdf")
        }
        response = client.post("/api/analyze", files=files)
        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()
