from utils.output_cleaner import (
    clean_llm_output,
    normalize_custom_emojis_for_llm,
    replace_mention_handles,
)


def test_normalize_custom_emojis_for_llm_skips_code():
    text = "Look <:wave:12345678901234567> `code <:keep:12345678901234567>`"
    normalized = normalize_custom_emojis_for_llm(text)
    assert ":wave:" in normalized
    assert "<:keep:12345678901234567>" in normalized


def test_replace_mention_handles():
    text = "hi @{alice} and @bob"
    mention_map = {"alice": ["123"], "bob": ["456"]}
    mention_ids = {"123", "456"}
    replaced = replace_mention_handles(text, mention_map=mention_map, mention_id_set=mention_ids)
    assert "<@123>" in replaced
    assert "<@456>" in replaced


def test_clean_llm_output_strips_system_and_bot_prefix():
    raw = "Tomori: [System: hidden]\nHello <|im_end|>"
    cleaned = clean_llm_output(raw, bot_name="Tomori")
    assert "[System:" not in cleaned
    assert not cleaned.startswith("Tomori:")
    assert "Hello" in cleaned


def test_clean_llm_output_removes_emoji_tags_when_disabled():
    raw = "text <:wave:12345678901234567>"
    cleaned = clean_llm_output(raw, emoji_usage_enabled=False)
    assert "<:wave:12345678901234567>" not in cleaned


def test_clean_llm_output_repairs_malformed_custom_tag_with_emoji_tail():
    raw = "Now <::e🙄> later <:f🥺>"
    cleaned = clean_llm_output(raw, emoji_usage_enabled=True)
    assert "🙄" in cleaned
    assert "🥺" in cleaned
    assert "<:f🥺>" not in cleaned


def test_clean_llm_output_repairs_malformed_custom_tag_to_shortcode():
    raw = "Hello <:WTAF>"
    cleaned = clean_llm_output(raw, emoji_usage_enabled=True)
    assert ":WTAF:" in cleaned
