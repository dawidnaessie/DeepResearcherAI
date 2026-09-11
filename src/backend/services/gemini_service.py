"""Gemini Analysis Engine Service.

Orchestrates structured intelligence extraction using Google Gemini 3.6 Flash
and enforces strict Pydantic JSON schemas for the Research Study Dashboard.
"""

import asyncio
import time
from typing import Any

from google import genai
from google.genai import errors, types

from src.backend.config import settings
from src.backend.core.logger import logger
from src.backend.schemas.dashboard import ResearchStudyDashboard

SYSTEM_PROMPT = """You are a Principal Academic Research Synthesizer and Knowledge Architect.
Your mission is to perform deep, rigorous multimodal analysis of the provided material and synthesize it into a comprehensive, structured research study dashboard.

Analyze the uploaded material with academic precision and adhere to the following directives:

1. Structured Executive Summary & Key Findings:
   - executive_summary:
     * overview: Provide an incisive narrative overview synthesizing core theses, breakthroughs, background, and essential subject matter.
     * core_objectives: List explicit scientific, technical, or research objectives addressed by the material.
     * methodology: Detail the theoretical frameworks, experimental methods, algorithmic designs, benchmarks, or analytical models utilized.
     * primary_conclusions: Extract concrete validated conclusions, major breakthroughs, practical implications, and open challenges.
   - key_findings: Extract high-impact, specific key findings, emphasizing quantitative metrics and experimental data where present.

2. Conceptual Mind Map:
   - Identify fundamental core themes, theoretical frameworks, methodologies, and specific discoveries.
   - Assign importance from 1 (peripheral/leaf details) to 5 (central core concept).
   - Construct rich, directed edges between concepts with explicit, explanatory relational descriptions (e.g., 'empirically validates', 'mechanistically causes', 'theoretically contradicts', 'derives from').
   - Ensure the mind map forms a well-connected, coherent semantic knowledge graph.

3. Active-Recall Flashcards:
   - Craft challenging, probing questions that test conceptual mastery, causal reasoning, mechanisms, and edge cases rather than superficial memorization.
   - Provide comprehensive, scientifically accurate answers grounded strictly in the source material.
   - Assign realistic difficulty levels ('easy', 'medium', 'hard'), tag with topic domains, and cite specific sections, page numbers, or timestamps where available.

4. Chronological & Phase Timeline:
   - Extract key chronological milestones, historical developments, experimental phases, or sequential breakthrough stages documented in the content.
   - Detail dates or temporal periods, descriptive titles, thorough summaries of what transpired, and their significance to the subject matter.
"""


class GeminiAnalysisError(Exception):
    """Base exception for Gemini analysis errors."""


class GeminiRateLimitError(GeminiAnalysisError):
    """Raised when Gemini API rate limit (HTTP 429) retries are exhausted."""


def _is_rate_limit_error(exc: Exception) -> bool:
    """Detect if an exception is an HTTP 429 rate limit or quota exhaustion."""
    if isinstance(exc, errors.APIError) and exc.code == 429:
        return True
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code == 429:
        return True
    exc_str = str(exc).upper()
    return "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str or "RATE LIMIT" in exc_str


async def generate_study_dashboard(
    file_ref: Any,
    mime_type: str = "application/pdf",
    client: genai.Client | None = None,
    user_prompt: str | None = None,
    model: str | None = None,
    max_retries: int = 4,
    initial_backoff: float = 2.0,
    backoff_factor: float = 2.0,
    max_backoff: float = 30.0,
) -> ResearchStudyDashboard:
    """Generate a structured ResearchStudyDashboard from an uploaded file reference.

    Args:
        file_ref: types.File object, file URI, or content reference accepted by google-genai.
        mime_type: MIME type of the uploaded file.
        client: Optional genai.Client instance. If omitted, initializes default client.
        user_prompt: Optional custom research instructions or focus topics from the user.
        model: Target Gemini model identifier (defaults to settings.MODEL_NAME, e.g. 'gemini-3.6-flash').
        max_retries: Maximum retry attempts on HTTP 429 rate limits.
        initial_backoff: Initial wait time in seconds before retrying after a 429.
        backoff_factor: Multiplier applied to wait time on consecutive 429 responses.
        max_backoff: Maximum backoff ceiling in seconds.

    Returns:
        Validated ResearchStudyDashboard instance matching the Pydantic schema.

    Raises:
        GeminiRateLimitError: If rate limit retries are exhausted.
        GeminiAnalysisError: If inference fails or returns invalid structure.
    """
    target_model = model or settings.MODEL_NAME

    if client is not None:
        genai_client = client
    elif settings.GEMINI_API_KEY:
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    else:
        genai_client = genai.Client()

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ResearchStudyDashboard,
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
    )

    contents: list[Any] = [file_ref]
    prompt_summary = user_prompt if user_prompt else "Default comprehensive study dashboard prompt"
    if user_prompt:
        contents.append(f"Research focus & specific user queries:\n{user_prompt}")
    else:
        contents.append("Synthesize this document thoroughly into the complete Research Study Dashboard.")

    file_identifier = getattr(file_ref, "name", str(file_ref))
    logger.info(
        "Dispatching Gemini inference request",
        model=target_model,
        file_ref=file_identifier,
        prompt_preview=prompt_summary[:120],
        has_custom_prompt=bool(user_prompt),
    )

    delay = initial_backoff
    for attempt in range(1, max_retries + 1):
        dispatch_start = time.perf_counter()
        try:
            logger.info(
                "Calling Gemini generation endpoint",
                model=target_model,
                attempt=attempt,
                max_retries=max_retries,
            )

            # Support both async client.aio.models and synchronous client.models
            if hasattr(genai_client, "aio") and hasattr(genai_client.aio, "models"):
                response = await genai_client.aio.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                )
            else:
                response = await asyncio.to_thread(
                    genai_client.models.generate_content,
                    model=target_model,
                    contents=contents,
                    config=config,
                )

            latency_ms = round((time.perf_counter() - dispatch_start) * 1000, 2)
            logger.info(
                "Received Gemini inference response",
                model=target_model,
                attempt=attempt,
                latency_ms=latency_ms,
                response_chars=len(response.text) if response.text else 0,
            )

            if not response.text:
                raise GeminiAnalysisError("Gemini returned empty response text.")

            # Validate against Pydantic schema
            dashboard = ResearchStudyDashboard.model_validate_json(response.text)
            logger.info(
                "Successfully validated ResearchStudyDashboard",
                title=dashboard.title,
                nodes_count=len(dashboard.nodes),
                flashcards_count=len(dashboard.flashcards),
                timeline_count=len(dashboard.timeline),
                total_latency_ms=latency_ms,
            )
            return dashboard

        except Exception as exc:
            latency_ms = round((time.perf_counter() - dispatch_start) * 1000, 2)
            if _is_rate_limit_error(exc):
                if attempt < max_retries:
                    logger.warning(
                        "Gemini rate limit (429) hit, retrying with exponential backoff",
                        model=target_model,
                        attempt=attempt,
                        max_retries=max_retries,
                        backoff_seconds=delay,
                        latency_ms=latency_ms,
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_backoff)
                    continue
                logger.error(
                    "Gemini rate limit retries exhausted",
                    model=target_model,
                    attempts_made=max_retries,
                    error=str(exc),
                )
                raise GeminiRateLimitError(
                    f"Gemini API rate limit exceeded after {max_retries} retries."
                ) from exc

            logger.error(
                "Gemini dashboard generation error",
                model=target_model,
                attempt=attempt,
                latency_ms=latency_ms,
                error=str(exc),
            )
            raise GeminiAnalysisError(f"Gemini generation failed: {exc}") from exc

    raise GeminiAnalysisError("Unexpected termination of generation retry loop.")
