# Logging & Observability Specification

**Project:** Multimodal Deep Researcher  
**Subsystem:** Telemetry, Structured Logging & Error Diagnosis  
**Technology:** Loguru (Structured JSON + Colored Console + Rotating Diagnostic Sinks)  
**Status:** Active  

---

## 1. Observability Architecture

The **Multimodal Deep Researcher** telemetry subsystem ([`src/backend/core/logger.py`](file:///c:/GIEREK/pythonPrograms/DeepResearcherAI/src/backend/core/logger.py)) provides production-grade observability across the entire multimodal lifecycle. It captures HTTP requests, streaming file uploads, remote Gemini Files API asynchronous polling intervals, LLM inference latency, and application exceptions.

```
                  ┌──────────────────────────────────────────┐
                  │          FastAPI HTTP Requests           │
                  └─────────────────────┬────────────────────┘
                                        │
                                        ▼
                  ┌──────────────────────────────────────────┐
                  │    Loguru Centralized Logging Engine     │
                  │        (src/backend/core/logger.py)      │
                  └─────┬──────────────────┬─────────────────┘
                        │                  │
        ┌───────────────┴────────┐         │
        ▼                        ▼         ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│    sys.stdout    │ │   logs/app.log   │ │  logs/error.log  │
│  (Color Console) │ │ (JSONL Telemetry)│ │(Diagnostic Stacks)
│   INFO & Above   │ │   INFO & Above   │ │  ERROR & Above   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 2. Log Sinks & Rotation Policy

| Sink Destination | Severity | Format | Rotation & Retention | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`sys.stdout`** | `INFO`+ | Colorized, human-readable console format | Active process stream | Local terminal visibility and live developer feedback. |
| **`logs/app.log`** | `INFO`+ | Single-line structured JSON (JSONL) | 10 MB per file, 7-day retention, ZIP compressed | Machine-parsable operational metrics and audit trail. |
| **`logs/error.log`** | `ERROR`+ | Full diagnostic traceback (`backtrace=True`, `diagnose=True`) | 10 MB per file, 7-day retention, ZIP compressed | Deep root-cause triage with local variable frame inspection. |

---

## 3. Structured JSON Schema (`logs/app.log`)

Every record written to `logs/app.log` conforms to the following schema:

```json
{
  "timestamp": "2026-09-10T23:42:30.123456Z",
  "level": "INFO",
  "module": "main",
  "function": "log_requests_middleware",
  "message": "HTTP request completed",
  "extra": {
    "method": "POST",
    "path": "/api/analyze",
    "client_ip": "127.0.0.1",
    "status_code": 200,
    "duration_ms": 4820.35
  }
}
```

### Core Schema Attributes

* `timestamp` *(string)*: ISO-8601 UTC timestamp with microsecond precision.
* `level` *(string)*: Log level (`INFO`, `WARNING`, `ERROR`, `CRITICAL`).
* `module` *(string)*: Source module emitting the event (e.g. `main`, `file_service`, `gemini_service`).
* `function` *(string)*: Function or coroutine name.
* `message` *(string)*: Human-readable event description.
* `extra` *(object)*: Dynamic key-value payload containing contextual domain metrics.

---

## 4. Instrumentation Points Across the Pipeline

### 4.1 FastAPI HTTP Middleware (`src/backend/main.py`)
Intercepts every HTTP transaction:
* **Request Start:** Logs incoming method, path, and client IP.
* **Request Completion:** Measures execution time with `time.perf_counter()` and logs status code and duration in milliseconds (`duration_ms`).
* **Unhandled Exceptions:** Logs 500-level failures with execution duration and error details.

### 4.2 File Management Service (`src/backend/services/file_service.py`)
Tracks the asynchronous lifecycle of multimodal uploads:
* **Upload Dispatch:** Emits `file_name`, `file_size_mb`, `mime_type`, and local file path.
* **Upload Completion:** Emits `remote_name`, `initial_state`, and `upload_duration_ms`.
* **State Polling:** On every polling iteration, emits `iteration`, `poll_interval_seconds`, `elapsed_seconds`, and remote `current_state` until `ACTIVE`.
* **Resource Cleanup:** Logs deletion of temporary local buffers and remote Gemini files.

### 4.3 Gemini Analysis Engine (`src/backend/services/gemini_service.py`)
Monitors intelligence extraction:
* **Prompt Dispatch:** Logs model identifier (`gemini-2.5-flash`), file identifier, prompt preview, and whether custom focus queries were provided.
* **Inference Latency:** Measures and records round-trip inference response time (`latency_ms`) and returned character length.
* **Rate Limit Retries (HTTP 429):** Logs warning on 429 responses with current attempt count, backoff duration, and latency.
* **Schema Validation:** Logs node count, edge count, flashcard count, and timeline milestone count upon Pydantic model validation.

---

## 5. Triage Guide for Engineers and AI Agents

When an analysis fails, follow this triage procedure:

### Step 1: Check `logs/error.log` for Root Cause
Run the following command in PowerShell:
```powershell
Get-Content logs/error.log -Tail 30
```
Or in Bash:
```bash
tail -n 50 logs/error.log
```

Because `logs/error.log` is configured with `backtrace=True` and `diagnose=True`, it includes full frame variable inspections showing the exact parameters passed when the exception occurred.

### Step 2: Correlate with `logs/app.log`
Locate the corresponding transaction by searching for the request path or file name:
```bash
# Search for failed HTTP requests
grep '"level": "ERROR"' logs/app.log
```

### Common Failure Scenarios & Resolutions

| Error in Log | Cause | Resolution |
| :--- | :--- | :--- |
| `GeminiRateLimitError` (HTTP 429) | Project quota or Queries Per Minute (QPM) exceeded after 4 backoff attempts. | Wait 60 seconds before retrying, or increase `max_retries` / `initial_backoff` in `src/backend/services/gemini_service.py`. |
| `GeminiFileTimeoutError` (HTTP 504) | Large video or dense PDF did not finish optical/acoustic processing within 180s. | Increase `POLL_TIMEOUT_SECONDS` in `.env` (e.g. `POLL_TIMEOUT_SECONDS=360`). |
| `GeminiFileProcessingError` (HTTP 422) | Video or audio file was corrupted or encoded with unsupported codecs. | Verify file integrity or transcode to standard MP4 (H.264/AAC) or MP3 before uploading. |
