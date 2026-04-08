import importlib
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = "/mnt/e/femboibot/discord_bot"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cogs.admin import Admin


class AvatarUpdateLimitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._old_database_dir = os.environ.get("DATABASE_DIR")
        self._old_global_db = os.environ.get("GLOBAL_DATABASE_PATH")
        os.environ["DATABASE_DIR"] = self._temp_dir.name
        os.environ.pop("GLOBAL_DATABASE_PATH", None)

        import utils.db_handler as db_handler

        self.db_handler = importlib.reload(db_handler)
        await self.db_handler.init_db()

    async def asyncTearDown(self) -> None:
        if self._old_database_dir is None:
            os.environ.pop("DATABASE_DIR", None)
        else:
            os.environ["DATABASE_DIR"] = self._old_database_dir

        if self._old_global_db is None:
            os.environ.pop("GLOBAL_DATABASE_PATH", None)
        else:
            os.environ["GLOBAL_DATABASE_PATH"] = self._old_global_db

        import utils.db_handler as db_handler

        importlib.reload(db_handler)
        self._temp_dir.cleanup()

    async def test_avatar_updates_allow_five_changes_per_window(self) -> None:
        guild_id = 987654321012345678

        for _ in range(5):
            allowed, reason = await self.db_handler.can_update_guild_avatar(guild_id)
            self.assertTrue(allowed)
            self.assertEqual(reason, "ok")
            await self.db_handler.record_guild_avatar_update(guild_id)

        allowed, reason = await self.db_handler.can_update_guild_avatar(guild_id)
        self.assertFalse(allowed)
        self.assertEqual(reason, "hourly")


class AvatarErrorMessageTests(unittest.TestCase):
    def test_avatar_hourly_error_mentions_five_per_five_minutes(self) -> None:
        self.assertEqual(
            Admin._avatar_error("hourly"),
            "Avatar updates are limited to 5 per 5 minutes. Try again later.",
        )

    def test_describe_http_error_includes_status_code_and_text(self) -> None:
        from utils.discord_http import describe_http_error

        error = SimpleNamespace(status=429, code=30008, text="Too many profile changes.")
        self.assertEqual(
            describe_http_error(error),
            "http (status=429, code=30008, text=Too many profile changes.)",
        )


if __name__ == "__main__":
    unittest.main()
