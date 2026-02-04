import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import pin_tool


class DummyChannel:
    def __init__(self):
        self._message = mock.AsyncMock()
        self._message.pin = mock.AsyncMock()

    async def fetch_message(self, message_id):
        return self._message

    def permissions_for(self, member):
        return mock.Mock(manage_messages=True)


class DummyMember:
    def __init__(self, manage_messages=True, administrator=False):
        self.guild_permissions = mock.Mock(
            manage_messages=manage_messages,
            administrator=administrator,
        )


class PinToolTests(unittest.IsolatedAsyncioTestCase):
    def _make_context(self):
        channel = DummyChannel()
        guild = mock.Mock()
        guild.get_channel.return_value = channel
        guild.me = DummyMember()
        return ToolContext(
            bot=mock.Mock(user=mock.Mock(id=1)),
            guild=guild,
            channel=channel,
            user=DummyMember(manage_messages=True),
            message=None,
            guild_config={},
            locale="en",
        )

    async def test_pin_message(self):
        context = self._make_context()
        with mock.patch.object(pin_tool.discord, "TextChannel", DummyChannel), \
            mock.patch.object(pin_tool.discord, "Member", DummyMember):
            result = await pin_tool._handle_pin_message(context, {"message_id": 123})

        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
