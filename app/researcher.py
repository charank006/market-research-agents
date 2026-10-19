"""
app/researcher.py
-----------------
The Researcher agent — the primary information-gathering component of the
Multi-Agent Market Research system.

CURRENT STATUS — PLACEHOLDER
  This module defines the Researcher class with a documented interface but
  no live LLM or Tavily calls.  The stub allows the rest of the codebase
  (including tests) to import and type-hint against Researcher without
  requiring live credentials.

DESIGN INTENT
  In a completed implementation the Researcher will:
    1. Accept a research topic (e.g. a company name or investment question).
    2. Use web_search() from tools.py to retrieve up-to-date information.
    3. Send the raw search results to an LLM (via OpenRouter) to produce a
       structured summary.
    4. Return a validated ResearchResult object.

  The agent will be orchestrated by LangGraph in a later milestone.
"""

from __future__ import annotations

from app.schemas import ResearchResult


class Researcher:
    """
    Orchestrates web search and LLM summarisation for a given research topic.

    Parameters
    ----------
    model : str
        The LLM identifier to use via OpenRouter, e.g.
        "openai/gpt-4o-mini" or "anthropic/claude-3-haiku".
    max_search_results : int
        How many Tavily results to pass to the LLM per search (default 5).
    """

    def __init__(self, model: str = "openai/gpt-4o-mini", max_search_results: int = 5) -> None:
        self.model = model
        self.max_search_results = max_search_results

    def research(self, topic: str) -> ResearchResult:
        """
        Conduct research on *topic* and return a structured result.

        Parameters
        ----------
        topic : str
            The subject to investigate, e.g. "Stripe Inc competitive landscape".

        Returns
        -------
        ResearchResult
            A validated Pydantic model containing the summary, sources, and
            confidence score.

        Raises
        ------
        NotImplementedError
            Always raised in this placeholder implementation.
        """
        # ------------------------------------------------------------------ #
        # PLACEHOLDER — replace the body below in the next milestone          #
        # ------------------------------------------------------------------ #
        raise NotImplementedError(
            f"Researcher.research() is not yet implemented.  "
            f"LLM + Tavily integration will be added in the next milestone.  "
            f"(Topic received: {topic!r})"
        )
