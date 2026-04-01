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

    async def test_web_search_uses_duckduckgo(self):
        async def fake_ddg(query, max_results=5):
            return [{"title": "Result", "url": "https://example.com", "snippet": "Snippet"}]

        with mock.patch.object(web_search, "duckduckgo_search", new=fake_ddg), \
            mock.patch.object(web_search, "_get_brave_key", new=mock.AsyncMock(return_value=None)):
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
