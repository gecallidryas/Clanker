import importlib
import os
import shutil
import sqlite3
import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp_tests"
TMP_ROOT.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT / "discord_bot"))


class DbHandlerTimestampSerializationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_path = TMP_ROOT / f"db_timestamps_{uuid.uuid4().hex}"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        os.environ["DATABASE_DIR"] = str(self._tmp_path)
        os.environ["GLOBAL_DATABASE_PATH"] = str(self._tmp_path / "global.db")

        sys.modules.pop("aiosqlite", None)
        import aiosqlite  # noqa: F401

        from utils import db_handler as db_handler_mod

        self.db_handler = importlib.reload(db_handler_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._tmp_path, ignore_errors=True)

    def _query_one(self, path: Path, sql: str, params: tuple = ()):
        with sqlite3.connect(path) as conn:
            row = conn.execute(sql, params).fetchone()
        return row[0] if row else None

    async def test_init_db_stores_global_start_time_as_iso_utc_string(self):
        await self.db_handler.init_db()

        stored = self._query_one(self._tmp_path / "global.db", "SELECT start_time FROM bot_stats WHERE id = 1")

        self.assertIsInstance(stored, str)
        self.assertIn("T", stored)
        self.assertTrue(stored.endswith("+00:00"))

    async def test_add_reminder_stores_iso_string_and_due_lookup_still_works(self):
        guild_id = 321
        await self.db_handler.init_guild_db(guild_id)
        remind_at = datetime(2026, 1, 15, 8, 30, 45, tzinfo=timezone.utc)

        reminder_id = await self.db_handler.add_reminder(
            user_id=111,
            guild_id=guild_id,
            channel_id=222,
            message="drink water",
            remind_at=remind_at,
        )

        stored = self._query_one(
            self._tmp_path / f"guild_{guild_id}.db",
            "SELECT remind_at FROM reminders WHERE id = ?",
            (reminder_id,),
        )

        self.assertEqual(stored, remind_at.isoformat())
        due = await self.db_handler.get_due_reminders()
        self.assertTrue(any(item["id"] == reminder_id for item in due))

    async def test_mark_starboard_entry_deleted_stores_iso_timestamp_string(self):
        guild_id = 654
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.upsert_starboard_entry(
            guild_id=guild_id,
            original_message_id=1001,
            starboard_message_id=2002,
            channel_id=3003,
            emoji_used="⭐",
        )

        deleted = await self.db_handler.mark_starboard_entry_deleted(guild_id, 1001)

        self.assertTrue(deleted)
        stored = self._query_one(
            self._tmp_path / f"guild_{guild_id}.db",
            "SELECT deleted_at FROM starboard_entries WHERE original_message_id = ?",
            (1001,),
        )
        self.assertIsInstance(stored, str)
        self.assertIn("T", stored)

    async def test_pending_fact_expiry_is_serialized_as_iso_string_and_cleanup_still_works(self):
        guild_id = 987
        await self.db_handler.init_guild_db(guild_id)

        pending_id = await self.db_handler.create_pending_fact(
            guild_id=guild_id,
            about_user_id=123,
            fact="likes tea",
            learned_from_user_id=456,
            channel_id=789,
            expires_minutes=-1,
        )

        stored = self._query_one(
            self._tmp_path / f"guild_{guild_id}.db",
            "SELECT expires_at FROM pending_facts WHERE id = ?",
            (pending_id,),
        )

        self.assertIsInstance(stored, str)
        self.assertIn("T", stored)

        deleted_count = await self.db_handler.cleanup_expired_pending_facts(guild_id)
        self.assertEqual(deleted_count, 1)


if __name__ == "__main__":
    unittest.main()
