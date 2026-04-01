from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from utils.expression_cache import get_expression_service
from utils.expression_sync import fetch_application_emojis_live, fetch_guild_assets_live
from utils.logger import get_logger

logger = get_logger(__name__)

FEMMY_EMOJI_PREFIX = "femmy"
YUMI_EMOJI_PREFIX = "yumi"
DISCORD_API_BASE = "https://discord.com/api/v10"


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
    service = get_expression_service(bot)
    if service is not None:
        return list(await service.get_application_emojis())
    return list(await fetch_application_emojis_live(bot))


async def get_guild_emojis(bot, guild) -> List:
    if not guild:
        return []
    service = get_expression_service(bot)
    if service is not None:
        return list(await service.get_guild_emojis(guild))
    emojis, _stickers = await fetch_guild_assets_live(guild)
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
_NAME_NO_TRAIL_PATTERN = re.compile(r"(?<!<a)(?<!<):([a-zA-Z0-9_]+)(?=$|[\s.,!?;)\]\}])")
_NAME_ID_PATTERN = re.compile(r"(?<!<a:)(?<!<:)(?<!<)([a-zA-Z0-9_]+):([0-9]{5,})")
_BROKEN_CUSTOM_TAG_PATTERN = re.compile(r"<a?:([^>]+)>")


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
    id_lookup: Dict[str, str] = {}
    for emoji in combined:
        emoji_id = getattr(emoji, "id", None)
        token = format_custom_emoji(emoji)
        if emoji_id and token:
            id_lookup[str(emoji_id)] = token

    def replace_name(match):
        name = match.group(1).lower()
        return lookup.get(name, match.group(0))

    def replace_name_no_trailing_colon(match):
        name = match.group(1).lower()
        return lookup.get(name, match.group(0))

    def replace_name_id(match):
        name = match.group(1).lower()
        emoji_id = match.group(2)
        return lookup.get(name) or id_lookup.get(emoji_id, match.group(0))

    def replace_broken_tag(match):
        name_raw = match.group(1)
        if re.fullmatch(r"[A-Za-z0-9_]+:\d{5,}", name_raw.strip()):
            return match.group(0)
        name = name_raw.lower()
        token = lookup.get(name)
        if token:
            return token
        stripped = (name_raw or "").strip().strip(":")
        if re.fullmatch(r"[A-Za-z0-9_]+", stripped):
            return f":{stripped}:"
        emoji_tail = re.sub(r"^[A-Za-z0-9_\-]+", "", stripped).strip()
        if emoji_tail:
            if re.fullmatch(r":[A-Za-z0-9_]+", emoji_tail):
                return f"{emoji_tail}:"
            return emoji_tail
        return stripped or name_raw

    text = _BROKEN_CUSTOM_TAG_PATTERN.sub(replace_broken_tag, text)
    if lookup or id_lookup:
        text = _NAME_ID_PATTERN.sub(replace_name_id, text)
        text = _NAME_PATTERN.sub(replace_name, text)
        text = _NAME_NO_TRAIL_PATTERN.sub(replace_name_no_trailing_colon, text)
    return text
