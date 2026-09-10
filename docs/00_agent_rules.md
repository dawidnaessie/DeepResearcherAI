# Agent Rules & Engineering Standards

**Project:** Multimodal Deep Researcher  
**Role:** Principal AI Architect & Lead Python Engineer  
**Status:** Active Operating Standard  

---

## 1. Purpose & Guiding Principles

This document sets the mandatory engineering standards, SDK constraints, code quality rules, and multimodal lifecycle requirements for all autonomous and human development across the **Multimodal Deep Researcher** codebase. Adherence is non-negotiable.

---

## 2. Library & SDK Standards

### 2.1 Mandatory `google-genai` SDK
* **Strict Prohibition:** The legacy `google-generativeai` package is **deprecated and strictly forbidden**. Under no circumstances should `google-generativeai` be installed, imported, or referenced in imports.
* **Modern Standard:** All Google Gemini interactions must strictly use the official unified **`google-genai`** SDK.
  ```python
  # CORRECT
  from google import genai
  from google.genai import types

  client = genai.Client(api_key=settings.GEMINI_API_KEY)
  ```
  ```python
  # FORBIDDEN (DO NOT USE)
  import google.generativeai as genai
  ```
* **Model References:** Target modern Gemini models (defaulting to `gemini-3.6-flash`, or `gemini-2.5-pro` where configured) using current SDK conventions.

---

## 3. Type Safety & Structured Outputs

### 3.1 Strict Pydantic Enforcement
* Gemini generation calls must enforce strict structured outputs using Pydantic models passed directly into `response_schema`.
* **Zero Parsing Ambiguity:** Unstructured, markdown-wrapped JSON or regex-extracted strings are strictly forbidden for API-driven workflows. All outputs must be validated at the boundary.
* **Configuration Syntax:**
  ```python
  from google.genai import types
  from src.backend.schemas.dashboard import ResearchDashboardPayload

  config = types.GenerateContentConfig(
      response_mime_type="application/json",
      response_schema=ResearchDashboardPayload,
      temperature=0.2,
  )

  response = await client.aio.models.generate_content(
      model="gemini-3.6-flash",
      contents=[uploaded_file, prompt_text],
      config=config,
  )

  # Validate directly via model
  dashboard_data = ResearchDashboardPayload.model_validate_json(response.text)
  ```

---

## 4. Code Quality & Architectural Modularity

### 4.1 Python 3.12+ Standards
* Modern type hinting is required throughout:
  * Use `X | None` instead of `Optional[X]`.
  * Use builtin collections (`list[str]`, `dict[str, Any]`, `set[int]`) instead of importing from `typing`.
  * Leverage `typing.Self` and `typing.Annotated` where appropriate.
* All functions, class methods, and API route handlers must include explicit input types and return annotations.

### 4.2 Absolute Modularity & Decoupling
* **Backend (`src/backend`):**
  * Built exclusively as a stateless, asynchronous FastAPI application.
  * Encapsulates all domain services, Gemini SDK interactions, file handling, and Pydantic validation.
  * Never imports frontend code or UI dependencies.
* **Frontend (`src/frontend`):**
  * Dedicated presentation layer (e.g., Streamlit).
  * Strictly decoupled: performs zero direct calls to the `google-genai` SDK or backend database.
  * Consumes backend capabilities solely through HTTP/REST endpoints using standard async or sync HTTP clients (`httpx`).
  * If the backend service is offline, the frontend must gracefully display connection diagnostics without crashing.

---

## 5. Multimodal Ingestion & Polling Lifecycle

Multimodal files (large PDFs, audio lectures, video recordings, high-res images) uploaded to the Gemini Files API undergo asynchronous ingestion and processing.

### 5.1 The `ACTIVE` State Polling Rule
1. **Upload:** Files must be registered with the Gemini Files API (`client.files.upload(...)`).
2. **State Verification:** Before passing any file URI/reference into `generate_content`, the system **must** enter an asynchronous polling loop checking `file.state`.
3. **Loop Conditions:**
   * Poll with exponential backoff (initial interval: 2 seconds, max interval: 10 seconds, timeout: 180 seconds).
   * Continue polling while `file.state == "PROCESSING"`.
   * Proceed to inference **only** when `file.state == "ACTIVE"`.
   * Terminate immediately with a specialized `GeminiFileProcessingError` if `file.state == "FAILED"`.
4. **Cleanup:** Register files for subsequent lifecycle tracking or explicit deletion via `client.files.delete(name=...)` once processing is completed to prevent resource leaks.

---

## 6. Error Handling, Logging, and Testing

* **Structured Logging:** Use standard Python `logging` with structured formats; log file upload IDs, Gemini latency, token consumption, and state transitions.
* **Secrets Management:** `GEMINI_API_KEY` must be loaded exclusively via environment variables (`pydantic-settings` or `.env`). Never commit keys or log them in plain text.
* **Testing:**
  * All unit and integration tests live in `tests/`.
  * External Gemini calls in unit tests must be mocked with deterministic Pydantic fixtures.
