"""Unit tests for Research Dashboard Pydantic schemas.

Validates instantiation, constraints, serialization, and JSON schema export
for Gemini structured output configuration.
"""

import json
import pytest
from pydantic import ValidationError

from src.backend.schemas.dashboard import (
    ExecutiveSummary,
    Flashcard,
    MindMapEdge,
    MindMapNode,
    ResearchDashboardPayload,
    ResearchStudyDashboard,
    TimelineEvent,
)


def test_executive_summary_instantiation() -> None:
    """Test structured ExecutiveSummary model fields and serialization."""
    summary = ExecutiveSummary(
        overview="High-level synthesis of quantum algorithms.",
        core_objectives=["Achieve quantum supremacy", "Minimize gate errors"],
        methodology="Variational Quantum Eigensolver evaluated on 127-qubit QPUs.",
        primary_conclusions=["Demonstrated 4x circuit depth improvement.", "Error mitigation is viable."],
    )
    assert summary.overview.startswith("High-level")
    assert len(summary.core_objectives) == 2
    assert "Variational" in summary.methodology
    assert len(summary.primary_conclusions) == 2



def test_mind_map_node_instantiation() -> None:
    """Test valid creation and default values of MindMapNode."""
    node = MindMapNode(
        id="node_1",
        label="Quantum Teleportation",
        description="Transfer of quantum states between separated systems.",
        category="core_concept",
        importance=5,
    )
    assert node.id == "node_1"
    assert node.label == "Quantum Teleportation"
    assert node.importance == 5
    assert node.category == "core_concept"


def test_mind_map_node_importance_bounds() -> None:
    """Ensure importance is constrained between 1 and 5."""
    # Under minimum
    with pytest.raises(ValidationError):
        MindMapNode(
            id="node_low",
            label="Too low",
            description="Test",
            importance=0,
        )

    # Over maximum
    with pytest.raises(ValidationError):
        MindMapNode(
            id="node_high",
            label="Too high",
            description="Test",
            importance=6,
        )


def test_mind_map_edge_instantiation() -> None:
    """Test valid creation of MindMapEdge."""
    edge = MindMapEdge(
        source="node_1",
        target="node_2",
        relationship="relies upon",
    )
    assert edge.source == "node_1"
    assert edge.target == "node_2"
    assert edge.relationship == "relies upon"


def test_flashcard_instantiation_and_difficulty() -> None:
    """Test flashcard validation, difficulty literals, and optional source."""
    card = Flashcard(
        id="fc_1",
        question="What is Bell's Theorem?",
        answer="A proof that no physical theory of local hidden variables can reproduce quantum mechanics.",
        difficulty="hard",
        topic="Quantum Physics",
        source_reference="Section 3.2, page 14",
    )
    assert card.difficulty == "hard"
    assert card.source_reference == "Section 3.2, page 14"

    # Invalid difficulty literal
    with pytest.raises(ValidationError):
        Flashcard(
            id="fc_invalid",
            question="Question",
            answer="Answer",
            difficulty="extreme",  # type: ignore[arg-type]
            topic="General",
        )


def test_timeline_event_instantiation() -> None:
    """Test TimelineEvent creation and source defaults."""
    event = TimelineEvent(
        id="event_1",
        date_or_period="1935",
        title="EPR Paradox Published",
        summary="Einstein, Podolsky, and Rosen publish critique of quantum completeness.",
        significance="Catalyzed the exploration of quantum entanglement.",
        sources=["Physical Review 47, 777"],
    )
    assert event.date_or_period == "1935"
    assert len(event.sources) == 1
    assert event.sources[0] == "Physical Review 47, 777"


def test_research_study_dashboard_roundtrip() -> None:
    """Test full dashboard root model serialization and deserialization."""
    dashboard = ResearchStudyDashboard(
        title="Advances in Quantum Computing",
        executive_summary="Comprehensive analysis of recent superconducting qubit coherence milestones.",
        key_findings=[
            "Coherence times doubled using niobium resonator filtering.",
            "Surface code error threshold reached in 72-qubit processor.",
        ],
        nodes=[
            MindMapNode(
                id="n1",
                label="Superconducting Qubits",
                description="Artificial atoms formed by Josephson junctions.",
                category="hardware",
                importance=5,
            )
        ],
        edges=[
            MindMapEdge(
                source="n1",
                target="n2",
                relationship="demonstrates error suppression in",
            )
        ],
        flashcards=[
            Flashcard(
                id="fc1",
                question="What is a Josephson Junction?",
                answer="A thin barrier separating two superconductors exhibiting tunneling effects.",
                difficulty="medium",
                topic="Hardware",
            )
        ],
        timeline=[
            TimelineEvent(
                id="te1",
                date_or_period="2024-Q1",
                title="Fault-tolerance Milestone",
                summary="Breakthrough in physical-to-logical qubit ratio.",
                significance="Demonstrates path to scalable fault tolerance.",
            )
        ],
    )

    # Test serialization to JSON
    json_str = dashboard.model_dump_json()
    assert "Superconducting Qubits" in json_str

    # Test deserialization from JSON
    restored = ResearchStudyDashboard.model_validate_json(json_str)
    assert restored.title == dashboard.title
    assert len(restored.nodes) == 1
    assert restored.nodes[0].label == "Superconducting Qubits"
    assert len(restored.flashcards) == 1
    assert len(restored.timeline) == 1


def test_alias_equivalence() -> None:
    """Verify that ResearchDashboardPayload is an alias of ResearchStudyDashboard."""
    assert ResearchDashboardPayload is ResearchStudyDashboard


def test_json_schema_export_for_gemini() -> None:
    """Verify model_json_schema() exports a complete schema suitable for Gemini response_schema."""
    schema = ResearchStudyDashboard.model_json_schema()

    assert schema["type"] == "object"
    assert "properties" in schema
    assert "title" in schema["properties"]
    assert "executive_summary" in schema["properties"]
    assert "nodes" in schema["properties"]
    assert "edges" in schema["properties"]
    assert "flashcards" in schema["properties"]
    assert "timeline" in schema["properties"]

    # Verify that descriptions exist on fields to guide Gemini
    assert "description" in schema["properties"]["title"]
    assert "description" in schema["properties"]["executive_summary"]

    # Validate JSON serializability of the schema dictionary itself
    json_schema_str = json.dumps(schema)
    assert len(json_schema_str) > 0
