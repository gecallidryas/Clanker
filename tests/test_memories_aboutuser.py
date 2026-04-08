import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))
sys.path.insert(0, str(ROOT))

sys.modules.setdefault(
    "bcrypt",
    SimpleNamespace(
        gensalt=lambda *args, **kwargs: b"salt",
        hashpw=lambda value, salt: b"hash",
        checkpw=lambda value, hashed: True,
    ),
)

from discord_bot.cogs.memories import Memories


class _FakeCtx:
    def __init__(self):
        self.guild = SimpleNamespace(id=123)
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append({"content": content, **kwargs})


class _FakeInteraction:
    def __init__(self):
        self.guild = SimpleNamespace(id=123)
        self.response = SimpleNamespace(send_message=AsyncMock())


class MemoriesAboutUserTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefix_aboutuser_reports_lookup_disabled_when_facts_exist(self):
        cog = Memories(bot=None)
        ctx = _FakeCtx()
        member = SimpleNamespace(id=55, display_name="Alias User")

        with patch(
            "discord_bot.cogs.memories.get_personal_memories",
            AsyncMock(return_value=["likes coffee"]),
        ), patch(
            "discord_bot.cogs.memories.get_mention_lookup_personal_memories",
            AsyncMock(return_value=[]),
        ):
            await Memories.about_user.callback(cog, ctx, member)

        self.assertIn("lookup is disabled", ctx.sent[-1]["content"].lower())

    async def test_slash_aboutuser_reports_lookup_disabled_when_facts_exist(self):
        cog = Memories(bot=None)
        interaction = _FakeInteraction()
        member = SimpleNamespace(id=55, display_name="Alias User")

        with patch(
            "discord_bot.cogs.memories.get_personal_memories",
            AsyncMock(return_value=["likes coffee"]),
        ), patch(
            "discord_bot.cogs.memories.get_mention_lookup_personal_memories",
            AsyncMock(return_value=[]),
        ):
            await Memories.about_user_slash.callback(cog, interaction, member)

        args, kwargs = interaction.response.send_message.await_args
        self.assertIn("lookup is disabled", args[0].lower())
        self.assertTrue(kwargs["ephemeral"])


if __name__ == "__main__":
    unittest.main()
