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
from utils.db_handler import get_welcome_config


class _FakeBot:
    user = SimpleNamespace(id=999)


class _FakeGuild:
    def __init__(self):
        self.id = 123
        self.name = "Test Guild"
        self.member_count = 42
        self.channels = {}

    def get_role(self, _role_id: int):
        return None

    def get_channel(self, channel_id: int):
        return self.channels.get(channel_id)


class _FakeChannel:
    def __init__(self):
        self.send = AsyncMock()


class _FakeMember:
    def __init__(self):
        self.guild = _FakeGuild()
        self.display_name = "New User"
        self.mention = "@new-user"
        self.add_roles = AsyncMock()
        self.send = AsyncMock()
        self.display_avatar = SimpleNamespace(read=AsyncMock(return_value=b"avatar-bytes"))


class SocialWelcomeDmTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_welcome_config_defaults_dm_petpet_off(self):
        with patch(
            "utils.db_handler.get_guild_config",
            AsyncMock(
                return_value={
                    "welcome_channel_id": None,
                    "welcome_enabled": 1,
                    "welcome_message_template": "Welcome!",
                    "dm_welcome_enabled": 0,
                }
            ),
        ):
            config = await get_welcome_config(123)

        self.assertIn("dm_welcome_petpet_enabled", config)
        self.assertIn("dm_welcome_enabled", config)
        self.assertFalse(config["dm_welcome_enabled"])
        self.assertFalse(config["dm_welcome_petpet_enabled"])

    def test_apply_welcome_template_replaces_user_alias(self):
        cog = Social(_FakeBot())
        member = _FakeMember()

        rendered = cog._apply_welcome_template("@user welcome to the batcave!", member, 42)

        self.assertEqual(rendered, "@new-user welcome to the batcave!")

    def test_apply_welcome_template_preserves_existing_placeholders(self):
        cog = Social(_FakeBot())
        member = _FakeMember()

        rendered = cog._apply_welcome_template(
            "{member} | {member_name} | {member_count} | {member_ordinal} | {guild}",
            member,
            42,
        )

        self.assertEqual(rendered, "@new-user | New User | 42 | 42nd | Test Guild")

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
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_petpet_enabled",
            AsyncMock(return_value=False),
        ):
            await cog.on_member_join(member)

        member.send.assert_awaited_once_with("Welcome to the server!")

    async def test_dm_welcome_sends_petpet_attachment_when_enabled(self):
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
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_petpet_enabled",
            AsyncMock(return_value=True),
        ), patch(
            "discord_bot.cogs.social.make_petpet",
            return_value=b"GIF89a-test",
            create=True,
        ):
            await cog.on_member_join(member)

        args, kwargs = member.send.await_args
        self.assertEqual(args[0], "Welcome to the server!")
        self.assertIn("file", kwargs)
        self.assertEqual(kwargs["file"].filename, "petpet.gif")

    async def test_dm_welcome_still_sends_text_when_petpet_generation_fails(self):
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
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_petpet_enabled",
            AsyncMock(return_value=True),
        ), patch(
            "discord_bot.cogs.social.make_petpet",
            side_effect=RuntimeError("petpet failed"),
            create=True,
        ) as make_petpet:
            await cog.on_member_join(member)

        make_petpet.assert_called_once()
        member.send.assert_awaited_once_with("Welcome to the server!")

    async def test_public_welcome_sends_petpet_attachment(self):
        cog = Social(_FakeBot())
        member = _FakeMember()
        channel = _FakeChannel()
        member.guild.channels[555] = channel

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_enabled": 1,
                    "welcome_channel_id": 555,
                    "welcome_message_template": "@user welcome to the batcave!",
                    "dm_welcome_enabled": 0,
                    "dm_welcome_petpet_enabled": 0,
                }
            ),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_message",
            AsyncMock(return_value=None),
        ), patch(
            "discord_bot.cogs.social.make_petpet",
            return_value=b"GIF89a-test",
            create=True,
        ):
            await cog.on_member_join(member)

        args, kwargs = channel.send.await_args
        self.assertEqual(args[0], "@new-user welcome to the batcave! You are the 42nd member to join~")
        self.assertIn("file", kwargs)
        self.assertEqual(kwargs["file"].filename, "petpet.gif")
        self.assertTrue(kwargs["allowed_mentions"].users)
        self.assertFalse(kwargs["allowed_mentions"].roles)
        self.assertFalse(kwargs["allowed_mentions"].everyone)

    async def test_public_welcome_skips_petpet_when_generation_fails(self):
        cog = Social(_FakeBot())
        member = _FakeMember()
        channel = _FakeChannel()
        member.guild.channels[555] = channel

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_enabled": 1,
                    "welcome_channel_id": 555,
                    "welcome_message_template": "@user welcome to the batcave!",
                    "dm_welcome_enabled": 0,
                    "dm_welcome_petpet_enabled": 0,
                }
            ),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_message",
            AsyncMock(return_value=None),
        ), patch(
            "discord_bot.cogs.social.make_petpet",
            side_effect=RuntimeError("petpet failed"),
            create=True,
        ):
            await cog.on_member_join(member)

        args, kwargs = channel.send.await_args
        self.assertEqual(args[0], "@new-user welcome to the batcave! You are the 42nd member to join~")
        self.assertNotIn("file", kwargs)
        self.assertTrue(kwargs["allowed_mentions"].users)
        self.assertFalse(kwargs["allowed_mentions"].roles)
        self.assertFalse(kwargs["allowed_mentions"].everyone)

    async def test_public_welcome_skips_petpet_when_avatar_fetch_fails(self):
        cog = Social(_FakeBot())
        member = _FakeMember()
        member.display_avatar.read = AsyncMock(side_effect=RuntimeError("avatar failed"))
        channel = _FakeChannel()
        member.guild.channels[555] = channel

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_enabled": 1,
                    "welcome_channel_id": 555,
                    "welcome_message_template": "@user welcome to the batcave!",
                    "dm_welcome_enabled": 0,
                    "dm_welcome_petpet_enabled": 0,
                }
            ),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_message",
            AsyncMock(return_value=None),
        ):
            await cog.on_member_join(member)

        args, kwargs = channel.send.await_args
        self.assertEqual(args[0], "@new-user welcome to the batcave! You are the 42nd member to join~")
        self.assertNotIn("file", kwargs)
        self.assertTrue(kwargs["allowed_mentions"].users)
        self.assertFalse(kwargs["allowed_mentions"].roles)
        self.assertFalse(kwargs["allowed_mentions"].everyone)


if __name__ == "__main__":
    unittest.main()
