import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.emoji_manager import EmojiManager  # noqa: E402


def _make_manager() -> EmojiManager:
    manager = EmojiManager(bot=object())
    manager.config = {
        "emojis": {
            "tada": {"usage": "name call excitement", "modes": ["all"], "conditions": {}},
            "sneakpeekcat": {"usage": "femmy mention", "modes": ["all"], "conditions": {}},
            "ban": {"usage": "ban action", "modes": ["all"], "conditions": {}},
            "mikucinema": {"usage": "sarcastic response", "modes": ["all"], "conditions": {}},
            "thisisfinefrog": {"usage": "user is rude", "modes": ["all"], "conditions": {}},
            "pout": {"usage": "annoyed", "modes": ["all"], "conditions": {}},
            "what": {"usage": "shocked response", "modes": ["all"], "conditions": {}},
            "inlovehearts": {
                "usage": "very affectionate",
                "modes": ["all"],
                "conditions": {"min_affection": 800},
            },
            "twin_spin": {
                "usage": "excited response",
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


def test_build_prompt_section_uses_shortcode_format_only():
    manager = _make_manager()
    manager._validated_general = ["<:erm:123123>"]
    prompt = manager.build_prompt_section(mode="mode_femboy", affection=0, evil_mode=False)

    assert ":tada:" in prompt
    assert ":erm:" in prompt
    assert "<a:tada:111111>" not in prompt
    assert "<:erm:123123>" not in prompt


def test_select_trigger_emojis_prefers_negative_context_over_name_mention():
    manager = _make_manager()
    selected = manager.select_trigger_emojis(
        response_text="Please stop being rude.",
        user_text="femmy you're stupid",
        mode="mode_femboy",
        affection=0,
        evil_mode=False,
        max_emojis=2,
    )

    assert "<:thisisfinefrog:555555>" in selected
    assert "<a:tada:111111>" not in selected


def test_select_trigger_emojis_includes_affectionate_match_when_high_affection():
    manager = _make_manager()
    selected = manager.select_trigger_emojis(
        response_text="Aww love you too",
        user_text="love you femmy",
        mode="mode_femboy",
        affection=900,
        evil_mode=False,
        max_emojis=2,
    )

    assert "<:inlovehearts:888888>" in selected
    assert "<:thisisfinefrog:555555>" not in selected


def test_apply_trigger_emojis_respects_existing_shortcode_quota():
    manager = _make_manager()
    response = manager.apply_trigger_emojis(
        response_text="Already has :tada:",
        user_text="wow femmy omg",
        mode="mode_femboy",
        affection=900,
        evil_mode=False,
        max_emojis=1,
    )

    assert response == "Already has :tada:"
