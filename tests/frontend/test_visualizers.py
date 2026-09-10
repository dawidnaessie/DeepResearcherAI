"""Unit tests for frontend visualizer components."""

from unittest.mock import MagicMock, patch
from src.backend.schemas.dashboard import (
    Flashcard,
    MindMapEdge,
    MindMapNode,
    TimelineEvent,
)
from src.frontend.components.visualizers import (
    CATEGORY_COLORS,
    DIFFICULTY_BADGES,
    _get_val,
    render_flashcards,
    render_mind_map,
    render_timeline,
)


def test_get_val_helper() -> None:
    """Verify _get_val extracts attributes from both Pydantic models and dictionaries."""
    node = MindMapNode(
        id="n1",
        label="Quantum",
        description="Quantum concept",
        importance=5,
    )
    assert _get_val(node, "id") == "n1"
    assert _get_val(node, "importance") == 5

    data_dict = {"id": "d1", "label": "Dict Concept", "category": "theory"}
    assert _get_val(data_dict, "id") == "d1"
    assert _get_val(data_dict, "category") == "theory"
    assert _get_val(data_dict, "missing", "default_val") == "default_val"


def test_palette_mappings() -> None:
    """Verify color palettes and difficulty badges exist."""
    assert "core_concept" in CATEGORY_COLORS
    assert "easy" in DIFFICULTY_BADGES
    assert "medium" in DIFFICULTY_BADGES
    assert "hard" in DIFFICULTY_BADGES


def test_render_empty_components() -> None:
    """Verify visualizers do not crash when given empty lists."""
    with patch("streamlit.info") as mock_info:
        render_mind_map([], [])
        mock_info.assert_called_once()

    with patch("streamlit.info") as mock_info:
        render_flashcards([])
        mock_info.assert_called_once()

    with patch("streamlit.info") as mock_info:
        render_timeline([])
        mock_info.assert_called_once()


def test_render_mind_map_construction() -> None:
    """Verify render_mind_map populates network and embeds HTML."""
    nodes = [
        MindMapNode(
            id="n1",
            label="Superposition",
            description="Linear combination of states",
            category="core_concept",
            importance=5,
        ),
        MindMapNode(
            id="n2",
            label="Measurement",
            description="Wavefunction collapse",
            category="methodology",
            importance=4,
        ),
    ]
    edges = [
        MindMapEdge(
            source="n1",
            target="n2",
            relationship="is observed through",
        )
    ]

    with patch("streamlit.components.v1.html") as mock_html, patch(
        "src.frontend.components.visualizers.Network"
    ) as mock_network_cls:
        mock_net = MagicMock()
        mock_network_cls.return_value = mock_net

        # Mock save_graph to write a dummy HTML file
        def fake_save(path: str) -> None:
            with open(path, "w", encoding="utf-8") as f:
                f.write("<html><body>Graph</body></html>")

        mock_net.save_graph.side_effect = fake_save

        render_mind_map(nodes, edges)

        assert mock_net.add_node.call_count == 2
        assert mock_net.add_edge.call_count == 1
        mock_html.assert_called_once()
