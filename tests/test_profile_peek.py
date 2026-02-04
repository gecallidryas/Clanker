import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import profile_peek


class DummyAvatar:
    async def read(self):
        return b"bytes"


class DummyMember:
    def __init__(self):
        self.id = 123
        self.display_avatar = DummyAvatar()


class ProfilePeekTests(unittest.IsolatedAsyncioTestCase):
    def _make_context(self):
        guild = mock.Mock(id=1)
        return ToolContext(
            bot=object(),
            guild=guild,
            channel=mock.Mock(),
            user=DummyMember(),
            message=None,
            guild_config={},
            locale="en",
        )

    async def test_profile_peek(self):
        context = self._make_context()
        with mock.patch.object(
            profile_peek,
            "generate_guild_gemini_vision",
            new=mock.AsyncMock(return_value=("ok", None)),
        ), \
            mock.patch.object(profile_peek.Image, "open", return_value=mock.Mock()):
            result = await profile_peek._handle_peek_profile_picture(context, {})

        self.assertTrue(result.ok)
        self.assertEqual(result.data.get("analysis"), "ok")


if __name__ == "__main__":
    unittest.main()
