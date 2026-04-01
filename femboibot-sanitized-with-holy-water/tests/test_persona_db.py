import os
import sys
import tempfile
import unittest
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class PersonaDbTests(unittest.IsolatedAsyncioTestCase):
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
            aliases=None,
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


if __name__ == "__main__":
    unittest.main()
