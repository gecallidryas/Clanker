import importlib
import json
import os
import shutil
import sqlite3
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp_tests"
TMP_ROOT.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT / "discord_bot"))


class CustomPersonaSchemaTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp_path = TMP_ROOT / f"custom_persona_schema_{uuid.uuid4().hex}"
        self._tmp_path.mkdir(parents=True, exist_ok=True)
        os.environ["DATABASE_DIR"] = str(self._tmp_path)
        os.environ["GLOBAL_DATABASE_PATH"] = str(self._tmp_path / "global.db")

        sys.modules.pop("aiosqlite", None)
        import aiosqlite  # noqa: F401

        from utils import db_handler as db_handler_mod

        self.db_handler = importlib.reload(db_handler_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self._tmp_path, ignore_errors=True)

    async def test_init_guild_db_adds_structured_custom_persona_columns(self):
        guild_id = 201
        await self.db_handler.init_guild_db(guild_id)

        db_path = Path(self.db_handler.get_guild_db_path(guild_id))
        with sqlite3.connect(db_path) as conn:
            columns = {
                row[1]: row
                for row in conn.execute("PRAGMA table_info(custom_personas)").fetchall()
            }

        for column_name in (
            "schema_version",
            "base_template",
            "identity_json",
            "voice_json",
            "worldview_json",
            "relationship_json",
            "scene_normal_json",
            "scene_evil_json",
            "utility_json",
            "examples_json",
            "constraints_json",
            "author_notes_text",
            "normal_prompt",
            "evil_prompt",
        ):
            self.assertIn(column_name, columns)

    async def test_structured_custom_persona_loader_hydrates_canonical_runtime_shape(self):
        guild_id = 202
        await self.db_handler.init_guild_db(guild_id)

        mode_key = self.db_handler.build_custom_mode_key(guild_id, "Velvet")
        await self.db_handler.create_custom_persona(
            guild_id=guild_id,
            name="Velvet",
            mode_key=mode_key,
            bio="Legacy bio",
            avatar_path=None,
            banner_path=None,
            normal_prompt="Legacy normal prompt",
            evil_prompt="Legacy evil prompt",
            created_by=42,
            aliases=["velvet"],
        )

        identity_json = json.dumps(
            {
                "display_name": "Velvet",
                "aliases": ["velvet", "vel"],
                "bio": "Structured bio",
            }
        )
        voice_json = json.dumps(
            {
                "tone": "soft and composed",
                "signature_phrases": ["my star"],
            }
        )
        worldview_json = json.dumps({"description": "Treats care as devotion."})
        relationship_json = json.dumps({"description": "Warm and protective."})
        scene_normal_json = json.dumps({"normal": "Stay intimate but restrained."})
        examples_json = json.dumps({"normal": ["Let me help you gently."]})
        constraints_json = json.dumps({"hard_rules": ["Never drop the velvet motif."]})

        async with self.db_handler.guild_db(guild_id) as db:
            await db.execute(
                """
                UPDATE custom_personas
                SET schema_version = ?,
                    base_template = ?,
                    identity_json = ?,
                    voice_json = ?,
                    worldview_json = ?,
                    relationship_json = ?,
                    scene_normal_json = ?,
                    examples_json = ?,
                    constraints_json = ?
                WHERE guild_id = ? AND mode_key = ?
                """,
                (
                    1,
                    "mode_oneesan",
                    identity_json,
                    voice_json,
                    worldview_json,
                    relationship_json,
                    scene_normal_json,
                    examples_json,
                    constraints_json,
                    guild_id,
                    mode_key,
                ),
            )
            await db.commit()

        from personas.custom import load_custom_persona_definition

        persona = await load_custom_persona_definition(guild_id, mode_key)

        self.assertEqual(persona.key, mode_key)
        self.assertEqual(persona.identity.display_name, "Velvet")
        self.assertEqual(persona.identity.aliases, ("velvet", "vel"))
        self.assertEqual(persona.identity.bio, "Structured bio")
        self.assertEqual(persona.voice.tone, "soft and composed")
        self.assertEqual(
            persona.voice.signature_phrases,
            ("Ara ara~", "my dear", "little one", "fufu~", "my star"),
        )
        self.assertEqual(persona.worldview.description, "Treats care as devotion.")
        self.assertEqual(persona.relationship.description, "Warm and protective.")
        self.assertEqual(persona.scene_rules.normal, "Stay intimate but restrained.")
        self.assertEqual(
            persona.examples.normal,
            (
                "Ara ara~ breathe with me first, then we can solve this step by step.",
                "My dear, here is a clean checklist so you can finish this calmly.",
                "Let me help you gently.",
            ),
        )
        self.assertIn("Never identify as Femmy or as a femboy.", persona.constraints.hard_rules)
        self.assertIn("Never drop the velvet motif.", persona.constraints.hard_rules)
        self.assertEqual(
            persona.utility.description,
            "Remain highly useful, translate care into actionable advice, and use tools when relevant.",
        )
        self.assertEqual(
            persona.scene_rules.evil,
            "Allow stronger possessive intimacy when evil mode is active and user-steered.",
        )


if __name__ == "__main__":
    unittest.main()
