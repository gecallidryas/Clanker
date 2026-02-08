from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Dict, Iterable, List, Optional

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

    if not emojis:
        application_id = getattr(bot, "application_id", None) or getattr(getattr(bot, "application", None), "id", None)
        token = getattr(getattr(bot, "http", None), "token", None)
        if application_id and token:
            try:
                import aiohttp

                url = f"{DISCORD_API_BASE}/applications/{application_id}/emojis"
                headers = {"Authorization": f"Bot {token}"}
                timeout = aiohttp.ClientTimeout(total=12)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status >= 400:
                            body = await response.text()
                            raise RuntimeError(f"HTTP {response.status}: {body[:200]}")
                        payload = await response.json()
                items = payload.get("items", []) if isinstance(payload, dict) else []
                emojis = [
                    SimpleNamespace(
                        id=int(item.get("id")),
                        name=str(item.get("name") or ""),
                        animated=bool(item.get("animated", False)),
                    )
                    for item in items
                    if item.get("id") and item.get("name")
                ]
            except Exception as exc:
                logger.warning("Failed REST fallback for application emojis: %s", exc)
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
_BROKEN_CUSTOM_TAG_PATTERN = re.compile(r"<a?:([A-Za-z0-9_]+)(?::)?>")


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
    id_lookup: Dict[str, str] = {}
    for emoji in combined:
        emoji_id = getattr(emoji, "id", None)
        token = format_custom_emoji(emoji)
        if emoji_id and token:
            id_lookup[str(emoji_id)] = token

    def replace_name(match):
        name = match.group(1).lower()
        return lookup.get(name, match.group(0))

    def replace_name_id(match):
        name = match.group(1).lower()
        emoji_id = match.group(2)
        return lookup.get(name) or id_lookup.get(emoji_id, match.group(0))

    def replace_broken_tag(match):
        name_raw = match.group(1)
        name = name_raw.lower()
        token = lookup.get(name)
        if token:
            return token
        return f":{name_raw}:"

    text = _BROKEN_CUSTOM_TAG_PATTERN.sub(replace_broken_tag, text)
    text = _NAME_ID_PATTERN.sub(replace_name_id, text)
    return _NAME_PATTERN.sub(replace_name, text)
