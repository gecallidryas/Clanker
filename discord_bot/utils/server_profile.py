from __future__ import annotations

from pathlib import Path
from typing import Optional

import discord

from utils.db_handler import DATA_DIR

MAX_BANNER_BYTES = 500 * 1024
BANNER_DIR = DATA_DIR / "banners"

MODE_BANNER_FILES = {
    "mode_default": BANNER_DIR / "mode_default.webp",
    "mode_femboy": BANNER_DIR / "mode_femboy.webp",
    "mode_tsundere": BANNER_DIR / "mode_tsundere.webp",
    "mode_oneesan": BANNER_DIR / "mode_oneesan.webp",
}


def _ensure_banner_dir() -> None:
    BANNER_DIR.mkdir(parents=True, exist_ok=True)


def _load_banner_bytes(path: Path) -> Optional[bytes]:
    if not path.exists():
        return None
    data = path.read_bytes()
    if len(data) > MAX_BANNER_BYTES:
        return None
    return data


def _get_bot_member(bot: discord.Client, guild_id: int) -> Optional[discord.Member]:
    guild = bot.get_guild(guild_id)
    if not guild:
        return None
    return guild.me or guild.get_member(bot.user.id if bot.user else 0)


async def set_member_profile(
    bot: discord.Client,
    guild_id: int,
    *,
    banner_bytes: Optional[bytes] = None,
    bio: Optional[str] = None,
) -> tuple[bool, str]:
    """Update the bot's per-guild profile (banner/bio)."""
    member = _get_bot_member(bot, guild_id)
    if not member:
        return False, "member"
    try:
        await member.edit(banner=banner_bytes, bio=bio)
    except TypeError:
        return False, "unsupported"
    except discord.Forbidden:
        return False, "forbidden"
    except discord.HTTPException:
        return False, "http"
    return True, "ok"


async def set_member_nickname(
    bot: discord.Client,
    guild_id: int,
    nickname: Optional[str],
) -> tuple[bool, str]:
    """Update the bot's per-guild nickname."""
    member = _get_bot_member(bot, guild_id)
    if not member:
        return False, "member"
    try:
        await member.edit(nick=nickname)
    except discord.Forbidden:
        return False, "forbidden"
    except discord.HTTPException:
        return False, "http"
    return True, "ok"


async def set_mode_profile(
    bot: discord.Client,
    guild_id: int,
    mode: str,
    *,
    bio: Optional[str],
    banner_file: Optional[str] = None,
) -> tuple[bool, str]:
    _ensure_banner_dir()
    if banner_file:
        banner_path = BANNER_DIR / banner_file
    else:
        banner_path = MODE_BANNER_FILES.get(mode)
    if not banner_path:
        return False, "missing"
    banner_bytes = _load_banner_bytes(banner_path)
    if not banner_bytes:
        return False, "missing"
    return await set_member_profile(bot, guild_id, banner_bytes=banner_bytes, bio=bio)


async def set_custom_profile(
    bot: discord.Client,
    guild_id: int,
    *,
    banner_bytes: Optional[bytes],
    bio: Optional[str],
) -> tuple[bool, str]:
    if banner_bytes and len(banner_bytes) > MAX_BANNER_BYTES:
        return False, "size"
    return await set_member_profile(bot, guild_id, banner_bytes=banner_bytes, bio=bio)
