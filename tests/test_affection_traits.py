import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.affection_traits import parse_persona_traits, extract_persona_traits


class AffectionTraitParseTests(unittest.TestCase):
    def test_parse_traits_with_meta(self):
        prompt = (
            "+likes talking about flowers (+10, one_time, keywords: flowers, roses)\n"
            "+dislikes rude behavior (-5, repeatable, keywords: rude, mean)"
        )
        traits = parse_persona_traits(prompt)
        by_key = {trait["trait_key"]: trait for trait in traits}

        self.assertIn("talking_about_flowers", by_key)
        self.assertEqual(by_key["talking_about_flowers"]["points_value"], 10)
        self.assertTrue(by_key["talking_about_flowers"]["one_time"])
        self.assertEqual(by_key["talking_about_flowers"]["trigger_terms"], ["flowers", "roses"])

        self.assertIn("rude_behavior", by_key)
        self.assertEqual(by_key["rude_behavior"]["points_value"], -5)
        self.assertFalse(by_key["rude_behavior"]["one_time"])
        self.assertEqual(by_key["rude_behavior"]["trigger_terms"], ["rude", "mean"])

    def test_extract_merges_prompts(self):
        normal = "+likes coffee (+10)"
        evil = "+likes coffee (+5)\n+likes sunsets (+10)"
        traits = extract_persona_traits(normal, evil)
        by_key = {trait["trait_key"]: trait for trait in traits}

        self.assertEqual(by_key["coffee"]["points_value"], 5)
        self.assertIn("sunsets", by_key)


if __name__ == "__main__":
    unittest.main()
