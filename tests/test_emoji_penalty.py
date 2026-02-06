from utils.emoji_penalty import (
    EmojiPenaltyConfig,
    UniqueEmojiConfig,
    filter_duplicate_custom_emojis,
    get_recently_used_custom_emojis,
    should_apply_emoji_penalty,
)


def test_should_apply_emoji_penalty_when_threshold_exceeded():
    messages = ["hi :a:", "yo :b:", "ok :c:"]
    config = EmojiPenaltyConfig(enabled=True, lookback_count=3, max_emojis=1)
    assert should_apply_emoji_penalty(messages, config=config) is True


def test_should_not_apply_emoji_penalty_when_disabled():
    messages = ["hi :a:", "yo :b:"]
    config = EmojiPenaltyConfig(enabled=False, lookback_count=3, max_emojis=0)
    assert should_apply_emoji_penalty(messages, config=config) is False


def test_get_recently_used_custom_emojis():
    messages = ["one :cat:", "two :dog:", "three :cat:"]
    config = UniqueEmojiConfig(enabled=True, lookback_count=2)
    assert get_recently_used_custom_emojis(messages, config=config) == {":dog:", ":cat:"}


def test_filter_duplicate_custom_emojis():
    recent = ["bot said :cat:", "another :dog:"]
    result = filter_duplicate_custom_emojis(
        "new response :cat: :bird:",
        recent,
        config=UniqueEmojiConfig(enabled=True, lookback_count=5),
    )
    assert ":cat:" not in result
    assert ":bird:" in result

