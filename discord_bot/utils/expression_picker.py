from __future__ import annotations

import random
import time
from typing import Optional

import discord

CACHE_TTL_SECONDS = 300

_cache: dict[int, dict[str, object]] = {}


def _refresh_cache(guild: discord.Guild) -> None:
    _cache[guild.id] = {
        "timestamp": time.time(),
        "emojis": list(guild.emojis),
        "stickers": list(guild.stickers),
    }


def _get_cached(guild: discord.Guild) -> dict[str, object]:
    entry = _cache.get(guild.id)
    if not entry or time.time() - float(entry.get("timestamp", 0)) > CACHE_TTL_SECONDS:
        _refresh_cache(guild)
        entry = _cache[guild.id]
    return entry


def get_emojis(guild: discord.Guild) -> list[discord.Emoji]:
    entry = _get_cached(guild)
    return list(entry.get("emojis") or [])


def get_stickers(guild: discord.Guild) -> list[discord.StickerItem]:
    entry = _get_cached(guild)
    return list(entry.get("stickers") or [])


def pick_emoji(guild: discord.Guild, query: Optional[str] = None) -> Optional[discord.Emoji]:
    emojis = get_emojis(guild)
    if not emojis:
        return None
    if query:
        query_lower = query.lower()
        filtered = [e for e in emojis if query_lower in (e.name or "").lower()]
        if filtered:
            emojis = filtered
    return random.choice(emojis) if emojis else None


def pick_sticker(guild: discord.Guild, query: Optional[str] = None) -> Optional[discord.StickerItem]:
    stickers = get_stickers(guild)
    if not stickers:
        return None
    if query:
        query_lower = query.lower()
        filtered = [s for s in stickers if query_lower in (s.name or "").lower()]
        if filtered:
            stickers = filtered
    return random.choice(stickers) if stickers else None
