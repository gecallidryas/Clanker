import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.tool_context import ToolContext
from utils import youtube


class YouTubeToolTests(unittest.IsolatedAsyncioTestCase):
    def _make_context(self):
        return ToolContext(
            bot=object(),
            guild=mock.Mock(id=123),
            channel=mock.Mock(),
            user=mock.Mock(),
            message=None,
            guild_config={},
            locale="en",
        )

    async def test_process_youtube(self):
        with mock.patch.object(youtube, "extract_video_id", return_value="abc123def45"), \
            mock.patch.object(youtube, "_fetch_metadata", return_value={"title": "Video"}), \
            mock.patch.object(youtube, "_fetch_transcript", return_value="hello world"):
            result = await youtube._handle_process_youtube(
                self._make_context(),
                {"youtube_url": "https://youtube.com/watch?v=abc123def45"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.data.get("video_id"), "abc123def45")


if __name__ == "__main__":
    unittest.main()
