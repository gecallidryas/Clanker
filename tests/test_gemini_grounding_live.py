from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class LiveGeminiGroundingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        super().setUp()
        if os.getenv("RUN_LIVE_GEMINI_GROUNDING") != "1":
            self.skipTest("Set RUN_LIVE_GEMINI_GROUNDING=1 to run the live Gemini grounding test.")

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            for index in range(1, 11):
                self.api_key = os.getenv(f"GEMINI_API_KEY_{index}")
                if self.api_key:
                    break
        if not self.api_key:
            self.skipTest("A Gemini API key is required to run the live Gemini grounding test.")

        self.web_search = importlib.import_module("utils.web_search")
        if self.web_search.genai is None or self.web_search.genai_types is None:
            self.skipTest("google-genai is not installed.")

        self.model = os.getenv("GEMINI_LIVE_MODEL") or "gemini-2.5-flash"
        self.query = os.getenv(
            "GEMINI_LIVE_QUERY",
            "Gemini google_search grounding example",
        )

    async def test_live_gemini_grounding_returns_normalized_results(self) -> None:
        self.web_search.clear_search_cache(provider="gemini", query=self.query)

        results = await self.web_search.gemini_search(
            self.query,
            [self.api_key],
            self.model,
            max_results=3,
        )

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        for item in results:
            self.assertIsInstance(item, dict)
            self.assertIn("title", item)
            self.assertIn("url", item)
            self.assertIn("snippet", item)
            self.assertIsInstance(item["title"], str)
            self.assertTrue(item["title"].strip())
            self.assertIsInstance(item["url"], str)
            self.assertTrue(item["url"].strip())
            self.assertTrue(item["url"].startswith(("http://", "https://")))
            self.assertIsInstance(item["snippet"], str)


if __name__ == "__main__":
    unittest.main()
