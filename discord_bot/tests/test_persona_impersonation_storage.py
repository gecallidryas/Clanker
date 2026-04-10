import importlib
import json
import os
import sys
import tempfile
import unittest

ROOT = "/mnt/e/femboibot/discord_bot"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class PersonaImpersonationStorageTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_custom_persona_persists_sample_dialogues_json(self) -> None:
        guild_id = 987654321
        mode_key = "custom_test_impersonation"
        sample_dialogues = [
            "yeah no i get you",
            "LMFAO that is so cursed",
        ]

        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Impersonated User",
            mode_key=mode_key,
            bio="Generated persona",
            avatar_path=None,
            banner_path=None,
            normal_prompt="Normal prompt",
            evil_prompt=None,
            created_by=111,
            aliases=["impersonated"],
            sample_dialogues_json=json.dumps(sample_dialogues),
        )

        persona = await self.db_handler.get_custom_persona_by_name(guild_id, "Impersonated User")

        self.assertIsNotNone(persona)
        self.assertEqual(json.loads(persona["sample_dialogues_json"]), sample_dialogues)


if __name__ == "__main__":
    unittest.main()
