from __future__ import annotations

import re
from typing import Iterable, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

FEMMY_EMOJI_PREFIX = "femmy"
YUMI_EMOJI_PREFIX = "yumi"


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
