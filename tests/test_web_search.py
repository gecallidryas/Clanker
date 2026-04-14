import json
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import web_search

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "gemini_grounding_response.json"


def _namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


def _web_chunk(url, title=None, domain=None):
    return SimpleNamespace(web=SimpleNamespace(uri=url, title=title, domain=domain))


def _support(text, chunk_indices):
    return SimpleNamespace(
        segment=SimpleNamespace(text=text),
        grounding_chunk_indices=chunk_indices,
    )


def _metadata(chunks=None, supports=None):
    return SimpleNamespace(
        grounding_chunks=chunks,
        grounding_supports=supports,
    )


def _candidate(metadata):
    return SimpleNamespace(grounding_metadata=metadata)


def _candidate_without_metadata():
    return SimpleNamespace()


def _response(candidates):
    return SimpleNamespace(candidates=candidates)


class WebSearchTests(unittest.IsolatedAsyncioTestCase):
    def _make_context(self):
        return ToolContext(
            bot=object(),
            guild=mock.Mock(id=123),
            channel=mock.Mock(),
            user=mock.Mock(),
            message=None,
            guild_config={},
            locale="en",
        )

    def test_format_results_emits_numbered_markdown_links(self):
        formatted = web_search._format_results(
            [{"title": "Example", "url": "https://example.com", "snippet": "Snippet"}]
        )

        self.assertEqual(formatted, "1. [Example](https://example.com)\nSnippet")

    def test_gemini_fixture_contract_extracts_normalized_results(self):
        with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        response = _namespace(payload)
        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Example Gemini Grounding Article",
                    "url": "https://example.com/articles/gemini-grounding",
                    "snippet": (
                        "Example Gemini Grounding Article explains how grounded results are "
                        "attached to search sources."
                    ),
                },
                {
                    "title": "Google Search in Gemini",
                    "url": "https://developers.googleblog.com/google-search",
                    "snippet": (
                        "Google Search in Gemini demonstrates the google_search tool shape "
                        "and grounding metadata."
                    ),
                },
            ],
        )

    def test_extract_gemini_results_skips_candidates_without_grounding_metadata(self):
        response = _response(
            [
                _candidate_without_metadata(),
                _candidate(
                    _metadata(
                        chunks=[
                            _web_chunk(
                                "https://example.com/articles/gemini-grounding",
                                title="Example Gemini Grounding Article",
                            )
                        ],
                        supports=[_support(" Example snippet ", [0])],
                    )
                ),
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Example Gemini Grounding Article",
                    "url": "https://example.com/articles/gemini-grounding",
                    "snippet": "Example snippet",
                }
            ],
        )

    def test_extract_gemini_results_skips_empty_metadata_before_valid_candidate(self):
        response = _response(
            [
                _candidate(_metadata(chunks=[], supports=[_support("Ignored", [0])])),
                _candidate(
                    _metadata(
                        chunks=[
                            _web_chunk(
                                "https://example.com/articles/gemini-grounding",
                                title="Example Gemini Grounding Article",
                            )
                        ],
                        supports=[_support(" Example snippet ", [0])],
                    )
                ),
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Example Gemini Grounding Article",
                    "url": "https://example.com/articles/gemini-grounding",
                    "snippet": "Example snippet",
                }
            ],
        )

    def test_extract_gemini_results_skips_malformed_chunks_before_valid_candidate(self):
        response = _response(
            [
                _candidate(
                    _metadata(
                        chunks=[SimpleNamespace(web=SimpleNamespace(uri=""))],
                        supports=[_support("Ignored", [0])],
                    )
                ),
                _candidate(
                    _metadata(
                        chunks=[
                            _web_chunk(
                                "https://example.com/articles/gemini-grounding",
                                title="Example Gemini Grounding Article",
                            )
                        ],
                        supports=[_support(" Example snippet ", [0])],
                    )
                ),
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Example Gemini Grounding Article",
                    "url": "https://example.com/articles/gemini-grounding",
                    "snippet": "Example snippet",
                }
            ],
        )

    def test_extract_gemini_results_handles_missing_grounding_supports(self):
        response = _response(
            [
                _candidate(
                    _metadata(
                        chunks=[
                            _web_chunk(
                                "https://example.com/articles/gemini-grounding",
                                title="Example Gemini Grounding Article",
                            )
                        ],
                        supports=None,
                    )
                )
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Example Gemini Grounding Article",
                    "url": "https://example.com/articles/gemini-grounding",
                    "snippet": "",
                }
            ],
        )

    def test_extract_gemini_results_falls_back_to_domain_text_when_title_missing(self):
        response = _response(
            [
                _candidate(
                    _metadata(
                        chunks=[_web_chunk("https://news.example.com/story", title=None)],
                        supports=None,
                    )
                )
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "news.example.com",
                    "url": "https://news.example.com/story",
                    "snippet": "",
                }
            ],
        )

    def test_extract_gemini_results_deduplicates_duplicate_urls_and_merges_snippets(self):
        response = _response(
            [
                _candidate(
                    _metadata(
                        chunks=[
                            _web_chunk("https://example.com/story", title=None),
                            _web_chunk(
                                "https://example.com/story",
                                title="Canonical story",
                            ),
                        ],
                        supports=[
                            _support(" Second snippet ", [1]),
                            _support(" First snippet ", [0]),
                        ],
                    )
                )
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Canonical story",
                    "url": "https://example.com/story",
                    "snippet": "First snippet Second snippet",
                }
            ],
        )

    def test_extract_gemini_results_keeps_single_snippet_for_multiple_chunk_indices(self):
        response = _response(
            [
                _candidate(
                    _metadata(
                        chunks=[
                            _web_chunk("https://example.com/story", title="Story"),
                            _web_chunk("https://example.com/story", title="Story"),
                        ],
                        supports=[_support(" Shared snippet ", [0, 1])],
                    )
                )
            ]
        )

        results = web_search._extract_gemini_results(response, max_results=5)

        self.assertEqual(
            results,
            [
                {
                    "title": "Story",
                    "url": "https://example.com/story",
                    "snippet": "Shared snippet",
                }
            ],
        )

    async def test_web_search_prefers_gemini_when_configured(self):
        async def fake_gemini_search(query, api_keys, model, max_results=5):
            self.assertEqual(query, "test")
            self.assertEqual(api_keys, ["gem-key"])
            self.assertEqual(model, "gemini-2.5-flash")
            return [{"title": "Gemini Result", "url": "https://gemini.example", "snippet": "Snippet"}]

        with (
            mock.patch.object(
                web_search,
                "_get_gemini_search_config",
                new=mock.AsyncMock(return_value=(["gem-key"], "gemini-2.5-flash")),
            ),
            mock.patch.object(web_search, "gemini_search", new=fake_gemini_search),
            mock.patch.object(web_search, "_get_brave_key", new=mock.AsyncMock(return_value="brave-key")),
            mock.patch.object(web_search, "brave_search", new=mock.AsyncMock()),
            mock.patch.object(web_search, "duckduckgo_search", new=mock.AsyncMock()),
        ):
            result = await web_search._handle_web_search(self._make_context(), {"query": "test"})

        self.assertTrue(result.ok)
        self.assertEqual(result.data.get("provider"), "gemini")
        self.assertEqual(result.data.get("results")[0]["url"], "https://gemini.example")

    async def test_web_search_falls_back_to_brave_when_gemini_search_unavailable(self):
        async def fake_brave_search(query, api_key, max_results=5):
            self.assertEqual(query, "test")
            self.assertEqual(api_key, "brave-key")
            return [{"title": "Brave Result", "url": "https://brave.example", "snippet": "Snippet"}]

        with (
            mock.patch.object(
                web_search,
                "_get_gemini_search_config",
                new=mock.AsyncMock(return_value=(["gem-key"], "gemini-2.5-flash")),
            ),
            mock.patch.object(web_search, "gemini_search", new=mock.AsyncMock(return_value=None)),
            mock.patch.object(web_search, "_get_brave_key", new=mock.AsyncMock(return_value="brave-key")),
            mock.patch.object(web_search, "brave_search", new=fake_brave_search),
            mock.patch.object(web_search, "duckduckgo_search", new=mock.AsyncMock()),
        ):
            result = await web_search._handle_web_search(self._make_context(), {"query": "test"})

        self.assertTrue(result.ok)
        self.assertEqual(result.data.get("provider"), "brave")
        self.assertEqual(result.data.get("results")[0]["url"], "https://brave.example")

    async def test_web_search_falls_back_to_brave_when_gemini_returns_no_usable_results(self):
        async def fake_brave_search(query, api_key, max_results=5):
            self.assertEqual(query, "test")
            self.assertEqual(api_key, "brave-key")
            return [{"title": "Brave Result", "url": "https://brave.example", "snippet": "Snippet"}]

        with (
            mock.patch.object(
                web_search,
                "_get_gemini_search_config",
                new=mock.AsyncMock(return_value=(["gem-key"], "gemini-2.5-flash")),
            ),
            mock.patch.object(web_search, "gemini_search", new=mock.AsyncMock(return_value=[])),
            mock.patch.object(web_search, "_get_brave_key", new=mock.AsyncMock(return_value="brave-key")),
            mock.patch.object(web_search, "brave_search", new=fake_brave_search),
            mock.patch.object(web_search, "duckduckgo_search", new=mock.AsyncMock()),
        ):
            result = await web_search._handle_web_search(self._make_context(), {"query": "test"})

        self.assertTrue(result.ok)
        self.assertEqual(result.data.get("provider"), "brave")
        self.assertEqual(result.data.get("results")[0]["url"], "https://brave.example")

    async def test_web_search_uses_duckduckgo_only_when_higher_priority_providers_unavailable(self):
        async def fake_ddg(query, max_results=5):
            return [{"title": "Result", "url": "https://example.com", "snippet": "Snippet"}]

        with (
            mock.patch.object(web_search, "_get_gemini_search_config", new=mock.AsyncMock(return_value=None)),
            mock.patch.object(web_search, "duckduckgo_search", new=fake_ddg),
            mock.patch.object(web_search, "_get_brave_key", new=mock.AsyncMock(return_value=None)),
        ):
            result = await web_search._handle_web_search(self._make_context(), {"query": "test"})

        self.assertTrue(result.ok)
        self.assertEqual(result.data.get("provider"), "duckduckgo")
        self.assertIn("formatted", result.data)

    async def test_fetch_url_returns_content(self):
        async def fake_fetch(url):
            return "content"

        with mock.patch.object(web_search, "fetch_url_text", new=fake_fetch):
            result = await web_search._handle_fetch_url(self._make_context(), {"url": "https://example.com"})

        self.assertTrue(result.ok)
        self.assertIn("content", result.data)


if __name__ == "__main__":
    unittest.main()
