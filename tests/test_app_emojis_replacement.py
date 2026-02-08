import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.app_emojis import replace_custom_emojis  # noqa: E402


class _FakeEmoji:
    def __init__(self, name: str, emoji_id: int, animated: bool = False):
        self.name = name
        self.id = emoji_id
        self.animated = animated


def test_replace_custom_emojis_repairs_broken_custom_tags():
    emojis = [
        _FakeEmoji("WTAF", 111111),
        _FakeEmoji("BocchiStress", 222222, animated=True),
    ]
    text = "<:WTAF> hello <a:BocchiStress>"
    replaced = replace_custom_emojis(text, emojis)
    assert "<:WTAF:111111>" in replaced
    assert "<a:BocchiStress:222222>" in replaced


def test_replace_custom_emojis_name_id_falls_back_to_id_lookup():
    emojis = [_FakeEmoji("RealName", 333333)]
    text = "WrongName:333333"
    replaced = replace_custom_emojis(text, emojis)
    assert replaced == "<:RealName:333333>"
