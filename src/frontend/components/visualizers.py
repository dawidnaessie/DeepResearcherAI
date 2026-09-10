"""Interactive visualizer components for the Multimodal Deep Researcher frontend.

Renders interactive Knowledge Graphs (pyvis), flip-style Flashcards,
and vertical Chronological Timelines in Streamlit.
"""

import os
import tempfile
from typing import Any

from pyvis.network import Network
import streamlit as st
import streamlit.components.v1 as components

# Category color palette for Mind Map nodes
CATEGORY_COLORS: dict[str, str] = {
    "core_concept": "#6366F1",  # Indigo
    "concept": "#8B5CF6",       # Violet
    "methodology": "#10B981",   # Emerald
    "finding": "#F59E0B",       # Amber
    "hardware": "#06B6D4",      # Cyan
    "architecture": "#3B82F6",  # Blue
    "theory": "#EC4899",        # Pink
    "entity": "#14B8A6",        # Teal
}
DEFAULT_NODE_COLOR = "#8B5CF6"

DIFFICULTY_BADGES: dict[str, tuple[str, str]] = {
    "easy": ("🟢 Easy", "#10B981"),
    "medium": ("🟡 Medium", "#F59E0B"),
    "hard": ("🔴 Hard", "#EF4444"),
}


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Extract value from either a Pydantic model or a dictionary."""
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def render_mind_map(
    nodes: list[Any],
    edges: list[Any],
    height: str = "650px",
) -> None:
    """Generate and render an interactive Force-Directed Knowledge Graph using PyVis.

    Args:
        nodes: List of MindMapNode models or dictionaries.
        edges: List of MindMapEdge models or dictionaries.
        height: CSS height of the interactive canvas.
    """
    if not nodes:
        st.info("ℹ️ No conceptual nodes found to construct a Knowledge Graph.")
        return

    st.markdown(
        """
        <div style="margin-bottom: 12px; font-size: 0.9rem; color: #94A3B8;">
            💡 <b>Interactive Graph:</b> Click and drag nodes to inspect connections. Scroll to zoom in/out. Hover over nodes to view complete definitions.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize PyVis network with dark modern theme and CDN assets
    net = Network(
        height=height,
        width="100%",
        bgcolor="#0F172A",
        font_color="#F8FAFC",
        directed=True,
        cdn_resources="remote",
    )

    # Configure physics for smooth force-directed organic layout
    net.set_options(
        """
        {
          "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {
              "color": "#F8FAFC",
              "size": 14,
              "face": "system-ui, -apple-system, sans-serif"
            },
            "shadow": {
              "enabled": true,
              "color": "rgba(0,0,0,0.5)",
              "size": 10
            }
          },
          "edges": {
            "color": {
              "color": "#64748B",
              "highlight": "#38BDF8",
              "hover": "#38BDF8"
            },
            "font": {
              "color": "#CBD5E1",
              "size": 11,
              "align": "middle",
              "background": "#1E293B"
            },
            "smooth": {
              "type": "continuous",
              "roundness": 0.3
            },
            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 0.8
              }
            }
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -4000,
              "centralGravity": 0.3,
              "springLength": 130,
              "springConstant": 0.04,
              "damping": 0.09
            },
            "minVelocity": 0.75,
            "stabilization": {
              "iterations": 150
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true,
            "keyboard": true
          }
        }
        """
    )

    # Add nodes
    for node in nodes:
        node_id = str(_get_val(node, "id"))
        label = str(_get_val(node, "label", node_id))
        description = str(_get_val(node, "description", ""))
        category = str(_get_val(node, "category", "concept")).lower()
        importance = int(_get_val(node, "importance", 3))

        color = CATEGORY_COLORS.get(category, DEFAULT_NODE_COLOR)
        size = 16 + (importance * 6)  # Scale node diameter by hierarchy importance (1 to 5)

        # Hover tooltip HTML
        tooltip = (
            f"<div style='font-family: sans-serif; padding: 6px; max-width: 280px;'>"
            f"<b style='color: {color}; font-size: 14px;'>{label}</b><br/>"
            f"<span style='font-size: 11px; text-transform: uppercase; color: #94A3B8;'>{category} (Importance: {importance}/5)</span><br/>"
            f"<p style='margin-top: 6px; font-size: 12px; color: #E2E8F0;'>{description}</p>"
            f"</div>"
        )

        net.add_node(
            node_id,
            label=label,
            title=tooltip,
            color=color,
            size=size,
        )

    # Add edges
    for edge in edges:
        source = str(_get_val(edge, "source"))
        target = str(_get_val(edge, "target"))
        relationship = str(_get_val(edge, "relationship", "relates to"))

        net.add_edge(
            source,
            target,
            label=relationship,
            title=relationship,
        )

    # Generate and embed HTML cleanly
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
    try:
        temp_path = temp_file.name
        temp_file.close()
        net.save_graph(temp_path)
        with open(temp_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=700, scrolling=False)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def render_flashcards(flashcards: list[Any]) -> None:
    """Render interactive active-recall study flashcards with flip-to-reveal answers.

    Args:
        flashcards: List of Flashcard models or dictionaries.
    """
    if not flashcards:
        st.info("ℹ️ No flashcards generated for this material.")
        return

    st.markdown(f"### 🗂️ Active-Recall Flashcards ({len(flashcards)} cards)")
    st.caption("Test your comprehension before expanding each card to reveal the complete answer and citation.")

    # Difficulty filter
    filter_col1, filter_col2 = st.columns([1, 3])
    with filter_col1:
        difficulty_filter = st.selectbox(
            "Filter by Difficulty",
            options=["All", "Easy", "Medium", "Hard"],
            index=0,
            key="flashcard_diff_filter",
        )

    # Filter cards
    filtered_cards = []
    for card in flashcards:
        diff = str(_get_val(card, "difficulty", "medium")).lower()
        if difficulty_filter == "All" or diff == difficulty_filter.lower():
            filtered_cards.append(card)

    if not filtered_cards:
        st.info(f"No flashcards match difficulty '{difficulty_filter}'.")
        return

    # Render cards in a 2-column grid
    for idx, card in enumerate(filtered_cards):
        q_text = str(_get_val(card, "question"))
        a_text = str(_get_val(card, "answer"))
        diff = str(_get_val(card, "difficulty", "medium")).lower()
        topic = str(_get_val(card, "topic", "General"))
        source_ref = _get_val(card, "source_reference")

        diff_label, diff_color = DIFFICULTY_BADGES.get(diff, ("⚪ Medium", "#94A3B8"))

        card_container = st.container(border=True)
        with card_container:
            # Card header badges
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"<span style='background: #334155; color: #38BDF8; padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;'>🏷️ {topic}</span>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"<div style='text-align: right;'><span style='background: {diff_color}22; color: {diff_color}; border: 1px solid {diff_color}; padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;'>{diff_label}</span></div>",
                    unsafe_allow_html=True,
                )

            st.markdown(f"**Q{idx + 1}: {q_text}**")

            with st.expander("🔍 Click to Reveal Answer & Citation", expanded=False):
                st.markdown(
                    f"""
                    <div style="background: #1E293B; border-left: 4px solid #38BDF8; padding: 12px; border-radius: 4px; margin-top: 6px;">
                        <b style="color: #38BDF8;">Answer:</b>
                        <p style="margin-top: 4px; color: #F1F5F9;">{a_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if source_ref:
                    st.caption(f"📍 **Source Reference:** `{source_ref}`")


def render_timeline(timeline_events: list[Any]) -> None:
    """Render a vertical chronological milestone timeline.

    Args:
        timeline_events: List of TimelineEvent models or dictionaries.
    """
    if not timeline_events:
        st.info("ℹ️ No chronological or phase timeline events identified in this material.")
        return

    st.markdown(f"### ⏳ Chronological & Phase Milestones ({len(timeline_events)} events)")
    st.caption("Progression of critical breakthroughs, discoveries, and sequential stages extracted from the study.")

    for idx, event in enumerate(timeline_events):
        period = str(_get_val(event, "date_or_period", "Milestone"))
        title = str(_get_val(event, "title", "Untitled Milestone"))
        summary = str(_get_val(event, "summary", ""))
        significance = str(_get_val(event, "significance", ""))
        sources = _get_val(event, "sources", [])

        st.markdown(
            f"""
            <div style="border-left: 3px solid #6366F1; padding-left: 18px; margin-left: 8px; margin-bottom: 24px; position: relative;">
                <div style="position: absolute; left: -9px; top: 0; width: 15px; height: 15px; border-radius: 50%; background: #6366F1; border: 3px solid #0F172A;"></div>
                <div style="display: inline-block; background: #312E81; color: #A5B4FC; font-size: 0.8rem; font-weight: 700; padding: 2px 10px; border-radius: 12px; margin-bottom: 6px;">
                    📅 {period}
                </div>
                <h4 style="margin: 4px 0 8px 0; color: #F8FAFC;">{idx + 1}. {title}</h4>
                <p style="color: #CBD5E1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 8px;">{summary}</p>
                <div style="background: #1E293B; border-radius: 6px; padding: 10px 14px; margin-top: 6px; font-size: 0.9rem;">
                    <b style="color: #FBBF24;">💡 Significance:</b> <span style="color: #E2E8F0;">{significance}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if sources and isinstance(sources, list):
            source_pills = " ".join(
                [
                    f"<span style='background: #334155; color: #94A3B8; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px;'>📄 {s}</span>"
                    for s in sources
                ]
            )
            st.markdown(
                f"<div style='margin-left: 26px; margin-bottom: 16px;'>{source_pills}</div>",
                unsafe_allow_html=True,
            )
