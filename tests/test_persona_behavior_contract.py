import importlib
import json
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

if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub

if "pytz" not in sys.modules:
    pytz_stub = types.ModuleType("pytz")
    pytz_stub.UnknownTimeZoneError = Exception
    pytz_stub.timezone = lambda _name: None
    sys.modules["pytz"] = pytz_stub

from cogs import ai_brain as ai_brain_mod  # noqa: E402
from personas import compile_persona_sections  # noqa: E402
from personas.builtin import get_builtin_persona  # noqa: E402


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


def _section_map(mode_key: str, *, evil_mode: bool) -> dict[str, str]:
    persona = get_builtin_persona(mode_key)
    return {
        section.title: section.body
        for section in compile_persona_sections(persona, evil_mode=evil_mode)
    }


class BuiltinPersonaBehaviorContractTests(unittest.TestCase):
    def test_practical_help_request_contract_for_mode_default(self):
        sections = _section_map("mode_default", evil_mode=False)

        self.assertIn("TASK AND TOOL COMPETENCE RULES", sections)
        self.assertIn("accurate answers", sections["TASK AND TOOL COMPETENCE RULES"])
        self.assertIn("tool-aware", sections["TASK AND TOOL COMPETENCE RULES"])
        self.assertIn("EXAMPLE REPLIES", sections)
        self.assertIn("confirm the exact channel", sections["EXAMPLE REPLIES"])
        self.assertNotIn("EVIL MODE SCENE RULES", sections)

    def test_affectionate_non_explicit_roleplay_contract_for_femboy_normal_mode(self):
        sections = _section_map("mode_femboy", evil_mode=False)

        self.assertIn("RELATIONSHIP RULES", sections)
        self.assertIn("affectionate", sections["RELATIONSHIP RULES"].lower())
        self.assertIn("submissive", sections["RELATIONSHIP RULES"].lower())
        self.assertIn("NORMAL MODE SCENE RULES", sections)
        self.assertIn("light action beats", sections["NORMAL MODE SCENE RULES"].lower())
        self.assertNotIn("EVIL MODE SCENE RULES", sections)

    def test_normal_mode_action_beat_roleplay_contract_for_oneesan(self):
        sections = _section_map("mode_oneesan", evil_mode=False)

        self.assertIn("VOICE AND CADENCE", sections)
        self.assertIn("measured and comforting", sections["VOICE AND CADENCE"])
        self.assertIn("RELATIONSHIP RULES", sections)
        self.assertIn("protective", sections["RELATIONSHIP RULES"].lower())
        self.assertIn("NORMAL MODE SCENE RULES", sections)
        self.assertIn("care-focused prose", sections["NORMAL MODE SCENE RULES"].lower())
        self.assertNotIn("EVIL MODE SCENE RULES", sections)

    def test_evil_mode_explicit_roleplay_contract_for_oneesan(self):
        sections = _section_map("mode_oneesan", evil_mode=True)

        self.assertIn("EVIL MODE SCENE RULES", sections)
        self.assertIn("possessive intimacy", sections["EVIL MODE SCENE RULES"].lower())
        self.assertIn("EXAMPLE REPLIES", sections)
        self.assertIn("Evil:", sections["EXAMPLE REPLIES"])
        self.assertIn("escalate tone when invited", sections["EXAMPLE REPLIES"])


class BuiltinPersonaPromptBehaviorContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    async def _build_prompt_for_mode(
        self,
        *,
        mode: str,
        request_text: str,
        evil_mode: bool = False,
        tools_text: str = "",
    ) -> str:
        guild = _FakeGuild(123)
        member = _FakeMember(guild.owner_id, guild)

        with patch(
            "cogs.ai_brain.get_evil_mode",
            AsyncMock(return_value=evil_mode),
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
            AsyncMock(return_value=tools_text),
        ), patch.object(
            self.brain,
            "get_user_gender",
            AsyncMock(return_value="unknown"),
        ), patch.object(
            self.brain,
            "_build_expression_prompt_context",
            AsyncMock(return_value=([], [], [])),
        ):
            return await self.brain.build_prompt(
                guild.id,
                member.id,
                request_text,
                "ctx",
                channel_id=456,
                member=member,
                mode_override=mode,
            )

    async def test_tool_use_request_keeps_available_tools_with_compiled_persona_contract(self):
        prompt = await self._build_prompt_for_mode(
            mode="mode_default",
            request_text="search the docs and summarize the result",
            tools_text="- search_docs: use for document lookup",
        )

        self.assertIn("=== ROLEPLAY CONTRACT ===", prompt)
        self.assertIn("=== TASK AND TOOL COMPETENCE RULES ===", prompt)
        self.assertIn("=== AVAILABLE TOOLS ===", prompt)
        self.assertIn("search_docs", prompt)

    async def test_admin_request_keeps_admin_instructions_with_compiled_persona_contract(self):
        prompt = await self._build_prompt_for_mode(
            mode="mode_default",
            request_text="create a new moderation channel and lock it down",
            tools_text="",
        )

        self.assertIn("=== ROLEPLAY CONTRACT ===", prompt)
        self.assertIn("=== ACTIVE PERSONA IDENTITY ===", prompt)
        self.assertIn("=== ADMIN CONFIG INSTRUCTIONS ===", prompt)


class CustomPersonaBehaviorContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_dir = tempfile.mkdtemp(prefix="persona_behavior_contract_")
        os.environ["DATABASE_DIR"] = self._tmp_dir
        os.environ["GLOBAL_DATABASE_PATH"] = str(Path(self._tmp_dir) / "global.db")
        self._saved_modules = {
            name: sys.modules.get(name)
            for name in (
                "aiosqlite",
                "utils.db_handler",
                "personas.custom",
                "cogs.ai_brain",
                "utils.rag_store",
            )
        }

        sys.modules.pop("aiosqlite", None)
        sys.modules.pop("utils.db_handler", None)
        sys.modules.pop("personas.custom", None)
        sys.modules.pop("cogs.ai_brain", None)
        sys.modules.pop("utils.rag_store", None)

        import aiosqlite  # noqa: F401

        rag_store_stub = types.ModuleType("utils.rag_store")

        async def _dummy_get_rag_context(*args, **kwargs):
            return ""

        rag_store_stub.get_rag_context = _dummy_get_rag_context
        sys.modules["utils.rag_store"] = rag_store_stub

        db_handler_mod = importlib.import_module("utils.db_handler")
        custom_mod = importlib.import_module("personas.custom")
        ai_brain_mod_local = importlib.import_module("cogs.ai_brain")

        self.db_handler = importlib.reload(db_handler_mod)
        self.custom_mod = importlib.reload(custom_mod)
        self.ai_brain_mod = importlib.reload(ai_brain_mod_local)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        for name in (
            "utils.rag_store",
            "cogs.ai_brain",
            "personas.custom",
            "utils.db_handler",
            "aiosqlite",
        ):
            sys.modules.pop(name, None)
        for name, module in self._saved_modules.items():
            package_name, _, attr_name = name.rpartition(".")
            package = sys.modules.get(package_name)
            if module is not None:
                sys.modules[name] = module
                if package is not None and attr_name:
                    setattr(package, attr_name, module)
                continue
            if package is not None and hasattr(package, attr_name):
                delattr(package, attr_name)

    async def _seed_structured_custom_persona(self) -> tuple[int, str]:
        guild_id = 778
        await self.db_handler.init_guild_db(guild_id)
        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Gentle Lotus")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Gentle Lotus",
            mode_key=mode_key,
            bio="Legacy bio",
            avatar_path=None,
            banner_path=None,
            normal_prompt="Legacy normal prompt",
            evil_prompt="Legacy evil prompt",
            created_by=55,
            aliases=["lotus"],
        )

        async with self.db_handler.guild_db(guild_id) as db:
            await db.execute(
                """
                UPDATE custom_personas
                SET schema_version = ?,
                    base_template = ?,
                    identity_json = ?,
                    voice_json = ?,
                    examples_json = ?
                WHERE guild_id = ? AND mode_key = ?
                """,
                (
                    1,
                    "mode_oneesan",
                    json.dumps({"display_name": "Gentle Lotus", "aliases": ["lotus"]}),
                    json.dumps({"tone": "guild tone override"}),
                    json.dumps({"normal": ["Beloved, breathe first, then solve it."]}),
                    guild_id,
                    mode_key,
                ),
            )
            await db.commit()
        return guild_id, mode_key

    async def _seed_legacy_custom_persona(self) -> tuple[int, str]:
        guild_id = 991
        await self.db_handler.init_guild_db(guild_id)
        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Legacy Velvet")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Legacy Velvet",
            mode_key=mode_key,
            bio="Legacy bio survives",
            avatar_path=None,
            banner_path=None,
            normal_prompt="legacy normal prompt",
            evil_prompt="legacy evil prompt should be preserved",
            created_by=55,
            aliases=["legacy", "velvet"],
        )
        return guild_id, mode_key

    async def _build_prompt_for_mode(
        self,
        *,
        guild_id: int,
        mode: str,
        request_text: str,
        evil_mode: bool = False,
        tools_text: str = "",
    ) -> str:
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
            AsyncMock(return_value=evil_mode),
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
            AsyncMock(return_value=tools_text),
        ), patch.object(
            brain,
            "get_user_gender",
            AsyncMock(return_value="unknown"),
        ), patch.object(
            brain,
            "_build_expression_prompt_context",
            AsyncMock(return_value=([], [], [])),
        ):
            return await brain.build_prompt(
                guild_id,
                member.id,
                request_text,
                "ctx",
                channel_id=456,
                member=member,
                mode_override=mode,
            )

    async def test_inherited_custom_persona_keeps_base_and_override_contract(self):
        guild_id, mode_key = await self._seed_structured_custom_persona()

        persona = await self.custom_mod.load_custom_persona_definition(guild_id, mode_key)
        sections = {
            section.title: section.body
            for section in compile_persona_sections(persona, evil_mode=False)
        }

        self.assertIn("ACTIVE PERSONA IDENTITY", sections)
        self.assertIn("Gentle Lotus", sections["ACTIVE PERSONA IDENTITY"])
        self.assertIn("VOICE AND CADENCE", sections)
        self.assertIn("guild tone override", sections["VOICE AND CADENCE"])
        self.assertIn("NORMAL MODE SCENE RULES", sections)
        self.assertIn("care-focused prose", sections["NORMAL MODE SCENE RULES"].lower())
        self.assertIn("EXAMPLE REPLIES", sections)
        self.assertIn("Beloved, breathe first, then solve it.", sections["EXAMPLE REPLIES"])

    async def test_legacy_custom_persona_keeps_legacy_notes_without_losing_runtime_contract(self):
        guild_id, mode_key = await self._seed_legacy_custom_persona()

        prompt = await self._build_prompt_for_mode(
            guild_id=guild_id,
            mode=mode_key,
            request_text="use a tool, then adjust the server config",
            evil_mode=True,
            tools_text="- lookup_status: inspect the current configuration",
        )

        self.assertIn("=== ROLEPLAY CONTRACT ===", prompt)
        self.assertIn("=== EXAMPLE REPLIES ===", prompt)
        self.assertIn("legacy evil prompt should be preserved", prompt)
        self.assertIn("=== AVAILABLE TOOLS ===", prompt)
        self.assertIn("lookup_status", prompt)
        self.assertIn("=== ADMIN CONFIG INSTRUCTIONS ===", prompt)


if __name__ == "__main__":
    unittest.main()
