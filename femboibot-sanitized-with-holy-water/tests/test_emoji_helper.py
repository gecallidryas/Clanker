from utils.emoji_helper import (
    count_emojis,
    count_emojis_in_multiple,
    extract_custom_emojis,
    extract_emojis,
    filter_custom_emojis,
    has_consecutive_emoji,
)


def test_extract_and_count_emojis():
    text = "hi :wave: \U0001F600 :wave:"
    assert count_emojis(text) >= 3
    emojis = extract_emojis(text)
    assert ":wave:" in emojis
    assert "\U0001F600" in emojis


def test_has_consecutive_emoji():
    assert has_consecutive_emoji("wow :cat::cat::cat:", ":cat:", threshold=2) is True
    assert has_consecutive_emoji("wow :cat: hi :cat:", ":cat:", threshold=2) is False


def test_extract_and_filter_custom_emojis():
    text = "A :cat: B :dog: C :cat:"
    assert set(extract_custom_emojis(text)) == {":cat:", ":dog:"}
    assert filter_custom_emojis(text, {":cat:"}) == "A B :dog: C"


def test_extract_and_filter_discord_custom_emoji_tags():
    text = "A <a:tada:123456> B <:cat:654321> C <a:tada:123456>"
    assert set(extract_custom_emojis(text)) == {"<a:tada:123456>", "<:cat:654321>"}
    assert filter_custom_emojis(text, {"<a:tada:123456>"}) == "A B <:cat:654321> C"


def test_count_emojis_in_multiple():
    total = count_emojis_in_multiple(["\U0001F600", ":wave: :wave:", "plain text"])
    assert total >= 3
