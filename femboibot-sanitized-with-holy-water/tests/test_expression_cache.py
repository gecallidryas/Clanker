import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class FakeEmoji:
    def __init__(self, emoji_id: int, name: str, animated: bool = False):
        self.id = emoji_id
        self.name = name
        self.animated = animated


class FakeStickerFormat:
    def __init__(self, value: int, name: str = "png"):
        self.value = value
        self.name = name


class FakeSticker:
    def __init__(self, sticker_id: int, name: str, description: str = "", format_value: int = 1):
        self.id = sticker_id
        self.name = name
        self.description = description
        self.format = FakeStickerFormat(format_value)


class FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self.name = f"Guild {guild_id}"
        self.emojis = []
        self.stickers = []

    async def fetch_emojis(self):
        return list(self.emojis)

    async def fetch_stickers(self):
        return list(self.stickers)


class FakeBot:
    def __init__(self):
        self.application_id = 999
        self._app_emojis = []

    async def fetch_application_emojis(self):
        value = self._app_emojis
        if isinstance(value, Exception):
            raise value
        return list(value)


class ExpressionCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        import utils.expression_sync as expression_sync_mod
        import utils.expression_cache as expression_cache_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.expression_sync = importlib.reload(expression_sync_mod)
        self.expression_cache = importlib.reload(expression_cache_mod)
        self.bot = FakeBot()
        self.service = self.expression_cache.ExpressionService(self.bot)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_guild_refresh_soft_deletes_removed_rows_and_prunes_after_retention(self):
        guild = FakeGuild(123)
        guild.emojis = [FakeEmoji(1, "wave"), FakeEmoji(2, "smile")]
        guild.stickers = [FakeSticker(10, "dance", "cute dance")]

        first_snapshot = await self.service.refresh_guild_snapshot(guild)
        self.assertEqual(first_snapshot.snapshot_version, 1)
        self.assertEqual(first_snapshot.counts_by_source["guild_emoji"], 2)
        self.assertEqual(first_snapshot.counts_by_source["guild_sticker"], 1)

        guild.emojis = [FakeEmoji(1, "wave_renamed"), FakeEmoji(3, "sparkle")]
        guild.stickers = []
        second_snapshot = await self.service.refresh_guild_snapshot(guild)
        self.assertEqual(second_snapshot.snapshot_version, 2)
        self.assertIn("wave_renamed", [item.name for item in second_snapshot.of_kind("emoji")])

        rows = await self.db_handler.list_expressions("guild", guild.id, include_unavailable=True)
        deleted_rows = [row for row in rows if row["kind"] == "sticker" and row["available"] == 0]
        self.assertEqual(len(deleted_rows), 1)
        self.assertIsNotNone(deleted_rows[0]["deleted_at"])

        pruned = await self.db_handler.prune_deleted_expressions(
            "guild",
            guild.id,
            now=self.db_handler._utcnow() + self.db_handler.timedelta(days=8),
        )
        self.assertEqual(pruned, 2)

    async def test_application_refresh_uses_background_timestamp_and_on_access_fallback(self):
        self.bot._app_emojis = [FakeEmoji(50, "femmywave")]
        snapshot = await self.service.refresh_application_emojis(background_refresh=True)
        self.assertEqual(snapshot.snapshot_version, 1)

        sync_state = await self.db_handler.get_expression_sync_state("application", self.bot.application_id)
        self.assertIsNotNone(sync_state["last_background_refresh_at"])

        self.bot._app_emojis = RuntimeError("boom")
        self.service.mark_application_stale()
        stale_snapshot = await self.service.get_application_snapshot()
        self.assertTrue(stale_snapshot.stale)
        self.assertEqual([item.name for item in stale_snapshot.of_kind("emoji")], ["femmywave"])

        self.bot._app_emojis = [FakeEmoji(50, "femmywave"), FakeEmoji(51, "yumismile")]
        self.service.mark_application_stale()
        refreshed = await self.service.get_application_snapshot()
        self.assertFalse(refreshed.stale)
        self.assertEqual(len(refreshed.of_kind("emoji")), 2)

    async def test_prompt_context_stays_bounded_and_exposes_stickers_selectively(self):
        guild = FakeGuild(321)
        guild.emojis = [FakeEmoji(index, f"emoji_{index}") for index in range(1, 12)]
        guild.stickers = [
            FakeSticker(200 + index, f"sticker_{index}", "cute happy reaction")
            for index in range(1, 6)
        ]
        self.bot._app_emojis = [FakeEmoji(500 + index, f"femmy_{index}") for index in range(1, 5)]

        await self.service.refresh_guild_snapshot(guild)
        await self.service.refresh_application_emojis(background_refresh=True)

        neutral = await self.service.build_prompt_context(
            guild,
            message_text="hello there",
            mode="mode_femboy",
            affection_points=0,
            recent_context_text="",
        )
        self.assertLessEqual(len(neutral.emoji_lines), 6)
        self.assertEqual(neutral.sticker_lines, [])

        expressive = await self.service.build_prompt_context(
            guild,
            message_text="reply with a cute sticker please",
            mode="mode_femboy",
            affection_points=800,
            recent_context_text="used :emoji_1: recently",
        )
        self.assertLessEqual(len(expressive.emoji_lines), 6)
        self.assertGreaterEqual(len(expressive.sticker_lines), 1)
        self.assertLessEqual(len(expressive.sticker_lines), 3)

    async def test_resolve_sticker_for_send_recovers_from_missing_runtime_cache(self):
        guild = FakeGuild(456)
        guild.stickers = [FakeSticker(900, "wave_sticker", "hi")]
        await self.service.refresh_guild_snapshot(guild)

        guild.stickers = []
        async def _fetch_stickers():
            return [FakeSticker(900, "wave_sticker", "hi")]

        guild.fetch_stickers = _fetch_stickers
        sticker = await self.service.resolve_sticker_for_send(guild, 900)
        self.assertIsNotNone(sticker)
        self.assertEqual(sticker.id, 900)


if __name__ == "__main__":
    unittest.main()
