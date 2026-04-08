import importlib
import os
import shutil
import sqlite3
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp_tests"
TMP_ROOT.mkdir(exist_ok=True)

import sys
sys.path.insert(0, str(ROOT / "discord_bot"))


class PersonaDbTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_path = TMP_ROOT / f"persona_db_{uuid.uuid4().hex}"
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

    async def test_persona_crud(self):
        guild_id = 12345
        await self.db_handler.init_guild_db(guild_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Test Persona")
        persona_id = await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Test Persona",
            mode_key=mode_key,
            bio="Bio",
            avatar_path="/tmp/avatar.png",
            banner_path=None,
            normal_prompt="Normal",
            evil_prompt=None,
            created_by=999,
        )

        self.assertGreater(persona_id, 0)

        persona = await self.db_handler.get_custom_persona_by_mode_key(guild_id, mode_key)
        self.assertIsNotNone(persona)
        self.assertEqual(persona["name"], "Test Persona")

        by_name = await self.db_handler.get_custom_persona_by_name(guild_id, "test persona")
        self.assertIsNotNone(by_name)
        self.assertEqual(by_name["mode_key"], mode_key)

        updated = await self.db_handler.update_custom_persona(guild_id, mode_key, bio="Updated")
        self.assertTrue(updated)
        persona = await self.db_handler.get_custom_persona_by_mode_key(guild_id, mode_key)
        self.assertEqual(persona["bio"], "Updated")

        deleted = await self.db_handler.delete_custom_persona(guild_id, mode_key)
        self.assertTrue(deleted)
        persona = await self.db_handler.get_custom_persona_by_mode_key(guild_id, mode_key)
        self.assertIsNone(persona)

    async def test_sanitize_and_build_mode_key(self):
        guild_id = 7
        name = "  My Cool Persona!! "
        slug = self.db_handler.sanitize_persona_name(name)
        self.assertEqual(slug, "my_cool_persona")
        mode_key = self.db_handler.build_custom_mode_key(guild_id, name)
        self.assertEqual(mode_key, "custom_7_my_cool_persona")

    async def test_active_persona_list_falls_back_to_primary_mode(self):
        guild_id = 123
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.set_server_mode(guild_id, "mode_femboy")

        modes = await self.db_handler.get_active_persona_modes(guild_id)

        self.assertEqual(modes, ["mode_femboy"])

    async def test_multi_persona_config_fields_persist(self):
        guild_id = 124
        await self.db_handler.init_guild_db(guild_id)

        await self.db_handler.update_guild_config(
            guild_id,
            {
                "ai_multi_persona_enabled": 1,
                "ai_triggered_persona_limit": 3,
                "ai_persona_webhooks_enabled": 0,
            },
        )

        config = await self.db_handler.get_guild_config(guild_id)

        self.assertEqual(config["ai_multi_persona_enabled"], 1)
        self.assertEqual(config["ai_triggered_persona_limit"], 3)
        self.assertEqual(config["ai_persona_webhooks_enabled"], 0)

    async def test_guild_config_omits_removed_reply_sequence_fields(self):
        guild_id = 1241
        await self.db_handler.init_guild_db(guild_id)

        config = await self.db_handler.get_guild_config(guild_id)

        self.assertNotIn("reply_sequence_enabled", config)
        self.assertNotIn("reply_sequence_timeout_seconds", config)
        self.assertNotIn("reply_sequence_hard_max_stages", config)
        self.assertNotIn("reply_sequence_allow_gif", config)
        self.assertNotIn("reply_sequence_allow_sticker", config)
        self.assertNotIn("reply_sequence_allow_emoji_only", config)

    async def test_guild_config_field_allowlist_omits_removed_legacy_continuation_fields(self):
        self.assertNotIn("reply_sequence_enabled", self.db_handler.GUILD_CONFIG_FIELDS)
        self.assertNotIn("reply_sequence_timeout_seconds", self.db_handler.GUILD_CONFIG_FIELDS)
        self.assertNotIn("reply_sequence_hard_max_stages", self.db_handler.GUILD_CONFIG_FIELDS)
        self.assertNotIn("reply_sequence_allow_gif", self.db_handler.GUILD_CONFIG_FIELDS)
        self.assertNotIn("reply_sequence_allow_sticker", self.db_handler.GUILD_CONFIG_FIELDS)
        self.assertNotIn("reply_sequence_allow_emoji_only", self.db_handler.GUILD_CONFIG_FIELDS)

    async def test_init_guild_db_rebuilds_legacy_guild_config_without_reply_sequence_fields(self):
        guild_id = 1242
        legacy_db_path = Path(self.db_handler.get_guild_db_path(guild_id))
        legacy_db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(legacy_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    gemini_model TEXT DEFAULT 'gemini-2.5-flash-lite',
                    reply_sequence_enabled INTEGER DEFAULT 0,
                    reply_sequence_timeout_seconds INTEGER DEFAULT 300,
                    reply_sequence_hard_max_stages INTEGER DEFAULT 4,
                    reply_sequence_allow_gif INTEGER DEFAULT 1,
                    reply_sequence_allow_sticker INTEGER DEFAULT 1,
                    reply_sequence_allow_emoji_only INTEGER DEFAULT 1,
                    ai_multi_persona_enabled INTEGER DEFAULT 0,
                    ai_triggered_persona_limit INTEGER DEFAULT 1,
                    ai_active_personas TEXT,
                    ai_persona_webhooks_enabled INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                INSERT INTO guild_config (
                    guild_id,
                    reply_sequence_enabled,
                    reply_sequence_timeout_seconds,
                    reply_sequence_hard_max_stages
                ) VALUES (?, ?, ?, ?)
                """,
                (guild_id, 1, 900, 9),
            )
            conn.commit()

        await self.db_handler.init_guild_db(guild_id)

        with sqlite3.connect(legacy_db_path) as conn:
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(guild_config)").fetchall()
            }

        self.assertNotIn("reply_sequence_enabled", columns)
        self.assertNotIn("reply_sequence_timeout_seconds", columns)
        self.assertNotIn("reply_sequence_hard_max_stages", columns)
        self.assertNotIn("reply_sequence_allow_gif", columns)
        self.assertNotIn("reply_sequence_allow_sticker", columns)
        self.assertNotIn("reply_sequence_allow_emoji_only", columns)

        config = await self.db_handler.get_guild_config(guild_id)

        self.assertNotIn("reply_sequence_enabled", config)
        self.assertNotIn("reply_sequence_timeout_seconds", config)
        self.assertNotIn("reply_sequence_hard_max_stages", config)

    async def test_set_welcome_image_enabled_repairs_initialized_legacy_schema(self):
        guild_id = 1243
        await self.db_handler.init_guild_db(guild_id)

        legacy_db_path = Path(self.db_handler.get_guild_db_path(guild_id))
        with sqlite3.connect(legacy_db_path) as conn:
            conn.execute("DROP TABLE guild_config")
            conn.execute(
                """
                CREATE TABLE guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel_id INTEGER,
                    welcome_enabled INTEGER DEFAULT 1,
                    welcome_message_template TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                INSERT INTO guild_config (guild_id, welcome_channel_id, welcome_enabled)
                VALUES (?, ?, ?)
                """,
                (guild_id, 555, 1),
            )
            conn.commit()

        await self.db_handler.set_welcome_image_enabled(guild_id, True)
        config = await self.db_handler.get_welcome_config(guild_id)

        with sqlite3.connect(legacy_db_path) as conn:
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(guild_config)").fetchall()
            }

        self.assertIn("welcome_image_enabled", columns)
        self.assertIn("welcome_image_template", columns)
        self.assertIn("welcome_image_destination", columns)
        self.assertIn("welcome_image_channel_id", columns)
        self.assertTrue(config["welcome_image_enabled"])

    async def test_set_active_persona_modes_persists_custom_personas(self):
        guild_id = 125
        await self.db_handler.init_guild_db(guild_id)
        custom_mode = self.db_handler.build_custom_mode_key(guild_id, "Lilya")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Lilya",
            mode_key=custom_mode,
            bio="Bio",
            avatar_path="/tmp/lilya.png",
            banner_path=None,
            normal_prompt="Normal",
            evil_prompt=None,
            created_by=999,
            aliases=None,
        )

        await self.db_handler.set_active_persona_modes(guild_id, ["mode_femboy", custom_mode])

        modes = await self.db_handler.get_active_persona_modes(guild_id)

        self.assertEqual(modes, ["mode_femboy", custom_mode])

    async def test_active_persona_list_drops_deleted_custom_personas(self):
        guild_id = 126
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.set_server_mode(guild_id, "mode_oneesan")
        custom_mode = self.db_handler.build_custom_mode_key(guild_id, "Minori")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Minori",
            mode_key=custom_mode,
            bio="Bio",
            avatar_path="/tmp/minori.png",
            banner_path=None,
            normal_prompt="Normal",
            evil_prompt=None,
            created_by=999,
            aliases=None,
        )
        await self.db_handler.set_active_persona_modes(
            guild_id,
            ["mode_oneesan", custom_mode, custom_mode, "custom_126_missing"],
        )
        await self.db_handler.delete_custom_persona(guild_id, custom_mode)

        modes = await self.db_handler.get_active_persona_modes(guild_id)

        self.assertEqual(modes, ["mode_oneesan"])

    async def test_init_guild_db_accepts_awaitable_aiosqlite_connect(self):
        guild_id = 127
        original_connect = self.db_handler.aiosqlite.connect

        async def _awaitable_connect(*args, **kwargs):
            return await original_connect(*args, **kwargs)

        with mock.patch.object(self.db_handler.aiosqlite, "connect", side_effect=_awaitable_connect):
            await self.db_handler.init_guild_db(guild_id)
            modes = await self.db_handler.get_active_persona_modes(guild_id)

        self.assertEqual(modes, ["mode_default"])


if __name__ == "__main__":
    unittest.main()
