import os
import sys
import tempfile
import unittest
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class ShortTermChannelMemoryTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_channel_scoped_short_term_add_get_delete(self):
        guild_id = 4242
        channel_a = 11
        channel_b = 22
        user_a = 101
        user_b = 202

        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, user_a)
        await self.db_handler.create_user(guild_id, user_b)

        await self.db_handler.add_short_term_fact(guild_id, user_a, "a-1", channel_id=channel_a)
        await self.db_handler.add_short_term_fact(guild_id, user_b, "b-1", channel_id=channel_a)
        await self.db_handler.add_short_term_fact(guild_id, user_a, "a-2", channel_id=channel_b)

        channel_a_user_a = await self.db_handler.get_short_term_facts_for_channel(
            guild_id, user_a, channel_a
        )
        channel_b_user_a = await self.db_handler.get_short_term_facts_for_channel(
            guild_id, user_a, channel_b
        )
        self.assertEqual(channel_a_user_a, ["a-1"])
        self.assertEqual(channel_b_user_a, ["a-2"])

        deleted = await self.db_handler.delete_short_term_facts_for_channel(guild_id, channel_a)
        self.assertEqual(deleted, 2)

        channel_a_user_a_after = await self.db_handler.get_short_term_facts_for_channel(
            guild_id, user_a, channel_a
        )
        channel_b_user_a_after = await self.db_handler.get_short_term_facts_for_channel(
            guild_id, user_a, channel_b
        )
        self.assertEqual(channel_a_user_a_after, [])
        self.assertEqual(channel_b_user_a_after, ["a-2"])


if __name__ == "__main__":
    unittest.main()
