import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOCIAL_PATH = ROOT / "discord_bot" / "cogs" / "social.py"


class SocialModuleSyntaxTests(unittest.TestCase):
    def test_social_module_has_no_merge_markers_and_parses(self) -> None:
        source = SOCIAL_PATH.read_text(encoding="utf-8-sig")
        self.assertIsNone(
            re.search(r"^(<<<<<<< .+|=======$|>>>>>>> .+)$", source, flags=re.MULTILINE)
        )
        ast.parse(source)


if __name__ == "__main__":
    unittest.main()
