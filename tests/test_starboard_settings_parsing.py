import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.db_handler import _parse_starboard_triggers  # noqa: E402


def test_parse_starboard_triggers_splits_plain_text_list():
    assert _parse_starboard_triggers("⭐ 🌟,💫") == ["⭐", "🌟", "💫"]
