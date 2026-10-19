"""
tests/test_schemas.py
---------------------
Unit tests for app/schemas.py.

Why test schemas?
  Schemas are the contract between agents.  If a schema silently accepts
  invalid data (e.g. a confidence score of 5.0), downstream agents will
  produce incorrect output that is very hard to debug.  These tests verify
  that Pydantic enforces the contract correctly.

Run with:
  pytest tests/test_schemas.py -v
"""

import pytest
from pydantic import ValidationError

from app.schemas import ResearchResult


# ── Happy-path tests ────────────────────────────────────────────────────────

class TestResearchResultValid:
    """Tests that verify ResearchResult accepts correct data."""

    def test_minimal_valid_result(self):
        """Only required fields — defaults should fill the rest."""
        result = ResearchResult(topic="OpenAI", summary="Leading AI lab.")
        assert result.topic == "OpenAI"
        assert result.summary == "Leading AI lab."
        assert result.sources == []          # default empty list
        assert result.confidence == 0.0      # default value
        assert result.error is None          # default None
        assert result.researched_at is not None

    def test_full_valid_result(self):
        """All fields explicitly provided."""
        result = ResearchResult(
            topic="Stripe",
            summary="Global payments infrastructure.",
            sources=["https://stripe.com/newsroom", "https://techcrunch.com/stripe"],
            confidence=0.85,
            error=None,
        )
        assert result.topic == "Stripe"
        assert len(result.sources) == 2
        assert result.confidence == 0.85

    def test_error_field_stores_message(self):
        """A failed research result should record its error message."""
        result = ResearchResult(
            topic="UnknownCorp",
            summary="No information found.",
            error="Tavily returned zero results.",
        )
        assert result.error == "Tavily returned zero results."

    def test_confidence_boundary_zero(self):
        result = ResearchResult(topic="X", summary="Y", confidence=0.0)
        assert result.confidence == 0.0

    def test_confidence_boundary_one(self):
        result = ResearchResult(topic="X", summary="Y", confidence=1.0)
        assert result.confidence == 1.0


# ── Validation-error tests ───────────────────────────────────────────────────

class TestResearchResultInvalid:
    """Tests that verify ResearchResult rejects invalid data."""

    def test_empty_topic_raises(self):
        """An empty topic string should fail the min_length=1 constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchResult(topic="", summary="Some summary.")
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "topic" in fields

    def test_empty_summary_raises(self):
        """An empty summary string should fail the min_length=1 constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchResult(topic="OpenAI", summary="")
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "summary" in fields

    def test_missing_topic_raises(self):
        """topic is a required field — omitting it must raise ValidationError."""
        with pytest.raises(ValidationError):
            ResearchResult(summary="Missing topic field.")

    def test_confidence_above_one_raises(self):
        """confidence > 1.0 violates the le=1.0 constraint."""
        with pytest.raises(ValidationError):
            ResearchResult(topic="X", summary="Y", confidence=1.5)

    def test_confidence_below_zero_raises(self):
        """confidence < 0.0 violates the ge=0.0 constraint."""
        with pytest.raises(ValidationError):
            ResearchResult(topic="X", summary="Y", confidence=-0.1)
