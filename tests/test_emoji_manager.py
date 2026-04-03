import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.emoji_manager import EmojiManager  # noqa: E402


def _make_manager() -> EmojiManager:
    manager = EmojiManager(bot=object())
    manager.config = {
        "emojis": {
            "tada": {"usage": "celebrating success, hype, and excited wins", "modes": ["all"], "conditions": {}},
            "sneakpeekcat": {"usage": "playful cute teasing when femmy is mentioned", "modes": ["all"], "conditions": {}},
            "ban": {"usage": "moderation or banning someone", "modes": ["all"], "conditions": {}},
            "mikucinema": {"usage": "sarcastic dramatic or smug reaction", "modes": ["all"], "conditions": {}},
            "thisisfinefrog": {"usage": "annoyed or hostile reaction when someone is rude", "modes": ["all"], "conditions": {}},
            "pout": {"usage": "mildly annoyed pouty reaction", "modes": ["all"], "conditions": {}},
            "what": {"usage": "shocked surprised confused reaction", "modes": ["all"], "conditions": {}},
            "inlovehearts": {
                "usage": "warm affectionate loving reaction",
                "modes": ["all"],
                "conditions": {"min_affection": 800},
            },
            "twin_spin": {
                "usage": "very excited celebratory energy",
                "modes": ["all"],
                "conditions": {"min_affection": 500},
            },
        },
        "general_emojis": [],
    }
    manager._validated_emojis = {
        "tada": "<a:tada:111111>",
        "sneakpeekcat": "<a:sneakpeekcat:222222>",
        "ban": "<a:ban:333333>",
        "mikucinema": "<:mikucinema:444444>",
        "thisisfinefrog": "<:thisisfinefrog:555555>",
        "pout": "<:pout:666666>",
        "what": "<:what:777777>",
        "inlovehearts": "<:inlovehearts:888888>",
        "twin_spin": "<a:twin_spin:999999>",
    }
    return manager


def test_pick_contextual_emoji_returns_none_for_neutral_reply():
    manager = _make_manager()

    selected = manager.pick_contextual_emoji(
        response_text="I updated the channel setting.",
        user_text="can you change the setting",
        mode="mode_femboy",
        affection=0,
        evil_mode=False,
    )

    assert selected == ""


def test_pick_contextual_emoji_prefers_celebratory_match():
    manager = _make_manager()

    selected = manager.pick_contextual_emoji(
        response_text="We actually did it! Let's go!",
        user_text="omg femmy you actually did it",
        mode="mode_femboy",
        affection=600,
        evil_mode=False,
    )

    assert selected in {"<a:tada:111111>", "<a:twin_spin:999999>"}


def test_pick_contextual_emoji_prefers_annoyed_match_over_positive_name_mention():
    manager = _make_manager()

    selected = manager.pick_contextual_emoji(
        response_text="Watch your tone.",
        user_text="femmy you're so annoying and rude",
        mode="mode_femboy",
        affection=0,
        evil_mode=False,
    )

    assert selected == "<:thisisfinefrog:555555>"


def test_strip_known_shortcodes_removes_bot_owned_custom_emoji_names():
    manager = _make_manager()
    manager._validated_general = ["<:erm:777777>"]

    stripped = manager.strip_known_shortcodes("still learning :erm: and :tada: today")

    assert stripped == "still learning and today"


def test_append_contextual_emoji_adds_one_validated_token():
    manager = _make_manager()

    response = manager.append_contextual_emoji(
        response_text="That was adorable, not gonna lie.",
        user_text="femmy did you see that",
        mode="mode_femboy",
        affection=0,
        evil_mode=False,
    )

    assert response.endswith("<a:sneakpeekcat:222222>")
