import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from utils.streaming.discord_sender import DiscordReplySession


class DiscordReplySessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_visible_output_callback_fires_once_on_first_chunk(self) -> None:
        source_message = SimpleNamespace(
            reply=AsyncMock(return_value=SimpleNamespace(content="hello")),
            channel=SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(content="world"))),
        )
        callback = AsyncMock()
        session = DiscordReplySession(
            source_message=source_message,
            on_visible_output=callback,
        )

        await session.send_text("hello")
        await session.send_text("world")

        self.assertEqual(callback.await_count, 1)


if __name__ == "__main__":
    unittest.main()
