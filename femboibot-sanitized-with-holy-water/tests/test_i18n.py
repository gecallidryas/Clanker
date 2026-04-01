import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.i18n import normalize_locale, t


class I18nTests(unittest.TestCase):
    def test_normalize_locale(self):
        self.assertEqual(normalize_locale("en-US"), "en")
        self.assertEqual(normalize_locale(None), "en")

    def test_missing_locale_falls_back_to_en(self):
        value = t("usage.dashboard.title", locale="fr")
        self.assertEqual(value, "Usage Dashboard")

    def test_ja_translation_lookup(self):
        value = t("usage.dashboard.title", locale="ja")
        self.assertEqual(value, "利用状況ダッシュボード")

    def test_ja_locale_contains_all_en_keys(self):
        locales_dir = ROOT / "discord_bot" / "locales"
        en = json.loads((locales_dir / "en.json").read_text(encoding="utf-8-sig"))
        ja = json.loads((locales_dir / "ja.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(sorted(set(en) - set(ja)), [])


if __name__ == "__main__":
    unittest.main()
