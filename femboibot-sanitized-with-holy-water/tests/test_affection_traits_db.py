import os
import sys
import tempfile
import unittest
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class AffectionTraitDbTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_trait_upsert_and_history(self):
        guild_id = 42
        mode_key = "custom_42_test"
        await self.db_handler.init_guild_db(guild_id)

        traits = [
            {
                "trait_key": "flowers",
                "trait_text": "likes flowers",
                "trigger_terms": ["flowers"],
                "points_value": 10,
                "one_time": True,
            }
        ]

        await self.db_handler.upsert_persona_traits(guild_id, mode_key, traits)
        stored = await self.db_handler.get_persona_traits(guild_id, mode_key)
        self.assertEqual(len(stored), 1)
        self.assertTrue(stored[0]["one_time"])

        first = await self.db_handler.record_trait_hit(guild_id, 7, mode_key, "flowers")
        self.assertTrue(first["first_time"])
        repeat = await self.db_handler.record_trait_hit(guild_id, 7, mode_key, "flowers")
        self.assertFalse(repeat["first_time"])

        history = await self.db_handler.get_user_trait_history(guild_id, 7, mode_key)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["trait_key"], "flowers")

if __name__ == "__main__":
    unittest.main()
