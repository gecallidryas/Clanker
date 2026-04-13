import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import web_search


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
