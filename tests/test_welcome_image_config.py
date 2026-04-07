import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
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

from discord_bot.cogs.config import Config
from discord_bot.utils.welcome_images import WelcomeImagePayload


class _FakeBot:
    user = SimpleNamespace(id=999)


class _FakeAvatar:
    def __init__(self, payload: bytes = b"avatar-bytes"):
        self._payload = payload

    def replace(self, **_kwargs):
        return self

    async def read(self):
        return self._payload


class _FakeChannel:
    def __init__(self):
        self.send = AsyncMock()


class _FakeUser:
    def __init__(self):
        self.id = 111
        self.display_name = "Preview User"
        self.mention = "@preview-user"
        self.display_avatar = _FakeAvatar()
        self.send = AsyncMock()


class _FakeGuild:
    def __init__(self, channels=None):
        self.id = 123
        self.name = "Test Guild"
        self.member_count = 42
        self._channels = channels or {}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeInteraction:
    def __init__(self, guild=None, user=None):
        self.guild = guild or _FakeGuild()
        self.user = user or _FakeUser()
        self.response = SimpleNamespace(send_message=AsyncMock(), is_done=lambda: False)
        self.followup = SimpleNamespace(send=AsyncMock())


class WelcomeImageConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_welcome_image_template_rejects_unknown_template(self):
        interaction = _FakeInteraction()

        with patch("discord_bot.cogs.config.get_encryption", return_value=SimpleNamespace()), patch(
            "discord_bot.cogs.config.set_welcome_image_template",
            AsyncMock(),
        ) as set_template:
            cog = Config(_FakeBot())
            await cog._save_welcome_image_template(interaction, {"template": "unknown-template"})

        set_template.assert_not_awaited()
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.await_args
        self.assertIn("pettinghand", args[0])
        self.assertIn("catmunch", args[0])
        self.assertTrue(kwargs["ephemeral"])

    async def test_send_welcome_image_test_sends_preview_to_specific_channel(self):
        image_channel = _FakeChannel()
        interaction = _FakeInteraction(guild=_FakeGuild(channels={777: image_channel}))
        payload = WelcomeImagePayload(data=b"png-bytes", filename="catmunch.png", content_type="image/png")

        with patch("discord_bot.cogs.config.get_encryption", return_value=SimpleNamespace()), patch(
            "discord_bot.cogs.config.get_welcome_config",
            AsyncMock(
                return_value={
                    "welcome_image_enabled": True,
                    "welcome_image_template": "catmunch",
                    "welcome_image_destination": "specific_channel",
                    "welcome_image_channel_id": 777,
                    "welcome_channel_id": None,
                }
            ),
        ), patch(
            "discord_bot.cogs.config.render_welcome_image",
            return_value=payload,
        ) as render_image:
            cog = Config(_FakeBot())
            await cog._send_welcome_image_test(interaction)

        render_image.assert_called_once()
        image_channel.send.assert_awaited_once()
        _, send_kwargs = image_channel.send.await_args
        self.assertEqual(send_kwargs["file"].filename, "catmunch.png")
        interaction.response.send_message.assert_awaited_once_with("Sent a welcome image preview.", ephemeral=True)


if __name__ == "__main__":
    unittest.main()
