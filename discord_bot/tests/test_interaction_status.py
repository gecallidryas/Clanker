import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import sys

sys.modules.setdefault(
    "psutil",
    SimpleNamespace(Process=lambda: SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=128 * 1024 * 1024))),
)

from cogs.utilities import Utilities
from utils.interaction_status import get_mode_display_name


class InteractionStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_mode_display_name_uses_builtin_names(self) -> None:
        self.assertEqual(await get_mode_display_name(None, "mode_default"), "Clanker")
        self.assertEqual(await get_mode_display_name(None, "mode_femboy"), "Femmy")
        self.assertEqual(await get_mode_display_name(None, "mode_tsundere"), "Femmy")
        self.assertEqual(await get_mode_display_name(None, "mode_oneesan"), "Yumi")

    async def test_get_mode_display_name_uses_custom_persona_name(self) -> None:
        with patch(
            "utils.interaction_status.get_custom_persona_by_mode_key",
            new=AsyncMock(return_value={"name": "Tomori"}),
        ):
            self.assertEqual(await get_mode_display_name(123, "custom_tomori"), "Tomori")

    async def test_build_about_embed_includes_stats_fields(self) -> None:
        bot = SimpleNamespace(
            guilds=[
                SimpleNamespace(id=1, member_count=12),
                SimpleNamespace(id=2, member_count=34),
            ]
        )
        cog = Utilities(bot)
        cog.start_time = datetime.now() - timedelta(hours=2, minutes=5)
        guild = SimpleNamespace(id=1)

        with patch(
            "cogs.utilities.get_stats",
            new=AsyncMock(return_value={"messages_processed": 321, "images_analyzed": 9}),
        ), patch(
            "cogs.utilities.get_server_mode",
            new=AsyncMock(return_value="mode_oneesan"),
        ), patch(
            "cogs.utilities.get_mode_profile",
            return_value=SimpleNamespace(bio="Warm and caring.", display_name="Onee-san"),
        ):
            embed = await cog._build_about_embed(guild)

        field_names = {field.name for field in embed.fields}
        self.assertEqual(embed.title, "🤖 About Yumi")
        self.assertIn("⏱️ Uptime", field_names)
        self.assertIn("🏠 Servers", field_names)
        self.assertIn("👥 Users", field_names)
        self.assertIn("💬 Messages Processed", field_names)
        self.assertIn("🖼️ Images Analyzed", field_names)
        self.assertIn("💾 Memory", field_names)
        self.assertIn("🎭 Current Mode", field_names)


if __name__ == "__main__":
    unittest.main()
