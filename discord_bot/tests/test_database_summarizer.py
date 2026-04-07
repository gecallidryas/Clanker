import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "/mnt/e/femboibot/discord_bot")

from utils.database_summarizer import DatabaseSummarizer


class _FakeSummarizer:
    async def generate(self, prompt: str) -> tuple[str, str]:
        return "- likes tea\n- enjoys coding\n- likes tea\n", "fake"


class DatabaseSummarizerTests(unittest.IsolatedAsyncioTestCase):
    async def test_summarize_fact_entries_parses_bulleted_unique_lines(self) -> None:
        summarizer = DatabaseSummarizer(summarizer=_FakeSummarizer())

        result = await summarizer.summarize_fact_entries(
            existing=["likes coffee"],
            new_entry="likes tea",
            scope_label="user memory",
        )

        self.assertEqual(result, ["likes tea", "enjoys coding"])

    async def test_init_disables_summarizer_when_manager_is_unavailable(self) -> None:
        with patch("utils.database_summarizer.get_gemini_summarize_manager", side_effect=ValueError("missing key")):
            summarizer = DatabaseSummarizer()

        self.assertIsNone(summarizer.summarizer)


if __name__ == "__main__":
    unittest.main()
