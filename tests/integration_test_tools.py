"""
tests/integration_test_tools.py
--------------------------------
Opt-in integration test that makes a REAL Tavily API call.

This file is intentionally NOT named test_*.py so pytest does NOT collect
it automatically.  Running the full test suite (pytest) will never hit the
real API.

HOW TO RUN MANUALLY (requires a real TAVILY_API_KEY in .env):
  python tests/integration_test_tools.py

Or with pytest explicitly:
  pytest tests/integration_test_tools.py -v -s

WHY SEPARATE?
  Unit tests must be fast, deterministic, and credential-free.  Integration
  tests are slower, depend on external services, and consume API quota.
  Keeping them separate means `pytest` (CI) stays fast and free.
"""

from __future__ import annotations

import json
import sys
import os

# Make sure the project root is on sys.path when running this file directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools import (
    ToolConfigurationError,
    ToolError,
    web_search,
)


def run_integration_test() -> None:
    print("=" * 60)
    print("  Tavily Integration Test — LIVE API CALL")
    print("=" * 60)

    query = "Apple Inc Q3 2024 revenue"
    max_results = 3

    print(f"\n  Query      : {query!r}")
    print(f"  Max results: {max_results}")
    print("\n  Calling Tavily API...\n")

    try:
        results = web_search(query, max_results=max_results)
    except ToolConfigurationError as e:
        print(f"  ✗ Configuration error: {e}")
        print("  → Add your real TAVILY_API_KEY to .env and retry.")
        sys.exit(1)
    except ToolError as e:
        print(f"  ✗ Tool error: {e}")
        sys.exit(1)

    if not results:
        print("  ⚠  API returned 0 results for this query — not an error.")
        return

    print(f"  ✓ Received {len(results)} result(s)\n")

    for i, r in enumerate(results, 1):
        print(f"  ── Result {i} ─────────────────────────────────────────")
        print(f"  Title : {r['title']}")
        print(f"  URL   : {r['url']}")
        print(f"  Score : {r['score']:.3f}")
        print(f"  Date  : {r['published_date']}")
        # Truncate content to 200 chars for readability
        content_preview = r["content"][:200].replace("\n", " ")
        if len(r["content"]) > 200:
            content_preview += "…"
        print(f"  Text  : {content_preview}")
        print()

    # Structural assertions — these run against real results
    for r in results:
        assert isinstance(r["title"], str),          "title must be str"
        assert isinstance(r["url"], str),             "url must be str"
        assert isinstance(r["content"], str),         "content must be str"
        assert isinstance(r["score"], float),         "score must be float"
        assert r["published_date"] is None or isinstance(r["published_date"], str), \
            "published_date must be str or None"

    print("  ✓ All structural assertions passed.")
    print("=" * 60)


if __name__ == "__main__":
    run_integration_test()
