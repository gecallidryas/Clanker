import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import expression_tools


class DummyChannel:
    def __init__(self):
        self._message = mock.AsyncMock()
        self._message.add_reaction = mock.AsyncMock()

    async def fetch_message(self, message_id):
        return self._message

    async def send(self, *args, **kwargs):
        return None


class ExpressionToolsTests(unittest.IsolatedAsyncioTestCase):
    def _make_context(self):
        guild = mock.Mock()
        guild.get_channel.return_value = DummyChannel()
        guild.emojis = []
        return ToolContext(
            bot=object(),
            guild=guild,
            channel=DummyChannel(),
            user=mock.Mock(),
            message=None,
            guild_config={},
            locale="en",
        )

    async def test_select_sticker_sends(self):
        context = self._make_context()
        sticker = mock.Mock(name="sticker")
        sticker.name = "cool"
        with mock.patch.object(expression_tools, "pick_sticker", return_value=sticker):
            result = await expression_tools._handle_select_sticker(context, {"query": "cool"})

        self.assertTrue(result.ok)

    async def test_react_with_emoji(self):
        context = self._make_context()
        channel = DummyChannel()
        context.channel = channel
        context.guild.get_channel.return_value = channel

        with mock.patch.object(expression_tools, "pick_emoji", return_value="🙂"), \
            mock.patch.object(expression_tools.discord, "TextChannel", DummyChannel):
            result = await expression_tools._handle_react_with_emoji(
                context,
                {"message_id": 123, "emoji": "smile"},
            )

        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
