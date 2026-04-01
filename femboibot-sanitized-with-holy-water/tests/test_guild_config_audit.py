import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class GuildConfigAuditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod

        self.db_handler = importlib.reload(db_handler_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_schema_migration_adds_normalized_columns(self):
        guild_id = 123
        db_path = Path(self._tmp.name) / f"guild_{guild_id}.db"
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                CREATE TABLE guild_config_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    field TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

        await self.db_handler.init_guild_db(guild_id)

        async with aiosqlite.connect(db_path) as db:
            async with db.execute("PRAGMA table_info(guild_config_audit)") as cursor:
                columns = {row[1] for row in await cursor.fetchall()}

        assert "category" in columns
        assert "detail_json" in columns
        assert "summary" in columns
        assert "target_type" in columns
        assert "target_id" in columns

    async def test_add_guild_config_audit_stores_normalized_fields(self):
        guild_id = 456
        await self.db_handler.init_guild_db(guild_id)

        await self.db_handler.add_guild_config_audit(
            guild_id,
            999,
            "persona_mode_switch",
            field="persona_mode",
            old_value="mode_default",
            new_value="custom_456_test",
            category="persona_presentation",
            summary="Switched active persona",
            target_type="persona",
            target_id="custom_456_test",
            detail={"evil_mode": False},
        )

        rows = await self.db_handler.get_guild_config_audit_entries(guild_id)
        row = rows[0]
        assert row["category"] == "persona_presentation"
        assert row["summary"] == "Switched active persona"
        assert row["target_type"] == "persona"
        assert row["target_id"] == "custom_456_test"
        assert row["detail"]["evil_mode"] is False

    async def test_add_guild_config_audit_keeps_legacy_calls_compatible(self):
        guild_id = 789
        await self.db_handler.init_guild_db(guild_id)

        await self.db_handler.add_guild_config_audit(
            guild_id,
            1,
            "tool_toggle_save",
            field="web_search_enabled",
            old_value="0",
            new_value="1",
        )

        rows = await self.db_handler.get_guild_config_audit_entries(guild_id)
        assert rows[0]["category"] == "tools_config"

    async def test_add_guild_config_audit_rejects_invalid_category(self):
        guild_id = 999
        await self.db_handler.init_guild_db(guild_id)

        with self.assertRaises(ValueError):
            await self.db_handler.add_guild_config_audit(
                guild_id,
                1,
                "oops",
                category="totally_invalid",
            )


if __name__ == "__main__":
    unittest.main()
