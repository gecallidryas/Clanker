import os
import sys
import tempfile
import unittest
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.memory_limits import validate_fact_content
from utils.self_teaching import _handle_remember_this_fact


class MemoryLimitsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        os.environ["MAX_MEMORY_LENGTH"] = "10"
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name
        from utils import db_handler as db_handler_mod

        self.db_handler = importlib.reload(db_handler_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_validate_fact_content_rejects_too_long(self):
        result = validate_fact_content("x" * 11)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error, "CONTENT_TOO_LONG")

    async def test_db_handler_rejects_oversized_fact(self):
        guild_id = 999
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, 1001)
        with self.assertRaises(ValueError):
            await self.db_handler.add_fact(guild_id, 1001, "x" * 50)

    async def test_self_teaching_rejects_oversized_fact(self):
        ctx = type(
            "Ctx",
            (),
            {
                "guild": type("Guild", (), {"id": 1})(),
                "user": type("User", (), {"id": 2})(),
                "channel": type("Channel", (), {"id": 3})(),
            },
        )()
        result = await _handle_remember_this_fact(ctx, {"fact": "x" * 50})
        self.assertFalse(result.ok)
        self.assertIn("too long", result.summary.lower())
