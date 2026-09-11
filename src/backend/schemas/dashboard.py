"""Pydantic schemas for the Research Study Dashboard.

Designed for Gemini structured output schema extraction and FastAPI validation.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class MindMapNode(BaseModel):
    """Represents an individual conceptual node in the synthesized mind map knowledge graph."""

    id: str = Field(
        ...,
        description="Unique alphanumeric identifier for the node (e.g., 'node_1', 'concept_quantum_entanglement').",
    )
    label: str = Field(
        ...,
        description="Concise, human-readable title or name of the conceptual node.",
    )
    description: str = Field(
        ...,
        description="Detailed explanation or definition of the concept.",
    )
    category: str = Field(
        default="concept",
        description="Categorical classification of the node (e.g., 'core_concept', 'methodology', 'finding', 'entity').",
    )
    importance: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Significance hierarchy level from 1 (peripheral leaf detail) to 5 (central core theme).",
    )


class MindMapEdge(BaseModel):
    """Represents a directed or associative relationship between two MindMap nodes."""

    source: str = Field(
        ...,
        description="ID of the source MindMapNode where the directed relationship originates.",
    )
    target: str = Field(
        ...,
        description="ID of the target MindMapNode where the directed relationship terminates.",
    )
    relationship: str = Field(
        ...,
        description="Description of how the two nodes relate (e.g., 'causes', 'influences', 'contradicts', 'derives from').",
    )


class Flashcard(BaseModel):
    """Represents a question-answer revision card derived from key material."""

    id: str = Field(
        ...,
        description="Unique identifier for the flashcard (e.g., 'fc_1').",
    )
    question: str = Field(
        ...,
        description="Targeted conceptual question designed to evaluate mastery of a core finding.",
    )
    answer: str = Field(
        ...,
        description="Clear, accurate, and comprehensive answer synthesizing material from the source.",
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium",
        description="Pedagogical difficulty level of the question ('easy', 'medium', 'hard').",
    )
    topic: str = Field(
        ...,
        description="Subject matter or domain module tag for categorization.",
    )
    source_reference: str | None = Field(
        default=None,
        description="Direct citation, timestamp, section title, or page number from the source document.",
    )


class TimelineEvent(BaseModel):
    """Represents a chronological milestone, discovery, or sequential stage."""

    id: str = Field(
        ...,
        description="Unique identifier for the timeline milestone (e.g., 'event_1').",
    )
    date_or_period: str = Field(
        ...,
        description="Explicit calendar date, historical era, or sequential milestone identifier (e.g., '1953', 'Phase 1', '00:15:30').",
    )
    title: str = Field(
        ...,
        description="Short, descriptive headline of the milestone.",
    )
    summary: str = Field(
        ...,
        description="Detailed contextual summary of the occurrence and relevant mechanisms.",
    )
    significance: str = Field(
        ...,
        description="Impact and broader implications of this event on the subject domain.",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of source citations, timestamps, or section references corroborating this event.",
    )


class ExecutiveSummary(BaseModel):
    """Structured executive summary component providing a multi-dimensional synthesis."""

    overview: str = Field(
        ...,
        description="Comprehensive narrative overview synthesizing core theses, background, and essential subject matter.",
    )
    core_objectives: list[str] = Field(
        default_factory=list,
        description="Key scientific, technical, or research objectives addressed by the material.",
    )
    methodology: str = Field(
        ...,
        description="Detailed breakdown of theoretical frameworks, experimental methods, algorithms, or analytical models utilized.",
    )
    primary_conclusions: list[str] = Field(
        default_factory=list,
        description="High-impact conclusions, validated outcomes, and final implications of the research.",
    )


class ResearchStudyDashboard(BaseModel):
    """Root container schema representing the complete synthesized research study dashboard."""

    title: str = Field(
        ...,
        description="Overarching title of the research study synthesis.",
    )
    executive_summary: ExecutiveSummary = Field(
        ...,
        description="Structured multi-section executive summary synthesizing narrative overview, objectives, methodology, and conclusions.",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key high-impact takeaways, conclusions, or breakthroughs identified in the research.",
    )
    nodes: list[MindMapNode] = Field(
        default_factory=list,
        description="Knowledge graph nodes representing primary concepts, methodologies, and entities.",
    )
    edges: list[MindMapEdge] = Field(
        default_factory=list,
        description="Directed relational links connecting nodes in the mind map knowledge graph.",
    )
    flashcards: list[Flashcard] = Field(
        default_factory=list,
        description="Collection of spaced-repetition study flashcards extracted from the core material.",
    )
    timeline: list[TimelineEvent] = Field(
        default_factory=list,
        description="Chronological or phase-based sequence of events and breakthroughs.",
    )

    @field_validator("executive_summary", mode="before")
    @classmethod
    def _coerce_executive_summary(cls, v: Any) -> Any:
        """Coerce legacy string summaries into structured ExecutiveSummary instance."""
        if isinstance(v, str):
            return ExecutiveSummary(
                overview=v,
                core_objectives=[],
                methodology="Extracted from source material narrative.",
                primary_conclusions=[],
            )
        return v


# Alias for compatibility with architecture specification
ResearchDashboardPayload = ResearchStudyDashboard
