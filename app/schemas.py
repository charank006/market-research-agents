"""
app/schemas.py
--------------
Defines the shared Pydantic data models (schemas) used across the system.

Why Pydantic?
  Pydantic validates data at runtime using Python type hints.  When an agent
  produces a research result, passing it through these models guarantees that
  every field has the correct type before it is used downstream — catching
  bugs early and producing clear error messages.

Current models
  ResearchResult — represents the output of a single research task.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResearchResult(BaseModel):
    """
    The structured output produced by the Researcher agent for a given topic.

    Attributes
    ----------
    topic : str
        The research question or company name that was investigated.
    summary : str
        A concise narrative summarising the findings.
    sources : list[str]
        URLs or citation strings used to support the summary.
    confidence : float
        A self-reported confidence score in [0.0, 1.0].
        0.0 = no confidence; 1.0 = fully confident.
    researched_at : datetime
        UTC timestamp of when this result was produced.
    error : Optional[str]
        If something went wrong during research, the error message is stored
        here rather than raising an exception, so the system can degrade
        gracefully.
    """

    topic: str = Field(..., min_length=1, description="The research subject.")
    summary: str = Field(..., min_length=1, description="Narrative summary of findings.")
    sources: list[str] = Field(default_factory=list, description="Supporting URLs or citations.")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0.",
    )
    researched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this result was produced.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if research failed; None on success.",
    )

    model_config = ConfigDict(from_attributes=True)
