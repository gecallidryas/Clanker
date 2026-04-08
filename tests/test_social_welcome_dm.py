import sys
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from PIL import Image

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
from discord_bot.utils.welcome_images import (
    CATMUNCH_SUBTITLE_Y,
    CATMUNCH_TEXT_CENTER_X,
    CATMUNCH_TOP_TEXT_Y,
    WelcomeImagePayload,
    _compute_catmunch_avatar_geometry,
    render_welcome_image,
)


class _FakeBot:
    user = SimpleNamespace(id=999)


class _FakeChannel:
    def __init__(self):
        self.send = AsyncMock()


class _FakeGuild:
    def __init__(self, channels=None):
        self.id = 123
        self.name = "Test Guild"
        self.member_count = 42
        self._channels = channels or {}

    def get_role(self, _role_id: int):
        return None

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeAvatar:
    def __init__(self, payload: bytes = b"avatar-bytes", *, side_effect=None):
        self._payload = payload
        self._side_effect = side_effect

    def replace(self, **_kwargs):
        return self

    async def read(self):
        if self._side_effect:
            value = self._side_effect.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return self._payload


class _FakeMember:
    def __init__(self, guild=None, avatar=None):
        self.guild = guild or _FakeGuild()
        self.display_name = "New User"
        self.mention = "@new-user"
        self.add_roles = AsyncMock()
        self.send = AsyncMock()
        self.display_avatar = avatar or _FakeAvatar()


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

    def test_render_welcome_image_pettinghand_returns_gif_payload(self):
        avatar = Image.new("RGB", (320, 240), "#7ec8ff")
        avatar_buffer = BytesIO()
        avatar.save(avatar_buffer, format="PNG")

        payload = render_welcome_image(
            template="pettinghand",
            avatar_bytes=avatar_buffer.getvalue(),
            member_name="snackuser",
            join_ordinal="42nd",
        )

        self.assertEqual(payload.filename, "pettinghand.gif")
        self.assertEqual(payload.content_type, "image/gif")
        self.assertTrue(payload.data.startswith(b"GIF8"))

    def test_compute_catmunch_avatar_geometry_overscans_and_shifts_top_right(self):
        self.assertEqual(_compute_catmunch_avatar_geometry(), (0, 0, 473))

    def test_catmunch_text_is_centered_to_full_image_and_top_text_moves_up(self):
        self.assertEqual(CATMUNCH_TEXT_CENTER_X, 512)
        self.assertEqual(CATMUNCH_TOP_TEXT_Y, 88)
        self.assertEqual(CATMUNCH_SUBTITLE_Y, 180)

    def test_render_welcome_image_catmunch_returns_png_payload(self):
        avatar = Image.new("RGB", (320, 240), "#7ec8ff")
        avatar_buffer = BytesIO()
        avatar.save(avatar_buffer, format="PNG")

        payload = render_welcome_image(
            template="catmunch",
            avatar_bytes=avatar_buffer.getvalue(),
            member_name="snackuser",
            join_ordinal="42nd",
        )

        self.assertEqual(payload.filename, "catmunch.png")
        self.assertEqual(payload.content_type, "image/png")
        self.assertTrue(payload.data.startswith(b"\x89PNG\r\n\x1a\n"))
        rendered = Image.open(BytesIO(payload.data))
        self.assertEqual(rendered.size, (1024, 933))

    async def test_on_member_join_routes_welcome_image_to_welcome_channel(self):
        cog = Social(_FakeBot())
        welcome_channel = _FakeChannel()
        member = _FakeMember(guild=_FakeGuild(channels={555: welcome_channel}))
        payload = WelcomeImagePayload(data=b"gif-bytes", filename="pettinghand.gif", content_type="image/gif")

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_enabled": 1,
                    "welcome_channel_id": 555,
                    "welcome_message_template": "@new-user welcome to the batcave!",
                    "welcome_image_enabled": True,
                    "welcome_image_template": "pettinghand",
                    "welcome_image_destination": "welcome_channel",
                    "welcome_image_channel_id": None,
                }
            ),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "discord_bot.cogs.social.render_welcome_image",
            return_value=payload,
        ) as render_image:
            await cog.on_member_join(member)

        render_image.assert_called_once()
        self.assertEqual(render_image.call_args.kwargs["template"], "pettinghand")
        self.assertEqual(welcome_channel.send.await_count, 2)
        text_args, _ = welcome_channel.send.await_args_list[0]
        self.assertEqual(text_args[0], "@new-user welcome to the batcave!")
        _, image_kwargs = welcome_channel.send.await_args_list[1]
        self.assertEqual(image_kwargs["file"].filename, "pettinghand.gif")

    async def test_on_member_join_routes_welcome_image_to_specific_channel(self):
        cog = Social(_FakeBot())
        image_channel = _FakeChannel()
        member = _FakeMember(guild=_FakeGuild(channels={777: image_channel}))
        payload = WelcomeImagePayload(data=b"png-bytes", filename="catmunch.png", content_type="image/png")

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_enabled": 0,
                    "welcome_channel_id": None,
                    "welcome_message_template": None,
                    "welcome_image_enabled": True,
                    "welcome_image_template": "catmunch",
                    "welcome_image_destination": "specific_channel",
                    "welcome_image_channel_id": 777,
                }
            ),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "discord_bot.cogs.social.render_welcome_image",
            return_value=payload,
        ) as render_image:
            await cog.on_member_join(member)

        render_image.assert_called_once()
        self.assertEqual(render_image.call_args.kwargs["template"], "catmunch")
        image_channel.send.assert_awaited_once()
        _, image_kwargs = image_channel.send.await_args
        self.assertEqual(image_kwargs["file"].filename, "catmunch.png")

    async def test_on_member_join_routes_welcome_image_to_dm_even_when_dm_text_is_disabled(self):
        cog = Social(_FakeBot())
        member = _FakeMember()
        payload = WelcomeImagePayload(data=b"png-bytes", filename="catmunch.png", content_type="image/png")

        with patch("discord_bot.cogs.social.get_server_mode", AsyncMock(return_value="mode_default")), patch(
            "discord_bot.cogs.social.get_autorole_config",
            AsyncMock(return_value={"autorole_enabled": 0, "autorole_id": None}),
        ), patch(
            "discord_bot.cogs.social.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_enabled": 0,
                    "welcome_channel_id": None,
                    "welcome_message_template": None,
                    "welcome_image_enabled": True,
                    "welcome_image_template": "catmunch",
                    "welcome_image_destination": "dm",
                    "welcome_image_channel_id": None,
                }
            ),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_enabled",
            AsyncMock(return_value=False),
        ), patch(
            "discord_bot.cogs.social.get_dm_welcome_message",
            AsyncMock(return_value=None),
        ), patch(
            "discord_bot.cogs.social.render_welcome_image",
            return_value=payload,
        ) as render_image:
            await cog.on_member_join(member)

        render_image.assert_called_once()
        member.send.assert_awaited_once()
        _, image_kwargs = member.send.await_args
        self.assertEqual(image_kwargs["file"].filename, "catmunch.png")

    async def test_send_welcome_image_retries_avatar_read_after_short_delay(self):
        cog = Social(_FakeBot())
        member = _FakeMember(
            avatar=_FakeAvatar(side_effect=[RuntimeError("cdn not ready"), b"avatar-bytes"]),
        )
        payload = WelcomeImagePayload(data=b"gif-bytes", filename="pettinghand.gif", content_type="image/gif")

        with patch("discord_bot.cogs.social.render_welcome_image", return_value=payload), patch(
            "asyncio.sleep",
            AsyncMock(),
        ) as sleep_mock:
            avatar_bytes = await cog._read_member_avatar_bytes(member)

        self.assertEqual(avatar_bytes, b"avatar-bytes")
        sleep_mock.assert_awaited_once()

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
