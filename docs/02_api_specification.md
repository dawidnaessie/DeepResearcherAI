# API Specification & Integration Guide

**Project:** Multimodal Deep Researcher  
**API Version:** 1.0.0  
**Backend Port:** `http://localhost:8000` (Default)  
**Specification Status:** Active  

---

## 1. Overview

The **Multimodal Deep Researcher API** exposes asynchronous endpoints for health monitoring and multimodal research analysis. The backend orchestrates file uploads to the Google Gemini Files API, safely polls for the `ACTIVE` processing state, extracts structured intelligence via `gemini-3.6-flash`, and returns a strongly validated Pydantic payload (`ResearchStudyDashboard`).

---

## 2. Supported Multimodal Formats & MIME Types

The `/api/analyze` endpoint accepts standard multipart file uploads. The backend and Gemini ingestion engine support the following formats:

| Category | File Extensions | MIME Types |
| :--- | :--- | :--- |
| **Documents** | `.pdf`, `.txt`, `.md`, `.csv` | `application/pdf`, `text/plain`, `text/markdown`, `text/csv` |
| **Audio** | `.mp3`, `.wav`, `.m4a`, `.aac` | `audio/mp3`, `audio/mpeg`, `audio/wav`, `audio/x-m4a` |
| **Video** | `.mp4`, `.mov`, `.webm`, `.avi` | `video/mp4`, `video/quicktime`, `video/webm` |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.webp` | `image/png`, `image/jpeg`, `image/webp` |

---

## 3. Endpoints

### 3.1 Health Check

Verifies that the FastAPI backend service is running and responsive.

* **Method:** `GET`
* **Route:** `/health`
* **Authentication:** None

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "Multimodal Deep Researcher API",
  "version": "1.0.0"
}
```

#### Curl Example
```bash
curl -X GET http://localhost:8000/health
```

---

### 3.2 Multimodal Research Analysis

Ingests an uploaded multimodal file, uploads it to the Gemini Files API, monitors the polling loop until the file reaches `ACTIVE` status, and invokes `gemini-3.6-flash` with structured Pydantic schema validation.

* **Method:** `POST`
* **Route:** `/api/analyze`
* **Content-Type:** `multipart/form-data`
* **Authentication:** Required via server-side `GEMINI_API_KEY`

#### Request Parameters (Form-Data)

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | `binary` | **Yes** | Multimodal file stream (PDF, audio, video, image). |
| `prompt` | `string` | No | Optional focus query or specific extraction instructions. |

#### HTTP Status Codes

| Code | Status | Description |
| :--- | :--- | :--- |
| `200` | `OK` | Multimodal analysis synthesized successfully. |
| `400` | `Bad Request` | Missing file or invalid filename. |
| `422` | `Unprocessable Content` | Remote Gemini file processing entered `FAILED` state. |
| `429` | `Too Many Requests` | Gemini quota or rate limits exceeded after backoff attempts. |
| `500` | `Internal Server Error` | Model inference failure or unhandled internal error. |
| `504` | `Gateway Timeout` | Uploaded file did not reach `ACTIVE` state within the timeout window. |

#### Response Schema (`ResearchStudyDashboard`)

```json
{
  "title": "Quantum Error Correction with Surface Codes",
  "executive_summary": "This research analyzes recent breakthroughs in superconducting qubit error suppression...",
  "key_findings": [
    "Below-threshold physical error rates achieved on a 72-qubit planar array.",
    "Real-time decoding latency reduced below 1 microsecond using FPGA accelerators."
  ],
  "nodes": [
    {
      "id": "node_surface_code",
      "label": "Planar Surface Code",
      "description": "2D topological quantum error-correcting code using stabilizer measurements.",
      "category": "core_concept",
      "importance": 5
    },
    {
      "id": "node_syndrome_extraction",
      "label": "Syndrome Extraction",
      "description": "Continuous non-destructive projective measurements of X and Z parity check operators.",
      "category": "methodology",
      "importance": 4
    }
  ],
  "edges": [
    {
      "source": "node_surface_code",
      "target": "node_syndrome_extraction",
      "relationship": "requires continuous execution of"
    }
  ],
  "flashcards": [
    {
      "id": "fc_1",
      "question": "What is the physical error threshold for the 2D surface code under depolarizing noise?",
      "answer": "Approximately 1% under standard phenomenological and circuit noise models.",
      "difficulty": "hard",
      "topic": "Quantum Information",
      "source_reference": "Section 4.1, Page 8"
    }
  ],
  "timeline": [
    {
      "id": "event_1",
      "date_or_period": "1998",
      "title": "Topological Quantum Memory Proposed",
      "summary": "Alexei Kitaev publishes the toric code framework establishing topological stability.",
      "significance": "Laid the mathematical groundwork for modern surface codes.",
      "sources": ["Annals of Physics 303, 2-30"]
    }
  ]
}
```

---

## 4. Testing with `curl`

### 4.1 Analyze a PDF Research Paper
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Accept: application/json" \
  -F "file=@./sample_paper.pdf;type=application/pdf" \
  -F "prompt=Focus on novel algorithms and quantitative benchmark comparisons."
```

### 4.2 Analyze an Audio Lecture (MP3)
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Accept: application/json" \
  -F "file=@./lecture_recording.mp3;type=audio/mp3" \
  -F "prompt=Extract all chronological milestone events discussed in this lecture."
```

### 4.3 Analyze a Video Recording (MP4)
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Accept: application/json" \
  -F "file=@./presentation.mp4;type=video/mp4"
```

---

## 5. Running the Backend Server Locally

To start the FastAPI development server with automatic reload:

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI documentation is available at:
* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`
