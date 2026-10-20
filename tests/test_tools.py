"""
tests/test_tools.py
-------------------
Unit tests for app/tools.py — specifically the web_search() function.

IMPORTANT: These tests use unittest.mock to patch TavilyClient.
They do NOT make real API calls and do NOT require a real TAVILY_API_KEY.

Design decisions
  - We patch at the point of use: 'app.tools.TavilyClient'.  This is a
    standard mock.patch best practice — patch where the name is *imported*,
    not where it is *defined*.
  - We also patch os.getenv / the env variable via monkeypatch (pytest
    fixture) to test credential handling without touching .env.
  - We test both the happy path and every exception branch in isolation.

Run with:
  pytest tests/test_tools.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tools import (
    ToolAuthenticationError,
    ToolConfigurationError,
    ToolError,
    ToolNetworkError,
    ToolRateLimitError,
    ToolRequestError,
    web_search,
)
from tavily import (
    BadRequestError,
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)
from tavily.errors import ForbiddenError, TimeoutError as TavilyTimeoutError


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fake_api_key(monkeypatch):
    """
    Inject a fake (non-placeholder) API key into the environment for every
    test in this file.  autouse=True means every test gets this automatically
    without calling it explicitly.

    We also patch load_dotenv to a no-op so tests never accidentally read the
    real .env file.
    """
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-fake-key-12345")
    with patch("app.tools.load_dotenv"):
        yield


def _make_raw_result(
    title="Test Title",
    url="https://example.com/page",
    content="Some extracted content.",
    score=0.85,
    published_date="2024-10-01",
) -> dict:
    """Helper to build a raw Tavily result dict (as the SDK returns it)."""
    return {
        "title": title,
        "url": url,
        "content": content,
        "score": score,
        "published_date": published_date,
    }


def _make_tavily_response(results: list[dict], query="test query") -> dict:
    """Helper to build a full Tavily API response dict."""
    return {
        "query": query,
        "answer": None,
        "results": results,
    }


# ── Happy-path tests ──────────────────────────────────────────────────────────

class TestWebSearchHappyPath:
    """Tests that verify correct behaviour when the API responds normally."""

    @patch("app.tools.TavilyClient")
    def test_returns_list_of_dicts(self, mock_client_cls):
        """web_search returns a list when the API call succeeds."""
        raw = [_make_raw_result()]
        mock_client_cls.return_value.search.return_value = _make_tavily_response(raw)

        results = web_search("Apple earnings")

        assert isinstance(results, list)
        assert len(results) == 1

    @patch("app.tools.TavilyClient")
    def test_normalised_keys_present(self, mock_client_cls):
        """Every result dict must contain the five guaranteed keys."""
        raw = [_make_raw_result(title="My Title", url="https://x.com", content="Text.")]
        mock_client_cls.return_value.search.return_value = _make_tavily_response(raw)

        results = web_search("test query")
        r = results[0]

        assert set(r.keys()) == {"title", "url", "content", "score", "published_date"}
        assert r["title"] == "My Title"
        assert r["url"] == "https://x.com"
        assert r["content"] == "Text."

    @patch("app.tools.TavilyClient")
    def test_score_is_float(self, mock_client_cls):
        """score is cast to float even when the API returns an int."""
        raw = [_make_raw_result(score=1)]  # int, not float
        mock_client_cls.return_value.search.return_value = _make_tavily_response(raw)

        results = web_search("test")
        assert isinstance(results[0]["score"], float)
        assert results[0]["score"] == 1.0

    @patch("app.tools.TavilyClient")
    def test_multiple_results_returned(self, mock_client_cls):
        """All results from the API are returned and normalised."""
        raw = [_make_raw_result(title=f"Result {i}", url=f"https://r{i}.com") for i in range(3)]
        mock_client_cls.return_value.search.return_value = _make_tavily_response(raw)

        results = web_search("multi test", max_results=3)
        assert len(results) == 3
        assert results[1]["title"] == "Result 1"

    @patch("app.tools.TavilyClient")
    def test_missing_optional_fields_get_defaults(self, mock_client_cls):
        """
        If the API omits optional fields (title, score, published_date),
        the normaliser fills in safe defaults instead of raising KeyError.
        """
        raw = [{"url": "https://minimal.com", "content": "Minimal result."}]
        mock_client_cls.return_value.search.return_value = _make_tavily_response(raw)

        results = web_search("minimal")
        r = results[0]

        assert r["title"] == ""           # default for missing title
        assert r["score"] == 0.0          # default for missing score
        assert r["published_date"] is None  # default for missing date

    @patch("app.tools.TavilyClient")
    def test_empty_results_list_is_valid(self, mock_client_cls):
        """
        Tavily may legitimately return zero results for an obscure query.
        This is a valid (not erroneous) response — we return [].
        """
        mock_client_cls.return_value.search.return_value = _make_tavily_response([])
        results = web_search("xkcd1234obscure")
        assert results == []

    @patch("app.tools.TavilyClient")
    def test_client_receives_correct_arguments(self, mock_client_cls):
        """Verify we pass query and max_results correctly to the SDK."""
        mock_instance = mock_client_cls.return_value
        mock_instance.search.return_value = _make_tavily_response([])

        web_search("Tesla revenue", max_results=7)

        mock_instance.search.assert_called_once_with(
            query="Tesla revenue",
            max_results=7,
            search_depth="basic",
        )

    @patch("app.tools.TavilyClient")
    def test_query_is_stripped_before_sending(self, mock_client_cls):
        """Leading/trailing whitespace in the query is stripped."""
        mock_instance = mock_client_cls.return_value
        mock_instance.search.return_value = _make_tavily_response([])

        web_search("  padded query  ")

        call_kwargs = mock_instance.search.call_args
        assert call_kwargs.kwargs["query"] == "padded query"


# ── Input validation tests ────────────────────────────────────────────────────

class TestWebSearchInputValidation:
    """Tests that bad arguments raise ValueError before any API call is made."""

    def test_empty_query_raises_value_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            web_search("")

    def test_whitespace_only_query_raises_value_error(self):
        with pytest.raises(ValueError, match="non-empty"):
            web_search("   ")

    def test_non_string_query_raises_value_error(self):
        with pytest.raises(ValueError):
            web_search(123)  # type: ignore[arg-type]

    def test_max_results_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="max_results"):
            web_search("valid query", max_results=0)

    def test_max_results_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="max_results"):
            web_search("valid query", max_results=-1)

    def test_max_results_above_20_raises_value_error(self):
        with pytest.raises(ValueError, match="max_results"):
            web_search("valid query", max_results=21)

    def test_max_results_non_integer_raises_value_error(self):
        with pytest.raises(ValueError, match="max_results"):
            web_search("valid query", max_results=3.5)  # type: ignore[arg-type]


# ── Missing credentials test ──────────────────────────────────────────────────

class TestWebSearchCredentials:
    """Tests for missing or invalid API key handling."""

    def test_missing_api_key_raises_configuration_error(self, monkeypatch):
        """If TAVILY_API_KEY is absent, raise ToolConfigurationError immediately."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with pytest.raises(ToolConfigurationError, match="TAVILY_API_KEY"):
            web_search("any query")

    def test_placeholder_api_key_raises_configuration_error(self, monkeypatch):
        """The literal placeholder value should be treated as absent."""
        monkeypatch.setenv("TAVILY_API_KEY", "your_tavily_key_here")
        with pytest.raises(ToolConfigurationError):
            web_search("any query")


# ── Exception mapping tests ───────────────────────────────────────────────────

class TestWebSearchExceptionMapping:
    """
    Tests that each Tavily SDK exception is translated to our custom type.

    Design: we patch TavilyClient.search to raise each SDK exception,
    then verify that web_search raises the corresponding ToolError subclass.
    We also confirm the original exception is chained (__cause__) so that
    debugging tools can still inspect the root cause.
    """

    @patch("app.tools.TavilyClient")
    def test_invalid_api_key_maps_to_authentication_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = InvalidAPIKeyError("bad key")
        with pytest.raises(ToolAuthenticationError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_forbidden_maps_to_authentication_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = ForbiddenError("forbidden")
        with pytest.raises(ToolAuthenticationError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_usage_limit_maps_to_rate_limit_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = UsageLimitExceededError("limit")
        with pytest.raises(ToolRateLimitError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_bad_request_maps_to_request_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = BadRequestError("bad request")
        with pytest.raises(ToolRequestError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_timeout_maps_to_network_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = TavilyTimeoutError(30.0)
        with pytest.raises(ToolNetworkError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_missing_api_key_from_sdk_maps_to_config_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = MissingAPIKeyError()
        with pytest.raises(ToolConfigurationError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_generic_exception_maps_to_tool_error(self, mock_client_cls):
        mock_client_cls.return_value.search.side_effect = RuntimeError("unexpected!")
        with pytest.raises(ToolError):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_original_exception_is_chained(self, mock_client_cls):
        """
        The original SDK exception must be the __cause__ of our ToolError.
        This preserves the full traceback for debugging.
        """
        original = InvalidAPIKeyError("original")
        mock_client_cls.return_value.search.side_effect = original
        with pytest.raises(ToolAuthenticationError) as exc_info:
            web_search("query")
        assert exc_info.value.__cause__ is original


# ── Malformed response tests ──────────────────────────────────────────────────

class TestWebSearchMalformedResponse:
    """Tests that a structurally wrong API response raises ToolError."""

    @patch("app.tools.TavilyClient")
    def test_missing_results_key_raises_tool_error(self, mock_client_cls):
        """If 'results' key is absent, raise ToolError rather than KeyError."""
        mock_client_cls.return_value.search.return_value = {"query": "x"}
        with pytest.raises(ToolError, match="unexpected response shape"):
            web_search("query")

    @patch("app.tools.TavilyClient")
    def test_results_not_a_list_raises_tool_error(self, mock_client_cls):
        """If 'results' is not a list (e.g. a string), raise ToolError."""
        mock_client_cls.return_value.search.return_value = {
            "query": "x",
            "results": "not a list",
        }
        with pytest.raises(ToolError, match="unexpected response shape"):
            web_search("query")
