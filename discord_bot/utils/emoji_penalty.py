from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

from utils.emoji_helper import extract_custom_emojis, filter_custom_emojis


@dataclass(frozen=True)
class EmojiPenaltyConfig:
    enabled: bool = True
    lookback_count: int = 3
    max_emojis: int = 1


@dataclass(frozen=True)
class UniqueEmojiConfig:
    enabled: bool = True
    lookback_count: int = 5


def load_emoji_penalty_config() -> EmojiPenaltyConfig:
    enabled = str(os.getenv("EMOJI_PENALTY_ENABLED", "true")).lower() not in {
        "0",
        "false",
        "off",
        "no",
    }
    try:
        lookback = int(os.getenv("EMOJI_PENALTY_LOOKBACK", "3"))
    except ValueError:
        lookback = 3
    try:
        threshold = int(os.getenv("EMOJI_PENALTY_THRESHOLD", "1"))
    except ValueError:
        threshold = 1
    return EmojiPenaltyConfig(
        enabled=enabled,
        lookback_count=max(1, lookback),
        max_emojis=max(0, threshold),
    )


def load_unique_emoji_config() -> UniqueEmojiConfig:
    enabled = str(os.getenv("EMOJI_UNIQUE_ENABLED", "true")).lower() not in {
        "0",
        "false",
        "off",
        "no",
    }
    try:
        lookback = int(os.getenv("EMOJI_UNIQUE_LOOKBACK", "5"))
    except ValueError:
        lookback = 5
    return UniqueEmojiConfig(enabled=enabled, lookback_count=max(1, lookback))


def should_apply_emoji_penalty(
    recent_bot_messages: Sequence[str],
    config: EmojiPenaltyConfig | None = None,
) -> bool:
    cfg = config or load_emoji_penalty_config()
    if not cfg.enabled:
        return False
    if not recent_bot_messages:
        return False
    window = list(recent_bot_messages)[-cfg.lookback_count :]
    total_custom = sum(len(extract_custom_emojis(message)) for message in window)
    return total_custom > cfg.max_emojis


def get_recently_used_custom_emojis(
    recent_bot_messages: Sequence[str],
    config: UniqueEmojiConfig | None = None,
) -> set[str]:
    cfg = config or load_unique_emoji_config()
    if not cfg.enabled or not recent_bot_messages:
        return set()
    window = list(recent_bot_messages)[-cfg.lookback_count :]
    used: set[str] = set()
    for message in window:
        for emoji in extract_custom_emojis(message):
            used.add(emoji.lower())
    return used


def filter_duplicate_custom_emojis(
    generated_text: str,
    recent_bot_messages: Sequence[str],
    config: UniqueEmojiConfig | None = None,
) -> str:
    if not generated_text:
        return generated_text
    used = get_recently_used_custom_emojis(recent_bot_messages, config=config)
    if not used:
        return generated_text
    duplicates = {
        emoji for emoji in extract_custom_emojis(generated_text) if emoji.lower() in used
    }
    if not duplicates:
        return generated_text
    filtered = filter_custom_emojis(generated_text, duplicates)
    return filtered or generated_text

