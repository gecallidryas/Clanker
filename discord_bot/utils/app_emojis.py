from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

FEMMY_EMOJI_PREFIX = "femmy"
YUMI_EMOJI_PREFIX = "yumi"
BEAR_EMOJI_PREFIX = "bear"



def clean_emoji_name(name: str) -> str:
    """Remove digits and hyphens for display-only names."""
    cleaned = re.sub(r"[-0-9]+", "", name or "")
    return cleaned.strip() or (name or "")


def format_custom_emoji(emoji) -> str:
    name = getattr(emoji, "name", "")
    emoji_id = getattr(emoji, "id", None)
    if not name or not emoji_id:
        return ""
    if getattr(emoji, "animated", False):
        return f"<a:{name}:{emoji_id}>"
    return f"<:{name}:{emoji_id}>"


def filter_emojis_by_prefix(emojis: Iterable, prefix: str) -> List:
    prefix_lower = (prefix or "").lower()
    if not prefix_lower:
        return list(emojis)
    filtered = []
    for emoji in emojis:
        name = (getattr(emoji, "name", "") or "").lower()
        if name.startswith(prefix_lower):
            filtered.append(emoji)
    return filtered


async def get_application_emojis(bot) -> List:
    cached = getattr(bot, "_app_emojis_cache", None)
    if cached is not None:
        return list(cached)

    emojis: List = []
    existing = getattr(bot, "application_emojis", None)
    if existing:
        try:
            emojis = list(existing)
        except Exception:
            emojis = []

    if not emojis:
        fetcher = getattr(bot, "fetch_application_emojis", None)
        if fetcher:
            try:
                emojis = await fetcher()
            except Exception as exc:
                logger.warning("Failed to fetch application emojis: %s", exc)
                emojis = []

    setattr(bot, "_app_emojis_cache", list(emojis))
    return list(emojis)


async def get_guild_emojis(bot, guild) -> List:
    if not guild:
        return []
    cache = getattr(bot, "_guild_emojis_cache", None)
    if cache is None:
        cache = {}
        setattr(bot, "_guild_emojis_cache", cache)
    if guild.id in cache:
        return list(cache[guild.id])

    emojis: List = []
    try:
        emojis = list(getattr(guild, "emojis", []) or [])
    except Exception:
        emojis = []

    if not emojis:
        fetcher = getattr(guild, "fetch_emojis", None)
        if fetcher:
            try:
                emojis = await fetcher()
            except Exception as exc:
                logger.warning("Failed to fetch guild emojis: %s", exc)
                emojis = []

    cache[guild.id] = list(emojis)
    return list(emojis)


def build_emoji_lookup(emojis: Iterable) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for emoji in emojis:
        name = getattr(emoji, "name", None)
        if not name:
            continue
        token = format_custom_emoji(emoji)
        if token:
            lookup[name.lower()] = token
    return lookup


_NAME_PATTERN = re.compile(r"(?<!<a)(?<!<):([a-zA-Z0-9_]+):")
_NAME_ID_PATTERN = re.compile(r"(?<!<a:)(?<!<:)(?<!<)([a-zA-Z0-9_]+):([0-9]{5,})")


def replace_custom_emojis(
    text: str,
    emojis: Iterable,
    extra_emojis: Optional[Iterable] = None,
) -> str:
    """Replace :name: or name:123 patterns with proper emoji tokens."""
    if not text:
        return text
    combined = list(emojis or [])
    if extra_emojis:
        combined.extend(list(extra_emojis))
    lookup = build_emoji_lookup(combined)
    if not lookup:
        return text

    def replace_name(match):
        name = match.group(1).lower()
        return lookup.get(name, match.group(0))

    def replace_name_id(match):
        name = match.group(1).lower()
        return lookup.get(name, match.group(0))

    text = _NAME_ID_PATTERN.sub(replace_name_id, text)
    return _NAME_PATTERN.sub(replace_name, text)
