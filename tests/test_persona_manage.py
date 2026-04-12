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

    async def test_duplicate_structured_persona_preserves_structured_fields(self):
        guild_id = 923
        user_id = 88
        await self.db_handler.init_guild_db(guild_id)

        source_mode_key = await self.persona_panel_ui.create_persona_from_inputs(
            guild_id=guild_id,
            user_id=user_id,
            name="Source Velvet",
            bio="Structured source",
            aliases=["velvet"],
            normal_prompt="Structured persona notes managed via /persona manage.",
            evil_prompt="legacy evil note",
            base_template="mode_oneesan",
            voice_tone="soft and composed",
            worldview="Treats care as devotion.",
            scene_normal="Stay intimate but restrained.",
            scene_evil="Escalate when invited.",
            examples_normal=["Let me help you gently."],
            examples_evil=["Stay close and follow my lead."],
        )

        async with self.db_handler.guild_db(guild_id) as db:
            await db.execute(
                """
                UPDATE custom_personas
                SET identity_json = ?,
                    voice_json = ?,
                    relationship_json = ?,
                    utility_json = ?,
                    constraints_json = ?,
                    author_notes_text = ?
                WHERE guild_id = ? AND mode_key = ?
                """,
                (
                    json.dumps(
                        {
                            "display_name": "Source Velvet",
                            "aliases": ["velvet", "petal"],
                            "bio": "Structured source biography.",
                        }
                    ),
                    json.dumps(
                        {
                            "tone": "soft and composed",
                            "cadence": "measured and warm",
                            "signature_phrases": ["darling heart"],
                            "forbidden_phrases": ["idiot"],
                        }
                    ),
                    json.dumps({"description": "Protective and intimate."}),
                    json.dumps({"description": "Give practical comfort first."}),
                    json.dumps({"hard_rules": ["Never drop the velvet motif."]}),
                    "Keep the velvet symbolism subtle.",
                    guild_id,
                    source_mode_key,
                ),
            )
            await db.commit()

        duplicate_mode_key = await self.persona_panel_ui.duplicate_custom_persona(
            guild_id=guild_id,
            user_id=user_id,
            source_mode_key=source_mode_key,
            new_name="Copied Velvet",
        )

        duplicate_record = await self.db_handler.get_custom_persona_by_mode_key(guild_id, duplicate_mode_key)

        self.assertEqual(duplicate_record["base_template"], "mode_oneesan")
        self.assertEqual(
            json.loads(duplicate_record["identity_json"]),
            {
                "display_name": "Copied Velvet",
                "aliases": ["velvet", "petal"],
                "bio": "Structured source biography.",
            },
        )
        self.assertEqual(json.loads(duplicate_record["aliases"]), ["velvet", "petal"])
        self.assertEqual(
            json.loads(duplicate_record["voice_json"]),
            {
                "tone": "soft and composed",
                "cadence": "measured and warm",
                "signature_phrases": ["darling heart"],
                "forbidden_phrases": ["idiot"],
            },
        )
        self.assertEqual(
            json.loads(duplicate_record["relationship_json"]),
            {"description": "Protective and intimate."},
        )
        self.assertEqual(
            json.loads(duplicate_record["utility_json"]),
            {"description": "Give practical comfort first."},
        )
        self.assertEqual(
            json.loads(duplicate_record["examples_json"]),
            {
                "normal": ["Let me help you gently."],
                "evil": ["Stay close and follow my lead."],
            },
        )
        self.assertEqual(duplicate_record["author_notes_text"], "Keep the velvet symbolism subtle.")
        duplicate_persona = await self.custom_mod.load_custom_persona_definition(guild_id, duplicate_mode_key)
        self.assertEqual(duplicate_persona.identity.display_name, "Copied Velvet")
        self.assertIn("velvet", duplicate_persona.identity.aliases)
        self.assertIn("petal", duplicate_persona.identity.aliases)
        self.assertEqual(duplicate_persona.voice.cadence, "measured and warm")
        self.assertIn("darling heart", duplicate_persona.voice.signature_phrases)
        self.assertIn("idiot", duplicate_persona.voice.forbidden_phrases)
        self.assertEqual(duplicate_persona.relationship.description, "Protective and intimate.")
        self.assertEqual(duplicate_persona.utility.description, "Give practical comfort first.")
        self.assertIn("Never drop the velvet motif.", duplicate_persona.constraints.hard_rules)

    async def test_structured_modal_chain_captures_evil_examples_and_notes(self):
        guild_id = 924
        user_id = 44
        await self.db_handler.init_guild_db(guild_id)

        pending = self.persona_mod.PendingPersona(
            name="Modal Velvet",
            bio="Bio",
            avatar_url="https://example.com/avatar.png",
            banner_url=None,
            aliases=["velvet"],
            normal_prompt=None,
            evil_prompt=None,
            created_at=datetime.utcnow(),
        )
        self.persona_cog.store_pending(guild_id, user_id, pending)

        structured_modal = self.persona_mod.PersonaNormalPromptModal(self.persona_cog, guild_id, user_id)
        structured_modal.base_template._value = "oneesan"
        structured_modal.voice_tone._value = "soft and composed"
        structured_modal.worldview._value = "Treats care as devotion."
        structured_modal.scene_normal._value = "Stay intimate but restrained."
        structured_modal.examples_normal._value = "Let me help you gently.\nBreathe with me first."

        structured_interaction = FakeInteraction(user_id=user_id, guild=FakeGuild(id=guild_id))
        await structured_modal.on_submit(structured_interaction)

        updated_pending = self.persona_cog.get_pending(guild_id, user_id)
        self.assertEqual(updated_pending.base_template, "mode_oneesan")
        self.assertEqual(updated_pending.examples_normal, ("Let me help you gently.", "Breathe with me first."))
        continue_view = structured_interaction.response.messages[-1]["view"]
        self.assertIsInstance(continue_view, self.persona_mod.ContinueToEvilPromptsView)

        evil_modal_interaction = FakeInteraction(user_id=user_id, guild=FakeGuild(id=guild_id))
        await continue_view.children[0].callback(evil_modal_interaction)
        evil_modal = evil_modal_interaction.response.modal
        self.assertIsInstance(evil_modal, self.persona_mod.PersonaEvilPromptModal)

        evil_modal.scene_evil._value = "Escalate when invited."
        evil_modal.examples_evil._value = "Stay close.\nFollow my lead."
        evil_modal.normal_prompt_notes._value = "raw normal notes"
        evil_modal.evil_prompt_notes._value = "raw evil notes"

        evil_interaction = FakeInteraction(user_id=user_id, guild=FakeGuild(id=guild_id))
        await evil_modal.on_submit(evil_interaction)

        updated_pending = self.persona_cog.get_pending(guild_id, user_id)
        self.assertEqual(updated_pending.scene_evil, "Escalate when invited.")
        self.assertEqual(updated_pending.examples_evil, ("Stay close.", "Follow my lead."))
        self.assertEqual(updated_pending.normal_prompt, "raw normal notes")
        self.assertEqual(updated_pending.evil_prompt, "raw evil notes")


if __name__ == "__main__":
    unittest.main()
