import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs.teach import Teach  # noqa: E402


class _FakeResponse:
    def __init__(self):
        self.deferred = False
        self.messages: list[str] = []

    async def defer(self, thinking: bool = False, ephemeral: bool = False):
        self.deferred = True

    async def send_message(self, message: str, ephemeral: bool = False):
        self.messages.append(str(message))


class _FakeFollowup:
    def __init__(self):
        self.messages: list[str] = []

    async def send(self, message: str, ephemeral: bool = False):
        self.messages.append(str(message))


class _FakeInteraction:
    def __init__(self):
        self.guild = SimpleNamespace(id=1)
        self.user = SimpleNamespace(
            id=20,
            guild_permissions=SimpleNamespace(manage_guild=True),
        )
        self.response = _FakeResponse()
        self.followup = _FakeFollowup()


def test_teach_attribute_does_not_replace_when_summary_item_invalid():
    async def _run():
        cog = Teach(bot=None)
        interaction = _FakeInteraction()
        cog.db_summarizer.summarize_attributes = AsyncMock(
            return_value=[("tone", "friendly"), ("", "invalid")]
        )
        replace_mock = AsyncMock()
        add_mock = AsyncMock()

        with (
            patch("cogs.teach.get_persona_attributes", new=AsyncMock(return_value=[{"attribute": "tone", "value": "rude"}])),
            patch("cogs.teach.replace_persona_attributes", new=replace_mock),
            patch("cogs.teach.add_persona_attribute", new=add_mock),
        ):
            await Teach.teach_attribute.callback(cog, interaction, "tone", "friendly")

        replace_mock.assert_not_awaited()
        add_mock.assert_not_awaited()
        assert any("cannot be empty" in msg.lower() for msg in interaction.followup.messages)

    asyncio.run(_run())


def test_teach_sampledialogue_does_not_replace_when_summary_item_invalid():
    async def _run():
        cog = Teach(bot=None)
        interaction = _FakeInteraction()
        cog.db_summarizer.summarize_sample_dialogues = AsyncMock(
            return_value=[("femmy", "hello there"), ("femmy", " ")]
        )
        replace_mock = AsyncMock()
        add_mock = AsyncMock()

        with (
            patch("cogs.teach.get_sample_dialogues", new=AsyncMock(return_value=[{"speaker": "femmy", "dialogue": "hi"}])),
            patch("cogs.teach.replace_sample_dialogues", new=replace_mock),
            patch("cogs.teach.add_sample_dialogue", new=add_mock),
        ):
            await Teach.teach_sampledialogue.callback(cog, interaction, "femmy", "hello there")

        replace_mock.assert_not_awaited()
        add_mock.assert_not_awaited()
        assert any("cannot be empty" in msg.lower() for msg in interaction.followup.messages)

    asyncio.run(_run())
