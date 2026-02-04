import os
import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import image_generation


class ImageGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        os.environ["OPENROUTER_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _make_context(self):
        channel = mock.AsyncMock()
        guild = mock.Mock(id=123)
        return ToolContext(
            bot=object(),
            guild=guild,
            channel=channel,
            user=mock.Mock(),
            message=None,
            guild_config={},
            locale="en",
        )

    async def test_generate_image_sends_file(self):
        context = self._make_context()
        with mock.patch.object(
            image_generation,
            "_resolve_image_provider",
            new=mock.AsyncMock(return_value=("openrouter", None, "model")),
        ), \
            mock.patch.object(
                image_generation,
                "_generate_with_openrouter",
                new=mock.AsyncMock(return_value=b"bytes"),
            ), \
            mock.patch.object(
                image_generation,
                "get_guild_config",
                new=mock.AsyncMock(return_value={}),
            ):
            result = await image_generation._handle_generate_image(context, {"prompt": "a cat"})

        self.assertTrue(result.ok)
        self.assertTrue(context.channel.send.called)


if __name__ == "__main__":
    unittest.main()
