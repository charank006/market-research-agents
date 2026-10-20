"""
app/tools.py
------------
External tool integrations for the Multi-Agent Market Research system.

STATUS — IMPLEMENTED (Tavily web search)
  web_search() calls the Tavily Search API and returns a normalised list of
  result dicts.  Gemini integration lives in researcher.py and is deferred.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TAVILY WORKS
  Tavily is a search API purpose-built for AI agents.  Instead of returning
  raw HTML (like a traditional scraper), it:
    1. Crawls the web for the given query.
    2. Extracts clean text from the most relevant pages.
    3. Returns structured JSON — title, URL, clean content, relevance score.

  This means the Researcher can hand results directly to the LLM without any
  HTML parsing or cleaning step.

REQUEST SHAPE (what we send)
  POST https://api.tavily.com/search
  {
    "query":        "Apple Inc Q4 2024 earnings",
    "max_results":  5,
    "search_depth": "basic"   # "basic" is fast; "advanced" is deeper
  }

RESPONSE SHAPE (what we receive — simplified)
  {
    "query":   "Apple Inc Q4 2024 earnings",
    "answer":  "Apple reported...",         # optional AI-generated summary
    "results": [
      {
        "title":   "Apple Q4 2024 Earnings Report",
        "url":     "https://investor.apple.com/...",
        "content": "Apple Inc. reported revenue of $94.9 billion...",
        "score":   0.97,                    # Tavily relevance score [0–1]
        "published_date": "2024-11-01"      # may be None
      },
      ...
    ]
  }

NORMALISED OUTPUT (what web_search returns)
  Each dict in the returned list is guaranteed to have these keys:
    - "title"          : str  — page title (empty string if missing)
    - "url"            : str  — source URL (empty string if missing)
    - "content"        : str  — cleaned text excerpt
    - "score"          : float — Tavily relevance score (0.0 if missing)
    - "published_date" : str | None — ISO date string or None

EXCEPTION HANDLING
  We never swallow errors silently or fabricate results.  Instead we raise
  typed, descriptive exceptions:
    - ToolConfigurationError  — TAVILY_API_KEY missing from environment
    - ToolAuthenticationError — API rejected the key (401 / 403)
    - ToolRateLimitError      — usage quota exceeded
    - ToolRequestError        — bad query or other 4xx
    - ToolNetworkError        — timeout or connectivity failure
    - ToolError               — catch-all for unexpected SDK / API errors

  These are our own exception types (defined below), so the Researcher does
  not have to import Tavily-specific exceptions — it only needs to know about
  ToolError and its subclasses.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from tavily import (
    BadRequestError,
    InvalidAPIKeyError,
    MissingAPIKeyError,
    TavilyClient,
    UsageLimitExceededError,
)
from tavily.errors import ForbiddenError, TimeoutError as TavilyTimeoutError

# ── Custom exceptions ─────────────────────────────────────────────────────────
# We define our own hierarchy so that caller code (Researcher, tests) does not
# need to import anything from the `tavily` package directly.


class ToolError(Exception):
    """Base class for all tool errors in this system."""


class ToolConfigurationError(ToolError):
    """Raised when a required environment variable (e.g. API key) is absent."""


class ToolAuthenticationError(ToolError):
    """Raised when the API rejects our credentials (invalid or revoked key)."""


class ToolRateLimitError(ToolError):
    """Raised when the API usage quota has been exceeded."""


class ToolRequestError(ToolError):
    """Raised when the request itself is malformed or invalid (4xx, bad query)."""


class ToolNetworkError(ToolError):
    """Raised on timeout or connectivity failure reaching the API."""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_api_key() -> str:
    """
    Read TAVILY_API_KEY from the environment.

    We call load_dotenv() here so that the function works correctly whether
    it is called from run.py (which already loaded .env) or from a test that
    patches the environment directly.  load_dotenv() is a no-op if the
    variables are already set — it does not overwrite existing env vars.

    Raises
    ------
    ToolConfigurationError
        If the variable is absent or still holds the placeholder value.
    """
    load_dotenv()
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key or key == "your_tavily_key_here":
        raise ToolConfigurationError(
            "TAVILY_API_KEY is not set.  "
            "Add it to your .env file: TAVILY_API_KEY=tvly-..."
        )
    return key


def _normalise_result(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a single raw Tavily result dict into our guaranteed output shape.

    Tavily's API may omit optional fields (title, published_date, score) for
    some results.  This function applies safe defaults so callers never have
    to guard against KeyError or missing fields.

    Parameters
    ----------
    raw : dict
        A single item from response["results"].

    Returns
    -------
    dict with keys: title, url, content, score, published_date
    """
    return {
        "title":          raw.get("title", ""),
        "url":            raw.get("url", ""),
        "content":        raw.get("content", ""),
        "score":          float(raw.get("score", 0.0)),
        "published_date": raw.get("published_date"),   # str or None
    }


# ── Public API ────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Search the web for information relevant to *query* using the Tavily API.

    Parameters
    ----------
    query : str
        The search query, e.g. "Tesla Q3 2024 revenue".
        Must be a non-empty string.
    max_results : int
        Maximum number of results to return.
        Must be an integer in [1, 20].  Default is 5.

    Returns
    -------
    list[dict]
        A list of up to *max_results* result dicts.  Each dict contains:
          - "title"          : str   — page title
          - "url"            : str   — source URL
          - "content"        : str   — cleaned text excerpt from the page
          - "score"          : float — Tavily relevance score (0.0 – 1.0)
          - "published_date" : str | None — ISO date string, or None

        The list may be shorter than *max_results* if fewer relevant pages
        were found.  It is NEVER silently empty due to an API error — errors
        always raise an exception (see below).

    Raises
    ------
    ValueError
        If *query* is empty or *max_results* is outside [1, 20].
    ToolConfigurationError
        If TAVILY_API_KEY is missing from the environment.
    ToolAuthenticationError
        If the API rejects the key (invalid or revoked).
    ToolRateLimitError
        If the API usage quota has been exceeded.
    ToolRequestError
        If the query itself is malformed or rejected by the API.
    ToolNetworkError
        If the request times out or cannot reach the API.
    ToolError
        For any other unexpected error from the SDK or API.

    Examples
    --------
    >>> results = web_search("Apple Inc Q4 2024 earnings", max_results=3)
    >>> for r in results:
    ...     print(r["title"], r["url"])
    """
    # ── 1. Input validation ───────────────────────────────────────────────────
    # We validate before touching the network so that callers get a clear
    # ValueError immediately, without wasting an API call.
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    if not isinstance(max_results, int) or not (1 <= max_results <= 20):
        raise ValueError("max_results must be an integer between 1 and 20.")

    # ── 2. Load API key ───────────────────────────────────────────────────────
    api_key = _get_api_key()

    # ── 3. Instantiate client ─────────────────────────────────────────────────
    # TavilyClient is lightweight — it stores the key and sets up an httpx
    # session.  We create a new instance per call for simplicity.  In the
    # future, the Researcher can cache a module-level client for efficiency.
    client = TavilyClient(api_key=api_key)

    # ── 4. Call the API ───────────────────────────────────────────────────────
    try:
        response = client.search(
            query=query.strip(),
            max_results=max_results,
            search_depth="basic",   # "basic" is fast and sufficient for now;
                                     # "advanced" is slower but more thorough
        )

    # ── 5. Map SDK exceptions → our own typed exceptions ─────────────────────
    # Why map exceptions?  So the Researcher does not need to import from
    # `tavily` — it only depends on ToolError.  This also lets us add better
    # context messages without leaking the raw API key in tracebacks.

    except MissingAPIKeyError as exc:
        # SDK raises this when api_key="" — shouldn't happen after _get_api_key
        # but we guard it for completeness.
        raise ToolConfigurationError(
            "TAVILY_API_KEY is missing.  This should not happen after "
            "_get_api_key() — check for env mutation."
        ) from exc

    except InvalidAPIKeyError as exc:
        raise ToolAuthenticationError(
            "The Tavily API rejected your key.  "
            "Verify TAVILY_API_KEY in .env is correct and active."
        ) from exc

    except ForbiddenError as exc:
        raise ToolAuthenticationError(
            "Access forbidden by the Tavily API.  "
            "Your key may lack permission for this endpoint."
        ) from exc

    except UsageLimitExceededError as exc:
        raise ToolRateLimitError(
            "Tavily API usage limit exceeded.  "
            "Wait before retrying or upgrade your plan."
        ) from exc

    except BadRequestError as exc:
        raise ToolRequestError(
            f"Tavily rejected the search request: {exc}"
        ) from exc

    except TavilyTimeoutError as exc:
        raise ToolNetworkError(
            "The Tavily API request timed out.  "
            "Check your internet connection and retry."
        ) from exc

    except Exception as exc:
        # Catch-all: ConnectionError, httpx errors, unexpected SDK changes.
        # We do NOT swallow the original exception — we chain it with `from exc`
        # so the traceback still shows the root cause in debug mode.
        raise ToolError(
            f"Unexpected error calling Tavily API: {type(exc).__name__}: {exc}"
        ) from exc

    # ── 6. Validate and normalise the response ────────────────────────────────
    # The API contract says response["results"] is a list of dicts.
    # We guard against malformed responses defensively.
    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        raise ToolError(
            f"Tavily API returned an unexpected response shape.  "
            f"Expected 'results' to be a list, got: {type(raw_results).__name__}.  "
            f"Response keys: {list(response.keys())}"
        )

    # Normalise every result into our guaranteed output shape.
    return [_normalise_result(r) for r in raw_results]
