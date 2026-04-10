import importlib
import json
import os
import shutil
import sys
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tests.helpers.discord_fakes import FakeGuild, FakeInteraction

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp_tests"
TMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "discord_bot"))


class _FakeBot(SimpleNamespace):
    def __init__(self):
        super().__init__(get_cog=lambda _name: None)


class PersonaManageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_path = TMP_ROOT / f"persona_manage_{uuid.uuid4().hex}"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        os.environ["DATABASE_DIR"] = str(self._tmp_path)
        os.environ["GLOBAL_DATABASE_PATH"] = str(self._tmp_path / "global.db")

        self._saved_modules = {
            name: sys.modules.get(name)
            for name in (
                "aiosqlite",
                "utils.db_handler",
                "utils.persona_panel_ui",
                "cogs.persona",
                "personas.custom",
            )
        }

        for name in self._saved_modules:
            sys.modules.pop(name, None)

        import aiosqlite  # noqa: F401

        db_handler_mod = importlib.import_module("utils.db_handler")
        persona_panel_ui_mod = importlib.import_module("utils.persona_panel_ui")
        persona_mod = importlib.import_module("cogs.persona")
        custom_mod = importlib.import_module("personas.custom")

        self.db_handler = importlib.reload(db_handler_mod)
        self.persona_panel_ui = importlib.reload(persona_panel_ui_mod)
        self.persona_mod = importlib.reload(persona_mod)
        self.custom_mod = importlib.reload(custom_mod)
        self.persona_cog = self.persona_mod.Persona(_FakeBot())

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._tmp_path, ignore_errors=True)
        for name in self._saved_modules:
            sys.modules.pop(name, None)
        for name, module in self._saved_modules.items():
            package_name, _, attr_name = name.rpartition(".")
            package = sys.modules.get(package_name)
            if module is not None:
                sys.modules[name] = module
                if package is not None and attr_name:
                    setattr(package, attr_name, module)
                continue
            if package is not None and attr_name and hasattr(package, attr_name):
                delattr(package, attr_name)

    async def test_finalize_pending_persona_creates_structured_persona(self):
        guild_id = 921
        user_id = 73
        await self.db_handler.init_guild_db(guild_id)

        pending = self.persona_mod.PendingPersona(
            name="Velvet",
            bio="Structured bio",
            avatar_url="https://example.com/avatar.png",
            banner_url=None,
            aliases=["velvet"],
            normal_prompt=None,
            evil_prompt=None,
            base_template="mode_oneesan",
            voice_tone="soft and composed",
            worldview="Treats care as devotion.",
            scene_normal="Stay intimate but restrained.",
            scene_evil="Escalate when invited.",
            example_replies=["Let me help you gently.", "Breathe with me first."],
            created_at=datetime.utcnow(),
        )
        self.persona_cog.store_pending(guild_id, user_id, pending)

        interaction = FakeInteraction(user_id=user_id, guild=FakeGuild(id=guild_id))
        with patch(
            "cogs.persona.download_and_validate_image",
            AsyncMock(return_value=(True, "ok")),
        ):
            await self.persona_cog.finalize_pending_persona(interaction, guild_id, user_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Velvet")
        persona_record = await self.db_handler.get_custom_persona_by_mode_key(guild_id, mode_key)

        self.assertEqual(persona_record["base_template"], "mode_oneesan")
        self.assertEqual(json.loads(persona_record["voice_json"]), {"tone": "soft and composed"})
        self.assertEqual(
            json.loads(persona_record["worldview_json"]),
            {"description": "Treats care as devotion."},
        )
        self.assertEqual(
            json.loads(persona_record["scene_normal_json"]),
            {"normal": "Stay intimate but restrained."},
        )
        self.assertEqual(
            json.loads(persona_record["scene_evil_json"]),
            {"evil": "Escalate when invited."},
        )
        self.assertEqual(
            json.loads(persona_record["examples_json"]),
            {"normal": ["Let me help you gently.", "Breathe with me first."]},
        )

        persona = await self.custom_mod.load_custom_persona_definition(guild_id, mode_key)
        self.assertEqual(persona.voice.tone, "soft and composed")
        self.assertEqual(persona.worldview.description, "Treats care as devotion.")
        self.assertEqual(persona.scene_rules.normal, "Stay intimate but restrained.")
        self.assertEqual(persona.scene_rules.evil, "Escalate when invited.")
        self.assertIn("Let me help you gently.", persona.examples.normal)
        self.assertTrue(any("never identify as femmy" in rule.lower() for rule in persona.constraints.hard_rules))

        self.assertTrue(interaction.response.deferred)
        self.assertIn("Custom persona **Velvet** created!", interaction.followup.messages[-1]["content"])

    async def test_legacy_prompt_only_editing_remains_readable(self):
        guild_id = 922
        await self.db_handler.init_guild_db(guild_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Legacy Velvet")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Legacy Velvet",
            mode_key=mode_key,
            bio="Legacy bio",
            avatar_path=None,
            banner_path=None,
            normal_prompt="Legacy normal prompt text",
            evil_prompt="Legacy evil prompt text",
            created_by=99,
            aliases=["legacy"],
        )

        state = await self.persona_panel_ui.load_persona_panel_state(guild_id)
        entry = next(item for item in state.entries if item.mode_key == mode_key)

        modal = self.persona_panel_ui.PersonaPromptsModal(SimpleNamespace(guild_id=guild_id), entry)

        self.assertEqual(modal.normal_prompt_input.default, "Legacy normal prompt text")
        self.assertEqual(modal.evil_prompt_input.default, "Legacy evil prompt text")


if __name__ == "__main__":
    unittest.main()
