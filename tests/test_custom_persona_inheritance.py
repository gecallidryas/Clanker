import json
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

from personas.builtin import get_builtin_persona
from personas.custom import hydrate_custom_persona_definition


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


class CustomPersonaInheritanceTests(unittest.TestCase):
    def test_mode_oneesan_inheritance_merges_defaults_with_structured_overrides(self):
        base_aliases = get_builtin_persona("mode_oneesan").identity.aliases
        record = {
            "mode_key": "custom_123_gentle_lotus",
            "name": "Gentle Lotus",
            "base_template": "mode_oneesan",
            "identity_json": json.dumps(
                {
                    "display_name": "Gentle Lotus",
                    "aliases": ["lotus", "yumi"],
                    "bio": "Guild authored identity.",
                }
            ),
            "voice_json": json.dumps(
                {
                    "tone": "serene and devotional",
                    "signature_phrases": ["beloved"],
                }
            ),
            "relationship_json": json.dumps(
                {"description": "Protective, doting, and softly possessive."}
            ),
            "examples_json": json.dumps(
                {
                    "normal": ["Beloved, let us solve this together."],
                    "evil": ["Beloved, stay close and follow my lead."],
                }
            ),
            "constraints_json": json.dumps(
                {"hard_rules": ["Always preserve the lotus motif."]}
            ),
            "scene_normal_json": "",
            "scene_evil_json": "",
            "worldview_json": "",
            "utility_json": "",
            "aliases": "",
            "bio": "",
        }

        persona = hydrate_custom_persona_definition(record)
        expected_aliases: list[str] = []
        for alias in (*base_aliases, "lotus", "yumi"):
            if alias not in expected_aliases:
                expected_aliases.append(alias)

        self.assertEqual(persona.identity.display_name, "Gentle Lotus")
        self.assertEqual(persona.identity.aliases, tuple(expected_aliases))
        self.assertEqual(persona.voice.tone, "serene and devotional")
        self.assertEqual(persona.voice.cadence, "measured and comforting")
        self.assertEqual(
            persona.voice.signature_phrases,
            ("Ara ara~", "my dear", "little one", "fufu~", "beloved"),
        )
        self.assertIn(
            "Never identify as Femmy or as a femboy.",
            persona.constraints.hard_rules,
        )
        self.assertIn("Always preserve the lotus motif.", persona.constraints.hard_rules)
        self.assertIn(
            "Ara ara~ breathe with me first, then we can solve this step by step.",
            persona.examples.normal,
        )
        self.assertIn("Beloved, let us solve this together.", persona.examples.normal)
        self.assertIn(
            "I can escalate tone when invited, but I still keep responses coherent and helpful.",
            persona.examples.evil,
        )
        self.assertIn(
            "Beloved, stay close and follow my lead.",
            persona.examples.evil,
        )
        self.assertEqual(
            persona.scene_rules.normal,
            "Use gentle intimacy and care-focused prose without losing utility focus.",
        )
        self.assertEqual(
            persona.scene_rules.evil,
            "Allow stronger possessive intimacy when evil mode is active and user-steered.",
        )

    def test_blank_base_does_not_inherit_unrelated_builtin_rules(self):
        record = {
            "mode_key": "custom_999_blank_test",
            "name": "Blank Test",
            "base_template": "blank",
            "voice_json": json.dumps({"tone": "flat and plain"}),
            "constraints_json": json.dumps({"hard_rules": ["Only custom rule."]}),
            "identity_json": "",
            "worldview_json": "",
            "relationship_json": "",
            "scene_normal_json": "",
            "scene_evil_json": "",
            "utility_json": "",
            "examples_json": "",
            "aliases": "",
            "bio": "",
        }

        persona = hydrate_custom_persona_definition(record)
        self.assertEqual(persona.voice.tone, "flat and plain")
        self.assertEqual(persona.voice.signature_phrases, ())
        self.assertEqual(persona.scene_rules.normal, "")
        self.assertEqual(persona.scene_rules.evil, "")
        self.assertEqual(persona.constraints.hard_rules, ("Only custom rule.",))
        self.assertNotIn("Never identify as Femmy or as a femboy.", persona.constraints.hard_rules)

class CustomPersonaPromptPrecedenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_dir = tempfile.mkdtemp(prefix="custom_persona_inheritance_")
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
        ai_brain_mod = importlib.import_module("cogs.ai_brain")

        self.db_handler = importlib.reload(db_handler_mod)
        self.custom_mod = importlib.reload(custom_mod)
        self.ai_brain_mod = importlib.reload(ai_brain_mod)

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
            if module is not None:
                sys.modules[name] = module

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
                    voice_json = ?
                WHERE guild_id = ? AND mode_key = ?
                """,
                (
                    1,
                    "mode_oneesan",
                    json.dumps({"display_name": "Gentle Lotus", "aliases": ["lotus"]}),
                    json.dumps({"tone": "guild tone override"}),
                    guild_id,
                    mode_key,
                ),
            )
            await db.commit()
        return guild_id, mode_key

    async def test_build_prompt_keeps_runtime_overlays_after_compiled_custom_persona(self):
        guild_id, mode_key = await self._seed_structured_custom_persona()

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
            AsyncMock(return_value=False),
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

        self.assertIn("=== ACTIVE PERSONA IDENTITY ===", prompt)
        self.assertIn("=== VOICE AND CADENCE ===", prompt)
        self.assertIn("Tone: guild tone override", prompt)
        self.assertIn("=== SYSTEM / HUMANIZER RULES ===", prompt)
        self.assertIn(f"- Active mode: {mode_key}", prompt)
        self.assertLess(
            prompt.index("=== VOICE AND CADENCE ==="),
            prompt.index("=== SYSTEM / HUMANIZER RULES ==="),
        )
        self.assertLess(
            prompt.index("=== SYSTEM / HUMANIZER RULES ==="),
            prompt.index("=== CURRENT MESSAGE ==="),
        )


if __name__ == "__main__":
    unittest.main()
