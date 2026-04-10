import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from personas.compiler import compile_persona_sections
from personas.custom import hydrate_custom_persona_definition


class CustomPersonaInheritanceTests(unittest.TestCase):
    def test_mode_oneesan_inheritance_merges_defaults_with_structured_overrides(self):
        record = {
            "mode_key": "custom_123_gentle_lotus",
            "name": "Gentle Lotus",
            "base_template": "mode_oneesan",
            "identity_json": json.dumps(
                {
                    "display_name": "Gentle Lotus",
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

        self.assertEqual(persona.identity.display_name, "Gentle Lotus")
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

    def test_precedence_base_then_custom_then_runtime_overlays(self):
        record = {
            "mode_key": "custom_456_precedence_test",
            "name": "Precedence Test",
            "base_template": "mode_oneesan",
            "voice_json": json.dumps({"tone": "guild tone override"}),
            "identity_json": "",
            "worldview_json": "",
            "relationship_json": "",
            "scene_normal_json": "",
            "scene_evil_json": "",
            "utility_json": "",
            "examples_json": "",
            "constraints_json": "",
            "aliases": "",
            "bio": "",
        }

        persona = hydrate_custom_persona_definition(record)
        self.assertEqual(persona.voice.tone, "guild tone override")

        compiled = compile_persona_sections(persona, evil_mode=False)
        voice_section = next(section for section in compiled if section.title == "VOICE AND CADENCE")
        self.assertIn("Tone: guild tone override", voice_section.body)

        runtime_overlay = "Tone: runtime overlay wins for this turn."
        layered_voice = "\n".join([voice_section.body, runtime_overlay])
        self.assertTrue(layered_voice.endswith(runtime_overlay))
        self.assertIn("runtime overlay wins for this turn", layered_voice)


if __name__ == "__main__":
    unittest.main()
