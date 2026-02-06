from utils.emoji_helper import (
    count_emojis,
    count_emojis_in_multiple,
    extract_custom_emojis,
    extract_emojis,
    filter_custom_emojis,
    has_consecutive_emoji,
)


def test_extract_and_count_emojis():
    text = "hi :wave: 😀 :wave:"
    assert count_emojis(text) >= 3
    emojis = extract_emojis(text)
    assert ":wave:" in emojis
    assert "😀" in emojis


def test_has_consecutive_emoji():
    assert has_consecutive_emoji("wow :cat::cat::cat:", ":cat:", threshold=2) is True
    assert has_consecutive_emoji("wow :cat: hi :cat:", ":cat:", threshold=2) is False


def test_extract_and_filter_custom_emojis():
    text = "A :cat: B :dog: C :cat:"
    assert set(extract_custom_emojis(text)) == {":cat:", ":dog:"}
    assert filter_custom_emojis(text, {":cat:"}) == "A B :dog: C"


def test_count_emojis_in_multiple():
    total = count_emojis_in_multiple(["😀", ":wave: :wave:", "plain text"])
    assert total >= 3

