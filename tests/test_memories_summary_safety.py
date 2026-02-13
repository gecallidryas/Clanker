import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs.memories import Memories  # noqa: E402


class _FakeCtx:
    def __init__(self):
        self.guild = SimpleNamespace(id=1)
        self.author = SimpleNamespace(id=10, display_name="Author")
        self.messages: list[str] = []

    async def send(self, message: str):
        self.messages.append(str(message))


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
            display_name="SlashUser",
            guild_permissions=SimpleNamespace(manage_guild=True),
        )
        self.response = _FakeResponse()
        self.followup = _FakeFollowup()


def test_prefix_remember_does_not_delete_when_summary_item_invalid():
    async def _run():
        cog = Memories(bot=None)
        cog._summarize_facts = AsyncMock(return_value=["valid summary", " "])
        ctx = _FakeCtx()
        target = SimpleNamespace(id=99, display_name="Target")
        delete_mock = AsyncMock()
        add_mock = AsyncMock()

        with (
            patch("cogs.memories.create_user", new=AsyncMock()),
            patch("cogs.memories.get_facts", new=AsyncMock(return_value=["old fact"])),
            patch("cogs.memories.delete_facts", new=delete_mock),
            patch("cogs.memories.add_fact", new=add_mock),
        ):
            await cog._remember_fact_for(ctx, target, "new fact")

        delete_mock.assert_not_awaited()
        add_mock.assert_not_awaited()
        assert any("cannot be empty" in msg.lower() for msg in ctx.messages)

    asyncio.run(_run())


def test_slash_remember_does_not_delete_when_summary_item_invalid():
    async def _run():
        cog = Memories(bot=None)
        cog._summarize_facts = AsyncMock(return_value=["valid summary", " "])
        interaction = _FakeInteraction()
        delete_mock = AsyncMock()
        add_mock = AsyncMock()

        with (
            patch("cogs.memories.create_user", new=AsyncMock()),
            patch("cogs.memories.get_facts", new=AsyncMock(return_value=["old fact"])),
            patch("cogs.memories.delete_facts", new=delete_mock),
            patch("cogs.memories.add_fact", new=add_mock),
        ):
            await Memories.remember_fact_slash.callback(cog, interaction, "new fact", None)

        delete_mock.assert_not_awaited()
        add_mock.assert_not_awaited()
        assert any("cannot be empty" in msg.lower() for msg in interaction.followup.messages)

    asyncio.run(_run())


def test_slash_remember_server_does_not_delete_when_summary_item_invalid():
    async def _run():
        cog = Memories(bot=None)
        cog._summarize_facts = AsyncMock(return_value=["valid summary", " "])
        interaction = _FakeInteraction()
        delete_mock = AsyncMock()
        add_server_mock = AsyncMock()

        with (
            patch("cogs.memories.get_server_memory", new=AsyncMock(return_value=["old server fact"])),
            patch("cogs.memories.delete_facts", new=delete_mock),
            patch("cogs.memories.add_server_memory", new=add_server_mock),
        ):
            await Memories.remember_server_slash.callback(cog, interaction, "new server fact")

        delete_mock.assert_not_awaited()
        add_server_mock.assert_not_awaited()
        assert any("cannot be empty" in msg.lower() for msg in interaction.followup.messages)

    asyncio.run(_run())
