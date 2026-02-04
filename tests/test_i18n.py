import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.i18n import normalize_locale, t


class I18nTests(unittest.TestCase):
    def test_normalize_locale(self):
        self.assertEqual(normalize_locale("en-US"), "en")
        self.assertEqual(normalize_locale(None), "en")

    def test_fallback_to_en(self):
        value = t("usage.dashboard.title", locale="ja")
        self.assertEqual(value, "Usage Dashboard")


if __name__ == "__main__":
    unittest.main()
