import importlib
import os
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp_tests"
TMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "discord_bot"))


class _FakeBot(SimpleNamespace):
    def __init__(self):
        super().__init__()


class PersonaManageConfigTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_path = TMP_ROOT / f"persona_manage_{uuid.uuid4().hex}"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        os.environ["DATABASE_DIR"] = str(self._tmp_path)
        os.environ["GLOBAL_DATABASE_PATH"] = str(self._tmp_path / "global.db")
        os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

        sys.modules.pop("aiosqlite", None)
        import aiosqlite  # noqa: F401

        from utils import db_handler as db_handler_mod
        from cogs import config as config_mod
        from cogs import persona as persona_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.config_mod = importlib.reload(config_mod)
        self.persona_mod = importlib.reload(persona_mod)

        self.config_cog = self.config_mod.Config(_FakeBot())
        self.persona_cog = self.persona_mod.Persona(_FakeBot())

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._tmp_path, ignore_errors=True)

    async def test_config_helpers_persist_multi_persona_runtime_settings(self):
        guild_id = 901
        user_id = 77
        await self.db_handler.init_guild_db(guild_id)

        await self.config_cog._set_multi_persona_enabled(guild_id, user_id, True)
        await self.config_cog._set_triggered_persona_limit(guild_id, user_id, 3)
        await self.config_cog._set_persona_webhooks_enabled(guild_id, user_id, False)

        config = await self.db_handler.get_guild_config(guild_id)

        self.assertEqual(config["ai_multi_persona_enabled"], 1)
        self.assertEqual(config["ai_triggered_persona_limit"], 3)
        self.assertEqual(config["ai_persona_webhooks_enabled"], 0)

    async def test_persona_helper_sets_active_builtin_personas(self):
        guild_id = 902
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.set_server_mode(guild_id, "mode_femboy")

        modes = await self.persona_cog._set_active_persona_modes_for_guild(
            guild_id,
            ["femboy", "oneesan"],
        )

        self.assertEqual(modes, ["mode_femboy", "mode_oneesan"])

    async def test_persona_helper_accepts_custom_persona_names(self):
        guild_id = 903
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
            created_by=77,
            aliases=["lily"],
        )

        modes = await self.persona_cog._set_active_persona_modes_for_guild(
            guild_id,
            ["Lilya"],
        )

        self.assertEqual(modes, [custom_mode])

    async def test_persona_helper_keeps_primary_mode_as_compatibility_fallback(self):
        guild_id = 904
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.set_server_mode(guild_id, "mode_tsundere")

        modes = await self.persona_cog._set_active_persona_modes_for_guild(guild_id, [])

        self.assertEqual(modes, ["mode_tsundere"])
