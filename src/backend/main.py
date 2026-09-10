"""FastAPI application for Multimodal Deep Researcher.

Provides endpoints for multimodal analysis orchestration, structured intelligence
extraction via Google Gemini, and service health monitoring.
"""

import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.config import settings
from src.backend.core.logger import logger
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

app = FastAPI(
    title="Multimodal Deep Researcher API",
    description="Backend API synthesizing multimodal research into interactive mind maps, flashcards, and timelines.",
    version="1.0.0",
)

# HTTP Request Logging Middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next) -> Response:
    """Intercept and log every incoming HTTP request and its execution latency."""
    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    logger.info(
        "Incoming HTTP request",
        method=method,
        path=path,
        client_ip=client_ip,
    )

    try:
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status_code = response.status_code

        logger.info(
            "HTTP request completed",
            method=method,
            path=path,
            client_ip=client_ip,
            status_code=status_code,
            duration_ms=process_time_ms,
        )
        return response
    except Exception as exc:
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            "HTTP request failed with unhandled exception",
            method=method,
            path=path,
            client_ip=client_ip,
            duration_ms=process_time_ms,
            error=str(exc),
        )
        raise exc

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

    if not settings.GEMINI_API_KEY and not os.environ.get("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY is not configured in .env or environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured. Please set a valid GEMINI_API_KEY in your .env file.",
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
            logger.info("Streaming uploaded file to temporary buffer", file_name=file.filename, temp_path=temp_file_path)
            shutil.copyfileobj(file.file, tmp_file)

        # Step 2: Upload to Gemini Files API and poll for ACTIVE state
        logger.info("Initiating Gemini Files API upload and active verification", file_name=file.filename)
        uploaded_resource = await file_service.upload_and_wait_until_active(
            file_path=temp_file_path,
            mime_type=mime_type,
            display_name=file.filename,
        )
        remote_file_name = uploaded_resource.name
        logger.info("Gemini file verified ACTIVE", remote_name=remote_file_name)

        # Step 3: Call Gemini generation engine with structured schema
        logger.info("Initiating intelligence extraction via Gemini model", model=settings.MODEL_NAME, remote_name=remote_file_name)
        dashboard_result = await generate_study_dashboard(
            file_ref=uploaded_resource,
            mime_type=mime_type,
            user_prompt=prompt,
            client=file_service.client,
            model=settings.MODEL_NAME,
        )

        return dashboard_result

    except GeminiFileTimeoutError as exc:
        logger.error("File processing timeout encountered", file_name=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Uploaded file timed out during processing: {exc}",
        ) from exc

    except GeminiFileProcessingError as exc:
        logger.error("Gemini server file processing failure", file_name=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Remote Gemini file processing failed: {exc}",
        ) from exc

    except GeminiRateLimitError as exc:
        logger.error("Gemini rate limit exceeded", file_name=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini rate limit exceeded. Please retry after a brief delay.",
        ) from exc

    except GeminiAnalysisError as exc:
        logger.error("Gemini analysis generation failure", file_name=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis generation failed: {exc}",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error during multimodal analysis", file_name=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        ) from exc

    finally:
        # Step 4: Cleanup local buffer and remote Gemini file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug("Removed local temporary file", temp_path=temp_file_path)
            except OSError as err:
                logger.warning("Failed to remove temporary file", temp_path=temp_file_path, error=str(err))

        if remote_file_name:
            try:
                await file_service.delete_file(remote_file_name)
                logger.debug("Cleaned up remote Gemini file", remote_name=remote_file_name)
            except Exception as err:
                logger.warning("Failed to delete remote file", remote_name=remote_file_name, error=str(err))
