"""
run.py
------
Entry point for the Multi-Agent Market Research system.

Usage
-----
  python run.py                         # Run with the default example topic
  python run.py "Tesla competitive landscape"   # Run with a custom topic

What this does (currently)
  - Loads environment variables from .env (without printing them).
  - Accepts an optional research topic via the command line.
  - Displays a status message confirming the system is configured.
  - Does NOT make any live API calls at this stage.

Next steps
  When Tavily and Gemini integration is authorised, this file will
  instantiate a Researcher and call researcher.research(topic).
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def main() -> None:
    # ── 1. Load credentials from .env ────────────────────────────────────────
    # load_dotenv() reads the .env file and populates os.environ.
    # It does NOT raise an error if the file is missing — useful for CI/CD
    # where variables are injected by the environment directly.
    load_dotenv()

    # ── 2. Resolve research topic ─────────────────────────────────────────────
    # sys.argv[0] is the script name; sys.argv[1] is the first user argument.
    topic = sys.argv[1] if len(sys.argv) > 1 else "Apple Inc"

    # ── 3. Confirm environment readiness ─────────────────────────────────────
    tavily_configured = bool(
        os.getenv("TAVILY_API_KEY") and
        os.getenv("TAVILY_API_KEY") != "your_tavily_key_here"
    )
    gemini_configured = bool(
        os.getenv("GEMINI_API_KEY") and
        os.getenv("GEMINI_API_KEY") != "your_gemini_key_here"
    )

    print("=" * 60)
    print("  Multi-Agent Market Research System")
    print("=" * 60)
    print(f"  Research topic  : {topic}")
    print(f"  Tavily key      : {'✓ configured' if tavily_configured else '✗ placeholder — update .env'}")
    print(f"  Gemini key      : {'✓ configured' if gemini_configured else '✗ placeholder — update .env'}")
    print("-" * 60)
    print("  Status: Environment loaded.  No API calls made yet.")
    print("  Next step: Authorise the Tavily + Gemini milestone")
    print("             to begin live research.")
    print("=" * 60)


if __name__ == "__main__":
    main()
