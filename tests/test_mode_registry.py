import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from modes import get_all_modes, get_mode_profile, resolve_mode_key


class ModeRegistryTests(unittest.TestCase):
    def test_registry_has_expected_modes(self):
        profiles = get_all_modes()
        self.assertGreaterEqual(len(profiles), 3)
        keys = {profile.key for profile in profiles}
        self.assertIn("mode_femboy", keys)
        self.assertIn("mode_tsundere", keys)
        self.assertIn("mode_oneesan", keys)

    def test_resolve_mode_key(self):
        self.assertEqual(resolve_mode_key("femboy"), "mode_femboy")
        self.assertEqual(resolve_mode_key("tsundere"), "mode_tsundere")
        self.assertEqual(resolve_mode_key("oneesan"), "mode_oneesan")

    def test_profile_fields(self):
        profile = get_mode_profile("mode_femboy")
        self.assertTrue(profile.prompt_file)
        self.assertTrue(profile.evil_prompt_file)
        self.assertTrue(profile.display_name)
        self.assertTrue(profile.description)

    def test_unknown_mode_returns_none(self):
        self.assertIsNone(resolve_mode_key("custom_123_missing"))
