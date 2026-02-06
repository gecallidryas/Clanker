from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set

# Normalized custom emoji form used in prompts/context.
CUSTOM_EMOJI_PATTERN = re.compile(r":[A-Za-z0-9_]+:")

# Broad unicode emoji ranges (not exhaustive, but stable without extra deps).
UNICODE_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FAFF"
    "\u2600-\u26FF"          # miscellaneous symbols
    "\u2700-\u27BF"          # dingbats
    "]",
    flags=re.UNICODE,
)

# Text emoticons frequently used in chat.
EMOTICON_PATTERN = re.compile(r"(?::\)|:D|:\(|:P|:p|;\)|:'\(|<3)")


def _find_all_emoji_tokens(text: str) -> list[str]:
    if not text:
        return []
    matches: list[tuple[int, str]] = []
    for pattern in (CUSTOM_EMOJI_PATTERN, UNICODE_EMOJI_PATTERN, EMOTICON_PATTERN):
        for match in pattern.finditer(text):
            matches.append((match.start(), match.group(0)))
    matches.sort(key=lambda item: item[0])
    return [token for _, token in matches]


def count_emojis(text: str) -> int:
    return len(_find_all_emoji_tokens(text))


def extract_emojis(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for token in _find_all_emoji_tokens(text):
        seen.setdefault(token, None)
    return list(seen.keys())


def has_consecutive_emoji(text: str, emoji: str, threshold: int = 2) -> bool:
    if not text or not emoji or threshold <= 1:
        return bool(text and emoji)
    escaped = re.escape(emoji)
    return bool(re.search(rf"(?:{escaped}){{{threshold},}}", text))


def count_emojis_in_multiple(texts: Sequence[str]) -> int:
    return sum(count_emojis(text) for text in texts)


def extract_custom_emojis(text: str) -> list[str]:
    if not text:
        return []
    seen: dict[str, None] = {}
    for match in CUSTOM_EMOJI_PATTERN.finditer(text):
        seen.setdefault(match.group(0), None)
    return list(seen.keys())


def filter_custom_emojis(text: str, emojis_to_remove: Set[str] | Iterable[str]) -> str:
    if not text:
        return text
    tokens = {token.lower() for token in emojis_to_remove}
    if not tokens:
        return text
    filtered = text
    for emoji in extract_custom_emojis(text):
        if emoji.lower() not in tokens:
            continue
        filtered = re.sub(re.escape(emoji), "", filtered, flags=re.IGNORECASE)
    filtered = re.sub(r"\s{2,}", " ", filtered).strip()
    return filtered

