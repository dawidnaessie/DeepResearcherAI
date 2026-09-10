"""FastAPI application for Multimodal Deep Researcher.

Provides endpoints for multimodal analysis orchestration, structured intelligence
extraction via Google Gemini, and service health monitoring.
"""

import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.config import settings
from src.backend.schemas.dashboard import ResearchStudyDashboard
from src.backend.services.file_service import (
    GeminiFileError,
    GeminiFileProcessingError,
    GeminiFileService,
    GeminiFileTimeoutError,
)
from src.backend.services.gemini_service import (
    GeminiAnalysisError,
    GeminiRateLimitError,
    generate_study_dashboard,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("deep_researcher.api")

app = FastAPI(
    title="Multimodal Deep Researcher API",
    description="Backend API synthesizing multimodal research into interactive mind maps, flashcards, and timelines.",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services (instantiated on demand or injected)
file_service = GeminiFileService(api_key=settings.GEMINI_API_KEY)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": "Multimodal Deep Researcher API",
        "version": "1.0.0",
    }


@app.post(
    "/api/analyze",
    response_model=ResearchStudyDashboard,
    status_code=status.HTTP_200_OK,
    tags=["Research Analysis"],
)
async def analyze_multimodal_document(
    file: Annotated[UploadFile, File(description="Multimodal file to analyze (PDF, MP4, MP3, PNG, etc.)")],
    prompt: Annotated[str | None, Form(description="Optional custom focus question or research prompt")] = None,
) -> ResearchStudyDashboard:
    """Analyze an uploaded multimodal document and synthesize a complete Research Study Dashboard.

    Workflow:
    1. Persists uploaded stream to a secure temporary local file.
    2. Dispatches file to Gemini Files API and asynchronously polls until state is ACTIVE.
    3. Triggers Gemini 2.5 Flash with strict Pydantic JSON schema enforcement.
    4. Cleans up temporary local and remote files.
    5. Returns validated ResearchStudyDashboard payload.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    # Determine file extension and MIME type
    suffix = Path(file.filename).suffix or ".tmp"
    mime_type = file.content_type or "application/octet-stream"
    temp_file_path: str | None = None
    remote_file_name: str | None = None

    try:
        # Step 1: Save uploaded stream to temporary local storage
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            temp_file_path = tmp_file.name
            logger.info("Streaming uploaded file '%s' to '%s'", file.filename, temp_file_path)
            shutil.copyfileobj(file.file, tmp_file)

        # Step 2: Upload to Gemini Files API and poll for ACTIVE state
        logger.info("Uploading '%s' to Gemini Files API...", file.filename)
        uploaded_resource = await file_service.upload_and_wait_until_active(
            file_path=temp_file_path,
            mime_type=mime_type,
            display_name=file.filename,
        )
        remote_file_name = uploaded_resource.name
        logger.info("Gemini file '%s' is verified ACTIVE.", remote_file_name)

        # Step 3: Call Gemini generation engine with structured schema
        logger.info("Initiating intelligence extraction via Gemini 2.5 Flash...")
        dashboard_result = await generate_study_dashboard(
            file_ref=uploaded_resource,
            mime_type=mime_type,
            user_prompt=prompt,
        )

        return dashboard_result

    except GeminiFileTimeoutError as exc:
        logger.error("File processing timeout: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Uploaded file timed out during processing: {exc}",
        ) from exc

    except GeminiFileProcessingError as exc:
        logger.error("File processing failed on Gemini server: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Remote Gemini file processing failed: {exc}",
        ) from exc

    except GeminiRateLimitError as exc:
        logger.error("Gemini rate limit exceeded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini rate limit exceeded. Please retry after a brief delay.",
        ) from exc

    except GeminiAnalysisError as exc:
        logger.error("Gemini analysis error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis generation failed: {exc}",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error during multimodal analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        ) from exc

    finally:
        # Step 4: Cleanup local buffer and remote Gemini file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug("Removed local temporary file '%s'", temp_file_path)
            except OSError as err:
                logger.warning("Failed to remove temporary file '%s': %s", temp_file_path, err)

        if remote_file_name:
            try:
                await file_service.delete_file(remote_file_name)
                logger.debug("Cleaned up remote Gemini file '%s'", remote_file_name)
            except Exception as err:
                logger.warning("Failed to delete remote file '%s': %s", remote_file_name, err)
