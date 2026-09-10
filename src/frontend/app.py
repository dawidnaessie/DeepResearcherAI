"""Streamlit interactive frontend for Multimodal Deep Researcher.

Communicates with the FastAPI backend (/api/analyze) via HTTP and renders
interactive Knowledge Graphs, active-recall Flashcards, Timelines, and Summaries.
"""

import os
from typing import Any
import requests
import streamlit as st

from src.frontend.components.visualizers import (
    render_flashcards,
    render_mind_map,
    render_timeline,
)

# Page Configuration
st.set_page_config(
    page_title="Multimodal Deep Researcher",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Default backend configuration
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize session state variables
if "dashboard_data" not in st.session_state:
    st.session_state["dashboard_data"] = None
if "analyzed_filename" not in st.session_state:
    st.session_state["analyzed_filename"] = None
if "backend_url" not in st.session_state:
    st.session_state["backend_url"] = DEFAULT_BACKEND_URL


def check_backend_health(url: str) -> bool:
    """Check whether the FastAPI backend is online and reachable."""
    try:
        resp = requests.get(f"{url}/health", timeout=2.0)
        return resp.status_code == 200 and resp.json().get("status") == "healthy"
    except Exception:
        return False


# --- Sidebar ---
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 16px;">
            <h2 style="margin: 0; color: #6366F1;">🔬 Deep Researcher</h2>
            <p style="color: #94A3B8; font-size: 0.85rem; margin: 4px 0 0 0;">Autonomous Multimodal Intelligence</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Backend Connectivity Indicator
    backend_online = check_backend_health(st.session_state["backend_url"])
    if backend_online:
        st.success("🟢 Backend Connected", icon="✅")
    else:
        st.warning(
            "🔴 Backend Offline\n\nStart backend via:\n`uvicorn src.backend.main:app --reload --port 8000`",
            icon="⚠️",
        )

    st.divider()

    st.markdown("### 📤 Upload Research Material")
    uploaded_file = st.file_uploader(
        "Choose a multimodal file",
        type=["pdf", "mp4", "mp3", "txt"],
        help="Upload an academic paper, audio lecture, video recording, or text notes.",
    )

    custom_prompt = st.text_area(
        "🎯 Research Focus (Optional)",
        placeholder="e.g. Focus on experimental methodologies, theoretical foundations, and numerical error thresholds...",
        help="Provide specific questions or focal themes to steer the synthesis.",
        height=100,
    )

    analyze_button = st.button(
        "🚀 Synthesize Research",
        type="primary",
        use_container_width=True,
        disabled=uploaded_file is None,
    )

    if st.session_state["dashboard_data"] is not None:
        if st.button("🔄 Reset Dashboard", use_container_width=True):
            st.session_state["dashboard_data"] = None
            st.session_state["analyzed_filename"] = None
            st.rerun()

    st.divider()

    with st.expander("⚙️ Connection Settings", expanded=False):
        new_url = st.text_input("Backend API URL", value=st.session_state["backend_url"])
        if new_url != st.session_state["backend_url"]:
            st.session_state["backend_url"] = new_url.rstrip("/")
            st.rerun()

    st.caption("Powered by Google Gemini 2.5 Flash & FastAPI")


# --- Analysis Trigger Logic ---
if analyze_button and uploaded_file is not None:
    backend_url = st.session_state["backend_url"]

    # Verify backend connectivity first
    if not check_backend_health(backend_url):
        st.error(
            f"❌ Unable to connect to backend at `{backend_url}`. "
            "Please ensure the FastAPI service is running: `uvicorn src.backend.main:app --port 8000`"
        )
    else:
        with st.spinner(
            f"🧠 Analyzing '{uploaded_file.name}' via Gemini 2.5 Flash...\n\n"
            "• Uploading to Gemini Files API\n"
            "• Polling file state until ACTIVE\n"
            "• Extracting Knowledge Graph, Flashcards & Timeline"
        ):
            try:
                # Prepare multipart/form-data payload
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream",
                    )
                }
                data = {"prompt": custom_prompt} if custom_prompt else {}

                response = requests.post(
                    f"{backend_url}/api/analyze",
                    files=files,
                    data=data,
                    timeout=300,  # 5-minute timeout for large videos/PDFs
                )

                if response.status_code == 200:
                    st.session_state["dashboard_data"] = response.json()
                    st.session_state["analyzed_filename"] = uploaded_file.name
                    st.toast("✅ Intelligence synthesis complete!", icon="🎉")
                    st.rerun()
                elif response.status_code == 429:
                    st.error("⏳ Rate limit reached on Gemini API. Please wait a minute and retry.")
                elif response.status_code == 504:
                    st.error("⏱️ Gateway Timeout: File processing took longer than expected on Gemini's servers.")
                else:
                    detail = response.json().get("detail", response.text)
                    st.error(f"❌ Analysis failed (HTTP {response.status_code}): {detail}")

            except requests.exceptions.ConnectionError:
                st.error(f"❌ Failed to reach backend at `{backend_url}`. Check server terminal.")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out after 300 seconds.")
            except Exception as exc:
                st.error(f"❌ Unexpected error occurred: {exc}")


# --- Main Dashboard Render ---
dashboard: dict[str, Any] | None = st.session_state.get("dashboard_data")

if dashboard is not None:
    title = dashboard.get("title", "Research Study Synthesis")
    source_name = st.session_state.get("analyzed_filename", "Uploaded Material")

    # Header section
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%); padding: 24px; border-radius: 12px; border: 1px solid #3730A3; margin-bottom: 24px;">
            <span style="background: #4F46E5; color: #FFFFFF; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; text-transform: uppercase;">Synthesized Study</span>
            <h1 style="margin: 8px 0 6px 0; color: #F8FAFC; font-size: 2.1rem;">{title}</h1>
            <p style="margin: 0; color: #94A3B8; font-size: 0.95rem;">📄 Source: <b>{source_name}</b> &nbsp;|&nbsp; 🤖 Engine: <b>Gemini 2.5 Flash</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tabs navigation
    tab_summary, tab_mindmap, tab_flashcards, tab_timeline = st.tabs(
        [
            "📑 Executive Summary",
            "🧠 Knowledge Graph (Mind Map)",
            "🗂️ Flashcards",
            "⏳ Timeline & Milestones",
        ]
    )

    # --- Tab 1: Executive Summary ---
    with tab_summary:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### 📝 Executive Summary")
            st.markdown(dashboard.get("executive_summary", "No executive summary provided."))

        with col2:
            st.markdown("### 🎯 Key Findings & Insights")
            findings = dashboard.get("key_findings", [])
            if findings:
                for idx, finding in enumerate(findings, start=1):
                    st.markdown(
                        f"""
                        <div style="background: #1E293B; border-left: 4px solid #10B981; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px; font-size: 0.95rem; color: #F1F5F9;">
                            <b>{idx}.</b> {finding}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No explicit key findings extracted.")

            # Quick stats container
            st.markdown("### 📊 Metrics")
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Concepts", len(dashboard.get("nodes", [])))
                st.metric("Flashcards", len(dashboard.get("flashcards", [])))
            with m2:
                st.metric("Connections", len(dashboard.get("edges", [])))
                st.metric("Milestones", len(dashboard.get("timeline", [])))

    # --- Tab 2: Knowledge Graph (Mind Map) ---
    with tab_mindmap:
        nodes = dashboard.get("nodes", [])
        edges = dashboard.get("edges", [])

        st.markdown(
            f"### 🧠 Conceptual Knowledge Graph ({len(nodes)} concepts, {len(edges)} connections)"
        )
        render_mind_map(nodes=nodes, edges=edges, height="680px")

    # --- Tab 3: Flashcards ---
    with tab_flashcards:
        flashcards = dashboard.get("flashcards", [])
        render_flashcards(flashcards=flashcards)

    # --- Tab 4: Timeline ---
    with tab_timeline:
        timeline_events = dashboard.get("timeline", [])
        render_timeline(timeline_events=timeline_events)

else:
    # --- Empty State Welcome View ---
    st.markdown(
        """
        <div style="text-align: center; padding: 60px 20px; max-width: 800px; margin: 0 auto;">
            <h1 style="color: #6366F1; font-size: 3rem; margin-bottom: 12px;">🔬 Multimodal Deep Researcher</h1>
            <p style="color: #94A3B8; font-size: 1.25rem; line-height: 1.6; margin-bottom: 32px;">
                Transform complex academic papers, audio lectures, and video presentations into interactive 
                <b>Knowledge Graphs</b>, <b>Active-Recall Flashcards</b>, and <b>Chronological Timelines</b>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            """
            <div style="background: #1E293B; padding: 20px; border-radius: 8px; border-top: 3px solid #6366F1; height: 100%;">
                <h4 style="color: #F8FAFC; margin-top: 0;">1. Upload</h4>
                <p style="color: #94A3B8; font-size: 0.9rem;">Drop a PDF research paper, MP4 video, MP3 audio lecture, or text notes into the sidebar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div style="background: #1E293B; padding: 20px; border-radius: 8px; border-top: 3px solid #10B981; height: 100%;">
                <h4 style="color: #F8FAFC; margin-top: 0;">2. Gemini Polling</h4>
                <p style="color: #94A3B8; font-size: 0.9rem;">Files are ingested into the Gemini Files API and polled asynchronously until ACTIVE.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div style="background: #1E293B; padding: 20px; border-radius: 8px; border-top: 3px solid #F59E0B; height: 100%;">
                <h4 style="color: #F8FAFC; margin-top: 0;">3. Synthesis</h4>
                <p style="color: #94A3B8; font-size: 0.9rem;">Gemini 2.5 Flash synthesizes the content under strict Pydantic JSON schema constraints.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            """
            <div style="background: #1E293B; padding: 20px; border-radius: 8px; border-top: 3px solid #EC4899; height: 100%;">
                <h4 style="color: #F8FAFC; margin-top: 0;">4. Interactive UI</h4>
                <p style="color: #94A3B8; font-size: 0.9rem;">Explore the interactive Force-Directed Mind Map, flip flashcards, and chronological timeline.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/><br/>", unsafe_allow_html=True)
    st.info("👈 **Get Started:** Upload a research document in the sidebar to begin analysis.")
