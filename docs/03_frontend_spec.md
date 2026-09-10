# Frontend Specification & Run Guide

**Project:** Multimodal Deep Researcher  
**Frontend Framework:** Streamlit (Python 3.12+)  
**Visualization Engine:** PyVis (Vis.js Interactive Physics Network)  
**Specification Status:** Active  

---

## 1. Architectural Philosophy

The **Multimodal Deep Researcher** frontend ([`src/frontend/app.py`](file:///c:/GIEREK/pythonPrograms/DeepResearcherAI/src/frontend/app.py)) is completely decoupled from model execution and file management. It acts as an interactive presentation client communicating with the FastAPI backend over HTTP (`multipart/form-data` uploads and JSON responses).

```
   ┌────────────────────────────────┐
   │       Streamlit Frontend       │
   │      (src/frontend/app.py)     │
   └───────────────┬────────────────┘
                   │ HTTP POST /api/analyze (multipart)
                   │ HTTP GET  /health
                   ▼
   ┌────────────────────────────────┐
   │         FastAPI Backend        │
   │       (src/backend/main.py)    │
   └───────────────┬────────────────┘
                   │
                   ▼
   ┌────────────────────────────────┐
   │      Gemini 3.6 Flash API      │
   │   (Files API + Polling Loop)   │
   └────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Main Application (`src/frontend/app.py`)
* **State Persistence:** Preserves `st.session_state["dashboard_data"]` and `st.session_state["analyzed_filename"]` so that user interactions (filtering flashcards, zooming graph) never trigger unexpected re-analysis or state loss.
* **Health Polling:** Queries `GET /health` to display live backend connectivity status ("🟢 Backend Connected" vs "🔴 Backend Offline").
* **Sidebar Controls:**
  * File uploader accepting `.pdf`, `.mp4`, `.mp3`, and `.txt`.
  * Optional custom research focus / prompt text area.
  * Primary trigger button: `🚀 Synthesize Research`.
  * Reset dashboard button: `🔄 Reset Dashboard`.
  * Connection settings expander to target custom backend hosts or ports.

### 2.2 Visualization Components (`src/frontend/components/visualizers.py`)

| Component | Function | Description |
| :--- | :--- | :--- |
| **Knowledge Graph** | `render_mind_map(nodes, edges)` | PyVis Force-Directed network graph embedded via `st.components.v1.html`. Nodes are colored by category and scaled by hierarchy importance (1–5). Edges describe relationships. Features zoom, pan, and physics stabilization. |
| **Active Recall Flashcards** | `render_flashcards(flashcards)` | Interactive cards with difficulty filters (`All`, `Easy`, `Medium`, `Hard`), topic badges, and expanders to reveal answers and exact source citations. |
| **Chronological Timeline** | `render_timeline(timeline_events)` | Vertical chronological milestone track with date badges, event summaries, domain significance callouts, and source pills. |

---

## 3. How to Run Locally (Concurrent Microservices)

To run the complete system, open two separate terminal windows in your IDE:

### Terminal 1: Start the FastAPI Backend
```bash
python -m uvicorn src.backend.main:app --reload --port 8000
```
* **API Server:** `http://localhost:8000`
* **Swagger Documentation:** `http://localhost:8000/docs`
* **Health Probe:** `http://localhost:8000/health`

### Terminal 2: Start the Streamlit Frontend
```bash
python -m streamlit run src/frontend/app.py
```
* **Web UI:** `http://localhost:8501`

---

## 4. End-to-End User Journey

1. Open `http://localhost:8501` in your browser.
2. Confirm the sidebar indicates **"🟢 Backend Connected"**.
3. Drag and drop a research document (`.pdf`), video lecture (`.mp4`), audio recording (`.mp3`), or text notes (`.txt`).
4. (Optional) Provide a research focus question in the **Research Focus** box.
5. Click **"🚀 Synthesize Research"**.
6. The frontend displays an animated spinner while the backend uploads the file to Gemini, safely polls until `ACTIVE`, and generates the structured schema.
7. Once complete, explore the synthesized results across the 4 tabs:
   * **Executive Summary:** High-level analytical takeaways and metric counters.
   * **Knowledge Graph (Mind Map):** Interactive physics network with zoomable nodes.
   * **Flashcards:** Test knowledge and reveal citations.
   * **Timeline & Milestones:** Chronological discovery progression.
