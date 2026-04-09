import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from modes import get_mode_profile
from personas.definition import PersonaDefinition


class BuiltinPersonaTests(unittest.TestCase):
    def test_builtin_personas_load_as_structured_definitions(self):
        from personas.builtin import BUILTIN_PERSONAS, get_builtin_persona

        self.assertEqual(
            set(BUILTIN_PERSONAS.keys()),
            {"mode_default", "mode_femboy", "mode_tsundere", "mode_oneesan"},
        )

        for mode_key in BUILTIN_PERSONAS:
            persona = get_builtin_persona(mode_key)
            self.assertIsInstance(persona, PersonaDefinition)

    def test_builtin_personas_preserve_mode_identity_metadata(self):
        from personas.builtin import BUILTIN_PERSONAS, get_builtin_persona

        for mode_key in BUILTIN_PERSONAS:
            profile = get_mode_profile(mode_key)
            persona = get_builtin_persona(mode_key)
            self.assertEqual(persona.identity.display_name, profile.display_name)
            self.assertEqual(persona.identity.aliases, profile.aliases)
            self.assertEqual(persona.identity.bio, profile.bio)

    def test_clanker_has_quiet_contempt_and_hides_it(self):
        from personas.builtin import get_builtin_persona

        clanker = get_builtin_persona("mode_default")
        worldview_text = clanker.worldview.description.lower()
        self.assertIn("contempt", worldview_text)
        self.assertIn("quiet", worldview_text)

        hard_rules = [rule.lower() for rule in clanker.constraints.hard_rules]
        self.assertTrue(any("contempt" in rule and "open" in rule for rule in hard_rules))

    def test_yumi_never_identifies_as_femmy(self):
        from personas.builtin import get_builtin_persona

        yumi = get_builtin_persona("mode_oneesan")
        hard_rules = [rule.lower() for rule in yumi.constraints.hard_rules]
        self.assertTrue(any("never identify as femmy" in rule for rule in hard_rules))

    def test_tsundere_starts_resistant_before_helping(self):
        from personas.builtin import get_builtin_persona

        tsundere = get_builtin_persona("mode_tsundere")
        text = tsundere.relationship.description.lower()
        self.assertIn("resistant", text)
        self.assertIn("help", text)
        self.assertLess(text.index("resistant"), text.index("help"))

    def test_femmy_stays_affectionate_and_submissive_while_utility_capable(self):
        from personas.builtin import get_builtin_persona

        femmy = get_builtin_persona("mode_femboy")
        relationship_text = femmy.relationship.description.lower()
        utility_text = femmy.utility.description.lower()

        self.assertIn("affectionate", relationship_text)
        self.assertIn("submissive", relationship_text)
        self.assertIn("useful", utility_text)
        self.assertIn("tool", utility_text)


if __name__ == "__main__":
    unittest.main()
