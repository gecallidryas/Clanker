import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.app_emojis import replace_custom_emojis  # noqa: E402
from utils.emoji_manager import EmojiManager  # noqa: E402


class _FakeEmoji:
    def __init__(self, name: str, emoji_id: int, animated: bool = False):
        self.name = name
        self.id = emoji_id
        self.animated = animated


def test_replace_custom_emojis_repairs_prefixed_broken_tags():
    emojis = [
        _FakeEmoji("happyemoji", 444444, animated=True),
        _FakeEmoji("eyebrowflashsmirk", 555555, animated=True),
    ]
    text = "<:h:happyemoji:> <:e:eyebrowflashsmirk:>"
    replaced = replace_custom_emojis(text, emojis)
    assert "<a:happyemoji:444444>" in replaced
    assert "<a:eyebrowflashsmirk:555555>" in replaced


def test_replace_custom_emojis_replaces_known_dangling_shortcode():
    emojis = [_FakeEmoji("erm", 666666)]
    text = "oops :erm"
    replaced = replace_custom_emojis(text, emojis)
    assert replaced == "oops <:erm:666666>"


def test_emoji_manager_replaces_known_dangling_shortcode():
    manager = EmojiManager(bot=object())
    manager._validated_emojis = {}
    manager._validated_general = ["<:erm:777777>"]
    replaced = manager.replace_shortcodes("still learning :erm")
    assert replaced == "still learning <:erm:777777>"
