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

from discord_bot.cogs.social import Social
from discord_bot.utils.db_handler import get_welcome_config


class _FakeBot:
    user = SimpleNamespace(id=999)


class _FakeGuild:
    def __init__(self):
        self.id = 123
        self.name = "Test Guild"
        self.member_count = 42

    def get_role(self, _role_id: int):
        return None

    def get_channel(self, _channel_id: int):
        return None


class _FakeMember:
    def __init__(self):
        self.guild = _FakeGuild()
        self.display_name = "New User"
        self.mention = "@new-user"
        self.add_roles = AsyncMock()
        self.send = AsyncMock()


class SocialWelcomeDmTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_welcome_config_defaults_include_welcome_image_settings(self):
        with patch("discord_bot.utils.db_handler.get_guild_config", AsyncMock(return_value={})):
            config = await get_welcome_config(123)

        self.assertEqual(
            config,
            {
                "welcome_channel_id": None,
                "welcome_enabled": True,
                "welcome_message_template": None,
                "welcome_image_enabled": False,
                "welcome_image_template": "pettinghand",
                "welcome_image_destination": "welcome_channel",
                "welcome_image_channel_id": None,
            },
        )

    async def test_dm_welcome_sends_plain_text_message(self):
        cog = Social(_FakeBot())
        member = _FakeMember()

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(return_value={"welcome_enabled": 0, "welcome_channel_id": None, "welcome_message_template": None}),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=True),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_message",
            AsyncMock(return_value="Welcome to the server!"),
        ):
            await cog.on_member_join(member)

        member.send.assert_awaited_once_with("Welcome to the server!")


if __name__ == "__main__":
    unittest.main()
