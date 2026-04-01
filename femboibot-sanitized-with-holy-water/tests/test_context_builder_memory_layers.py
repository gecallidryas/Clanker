import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.context_builder import build_memory_context_sections  # noqa: E402


class ContextBuilderMemoryLayerTests(unittest.TestCase):
    def test_memory_sections_follow_plan_order_and_filter_empty_layers(self):
        sections = build_memory_context_sections(
            server_memory=["Server norm"],
            current_user_memory=["Current user pref"],
            mentioned_user_memory=["Mentioned user pref"],
            channel_summary=["Channel summary"],
            guild_summary=["Guild summary"],
            rag_chunks=["Chunk A"],
            conversation_timeline="Recent messages",
        )
        titles = [section.title for section in sections]
        self.assertEqual(
            titles,
            [
                "SERVER MEMORY",
                "CURRENT USER PERSONAL MEMORY",
                "MENTIONED USER PERSONAL MEMORY",
                "SHORT-TERM CHANNEL SUMMARY",
                "SHORT-TERM GUILD RECENCY SUMMARY",
                "DOCUMENT RAG CHUNKS",
                "CONVERSATION TIMELINE",
            ],
        )

    def test_guild_summary_is_rendered_after_channel_summary(self):
        sections = build_memory_context_sections(
            channel_summary=["Channel summary"],
            guild_summary=["Guild summary"],
        )
        titles = [section.title for section in sections]
        self.assertLess(
            titles.index("SHORT-TERM CHANNEL SUMMARY"),
            titles.index("SHORT-TERM GUILD RECENCY SUMMARY"),
        )


if __name__ == "__main__":
    unittest.main()
