import importlib
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class _FakeBot:
    def __init__(self):
        self.user = types.SimpleNamespace(id=999, display_name="Femmy")

    def get_guild(self, _guild_id: int):
        return None

    def get_user(self, _user_id: int):
        return None


class _FakeGuildPermissions:
    administrator = False
    manage_guild = False


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self.name = "Test Guild"
        self.owner_id = 1234

    def get_channel(self, _channel_id: int):
        return None


class _FakeMember:
    def __init__(self, user_id: int, guild: _FakeGuild):
        self.id = user_id
        self.guild = guild
        self.display_name = "Tester"
        self.bot = False
        self.mention = f"<@{user_id}>"
        self.guild_permissions = _FakeGuildPermissions()


class LegacyCustomPersonaAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_dir = tempfile.mkdtemp(prefix="legacy_custom_persona_")
        os.environ["DATABASE_DIR"] = self._tmp_dir
        os.environ["GLOBAL_DATABASE_PATH"] = str(Path(self._tmp_dir) / "global.db")
        self._saved_modules = {
            name: sys.modules.get(name)
            for name in (
                "aiosqlite",
                "utils.rag_store",
            )
        }

        # Ensure modules are reloaded using this test database path.
        sys.modules.pop("aiosqlite", None)
        sys.modules.pop("utils.rag_store", None)

        import aiosqlite  # noqa: F401

        rag_store_stub = types.ModuleType("utils.rag_store")

        async def _dummy_get_rag_context(*args, **kwargs):
            return ""

        rag_store_stub.get_rag_context = _dummy_get_rag_context
        sys.modules["utils.rag_store"] = rag_store_stub

        db_handler_mod = importlib.import_module("utils.db_handler")
        custom_mod = importlib.import_module("personas.custom")
        ai_brain_mod = importlib.import_module("cogs.ai_brain")
        personas_mod = importlib.import_module("personas")

        self.db_handler = importlib.reload(db_handler_mod)
        self.custom_mod = importlib.reload(custom_mod)
        self.ai_brain_mod = importlib.reload(ai_brain_mod)
        self.compile_persona_sections = personas_mod.compile_persona_sections

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        for name in ("utils.rag_store", "aiosqlite"):
            sys.modules.pop(name, None)
        for name, module in self._saved_modules.items():
            if module is not None:
                sys.modules[name] = module

    async def _seed_legacy_custom_persona(self) -> tuple[int, str, str]:
        guild_id = 991
        await self.db_handler.init_guild_db(guild_id)
        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Legacy Velvet")
        evil_prompt = "legacy evil prompt should be preserved"
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Legacy Velvet",
            mode_key=mode_key,
            bio="Legacy bio survives",
            avatar_path=None,
            banner_path=None,
            normal_prompt="legacy normal prompt",
            evil_prompt=evil_prompt,
            created_by=55,
            aliases=["legacy", "velvet"],
        )
        return guild_id, mode_key, evil_prompt

    async def test_loader_adapts_legacy_prompt_only_persona_definition(self):
        guild_id, mode_key, evil_prompt = await self._seed_legacy_custom_persona()

        persona = await self.custom_mod.load_custom_persona_definition(guild_id, mode_key)

        self.assertIsNotNone(persona)
        self.assertEqual(persona.key, mode_key)
        self.assertEqual(persona.identity.bio, "Legacy bio survives")
        self.assertEqual(persona.identity.aliases, ("legacy", "velvet"))

        compiled = self.compile_persona_sections(persona, evil_mode=True)
        compiled_text = "\n\n".join(f"{section.title}\n{section.body}" for section in compiled)
        self.assertIn(evil_prompt, compiled_text)
        self.assertIn("EXAMPLE REPLIES", compiled_text)

    async def test_ai_brain_build_prompt_compiles_legacy_custom_persona_sections(self):
        guild_id, mode_key, evil_prompt = await self._seed_legacy_custom_persona()

        original_register_builtin_tools = self.ai_brain_mod.register_builtin_tools
        self.ai_brain_mod.register_builtin_tools = lambda: None
        try:
            brain = self.ai_brain_mod.AIBrain(_FakeBot())
        finally:
            self.ai_brain_mod.register_builtin_tools = original_register_builtin_tools

        guild = _FakeGuild(guild_id)
        member = _FakeMember(guild.owner_id, guild)
        with patch(
            "cogs.ai_brain.get_evil_mode",
            AsyncMock(return_value=True),
        ), patch(
            "cogs.ai_brain.get_guild_config",
            AsyncMock(return_value={"normal_text_provider": "gemini"}),
        ), patch(
            "cogs.ai_brain.get_personal_memories",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_channel_recency_summary",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_guild_recency_summary",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_mention_lookup_personal_memories",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_server_memory",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_persona_attributes",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_sample_dialogues",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.get_affection_by_mode",
            AsyncMock(return_value={"affection_level": "friend", "affection_points": 250}),
        ), patch(
            "cogs.ai_brain.get_strict_alias",
            AsyncMock(return_value=None),
        ), patch(
            "cogs.ai_brain.get_aliases",
            AsyncMock(return_value=[]),
        ), patch(
            "cogs.ai_brain.render_prompt_tool_definitions",
            AsyncMock(return_value=""),
        ), patch.object(
            brain,
            "get_user_gender",
            AsyncMock(return_value="unknown"),
        ), patch.object(
            brain,
            "_build_expression_prompt_context",
            AsyncMock(return_value=([], [], [])),
        ):
            prompt = await brain.build_prompt(
                guild_id,
                member.id,
                "help me",
                "ctx",
                channel_id=456,
                member=member,
                mode_override=mode_key,
            )

        self.assertIn("=== ROLEPLAY CONTRACT ===", prompt)
        self.assertIn("=== ACTIVE PERSONA IDENTITY ===", prompt)
        self.assertIn("=== EXAMPLE REPLIES ===", prompt)
        self.assertIn(evil_prompt, prompt)


if __name__ == "__main__":
    unittest.main()
