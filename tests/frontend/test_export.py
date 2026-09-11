"""Unit tests for Markdown study guide export functionality in src/frontend/app.py."""

from src.frontend.app import format_as_markdown


def test_format_as_markdown_structured() -> None:
    """Verify Markdown export with structured executive summary, flashcards, and timeline."""
    payload = {
        "title": "Quantum Error Mitigation",
        "executive_summary": {
            "overview": "Synthesis of zero-noise extrapolation techniques in superconducting processors.",
            "core_objectives": ["Measure gate errors", "Extrapolate to zero noise"],
            "methodology": "Pulse-level stretching evaluated on ibm_torino.",
            "primary_conclusions": ["2.3x fidelity improvement achieved."],
        },
        "key_findings": [
            "Richardson extrapolation suppressed coherent noise.",
            "Measurement error mitigation scales linearly.",
        ],
        "flashcards": [
            {
                "question": "What is Zero-Noise Extrapolation?",
                "answer": "A technique that intentionally amplifies noise at controlled factors to extrapolate back to zero noise.",
                "difficulty": "medium",
                "topic": "Quantum Computing",
                "source_reference": "Section 4.1",
            }
        ],
        "timeline": [
            {
                "date_or_period": "2024-Q2",
                "title": "Initial Benchmark",
                "summary": "First calibration on 127-qubit system.",
                "significance": "Demonstrated circuit depth > 100.",
                "sources": ["arXiv:2405.00000"],
            }
        ],
    }

    md = format_as_markdown(payload)

    # Title & Header
    assert "# Quantum Error Mitigation" in md
    assert "## 📝 Executive Summary" in md

    # Structured summary components
    assert "### Overview" in md
    assert "Synthesis of zero-noise" in md
    assert "### Core Objectives" in md
    assert "- Measure gate errors" in md
    assert "- Extrapolate to zero noise" in md
    assert "### Methodology & Technical Frameworks" in md
    assert "Pulse-level stretching" in md
    assert "### Primary Conclusions" in md
    assert "- 2.3x fidelity improvement achieved." in md

    # Key findings
    assert "## 🎯 Key Findings & Insights" in md
    assert "- Richardson extrapolation" in md

    # Flashcards with blockquote
    assert "## 🗂️ Active-Recall Study Flashcards" in md
    assert "### Flashcard 1: What is Zero-Noise Extrapolation?" in md
    assert "**Topic:** `Quantum Computing`" in md
    assert "**Difficulty:** `Medium`" in md
    assert "**Source Reference:** *Section 4.1*" in md
    assert "> A technique that intentionally amplifies noise" in md

    # Timeline
    assert "## ⏳ Chronological & Phase Timeline" in md
    assert "### [2024-Q2] Initial Benchmark" in md
    assert "First calibration on 127-qubit system." in md
    assert "**Significance:** Demonstrated circuit depth > 100." in md
    assert "**Sources:** arXiv:2405.00000" in md


def test_format_as_markdown_legacy_string_summary() -> None:
    """Verify Markdown export handles legacy flat string executive summaries."""
    payload = {
        "title": "Legacy Study",
        "executive_summary": "Flat text narrative summary without dict structure.",
        "key_findings": ["Finding 1"],
        "flashcards": [],
        "timeline": [],
    }

    md = format_as_markdown(payload)
    assert "# Legacy Study" in md
    assert "Flat text narrative summary without dict structure." in md
    assert "- Finding 1" in md
