import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.database_summarizer import DatabaseSummarizer  # noqa: E402


class _FakeSummarizer:
    def __init__(self, output: str):
        self.output = output

    async def generate(self, prompt: str):
        return self.output, "fake-key"


def test_summarize_fact_entries_parses_and_dedupes():
    async def _run():
        summarizer = DatabaseSummarizer(
            summarizer=_FakeSummarizer("- likes tea\n- likes tea\n* likes cats")
        )
        result = await summarizer.summarize_fact_entries(["likes coffee"], "likes tea")
        assert result == ["likes tea", "likes cats"]

    asyncio.run(_run())


def test_summarize_attributes_parses_pairs():
    async def _run():
        summarizer = DatabaseSummarizer(
            summarizer=_FakeSummarizer("- tone = playful\n- style = warm")
        )
        result = await summarizer.summarize_attributes([], "tone", "playful")
        assert result == [("tone", "playful"), ("style", "warm")]

    asyncio.run(_run())


def test_summarize_sample_dialogues_parses_pairs():
    async def _run():
        summarizer = DatabaseSummarizer(
            summarizer=_FakeSummarizer("- femmy || hello\n- yumi || ara ara")
        )
        result = await summarizer.summarize_sample_dialogues([], "femmy", "hello")
        assert result == [("femmy", "hello"), ("yumi", "ara ara")]

    asyncio.run(_run())
