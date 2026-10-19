"""
app/tools.py
------------
External tool integrations for the Multi-Agent Market Research system.

CURRENT STATUS — PLACEHOLDER
  No live API calls are made here yet.  The functions below define the
  interfaces that the Researcher agent will call once API keys are
  configured and Tavily integration is authorised.

FUTURE INTEGRATION — Tavily Web Search
  Tavily is a search API built specifically for AI agents.  Unlike scraping
  raw HTML, Tavily returns clean, pre-processed text that LLMs can reason
  over directly.  The `tavily-python` SDK is already installed.

  When integration is authorised, the implementation will look like:
    from tavily import TavilyClient
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    results = client.search(query="Apple Inc Q4 2024 earnings")
"""

from __future__ import annotations

import os
from typing import Any


def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Search the web for information relevant to *query*.

    Parameters
    ----------
    query : str
        The search query, e.g. "Tesla Q3 2024 revenue".
    max_results : int
        Maximum number of results to return (default 5).

    Returns
    -------
    list[dict]
        Each dict will contain at least:
          - "title"   : page title
          - "url"     : source URL
          - "content" : extracted text snippet

    Raises
    ------
    NotImplementedError
        Always raised in this placeholder implementation.
    """
    # ------------------------------------------------------------------ #
    # PLACEHOLDER — replace the body below in the next milestone          #
    # ------------------------------------------------------------------ #
    raise NotImplementedError(
        "web_search is not yet implemented.  "
        "Tavily integration will be added in the next milestone."
    )
