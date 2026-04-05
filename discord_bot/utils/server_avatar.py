from __future__ import annotations

import inspect
from pathlib import Path
from typing import Optional

import discord

from utils.db_handler import (
    DATA_DIR,
    get_guild_avatar_path,
    set_guild_avatar_path,
    can_update_guild_avatar,
    record_guild_avatar_update,
)
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_AVATAR_BYTES = 500 * 1024
AVATAR_DIR = DATA_DIR / "avatars"
CUSTOM_DIR = AVATAR_DIR / "custom"

MODE_AVATAR_FILES = {
    "mode_femboy": AVATAR_DIR / "mode_femboy.webp",
    "mode_tsundere": AVATAR_DIR / "mode_tsundere.webp",
    "mode_oneesan": AVATAR_DIR / "mode_oneesan.webp",
}

EVIL_MODE_AVATAR_FILES = {
    "mode_femboy": AVATAR_DIR / "mode_femboy_evil.webp",
    "mode_tsundere": AVATAR_DIR / "mode_tsundere_evil.webp",
    "mode_oneesan": AVATAR_DIR / "mode_oneesan_evil.webp",
}


def _ensure_avatar_dirs() -> None:
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)


def get_custom_avatar_file(guild_id: int) -> Path:
    _ensure_avatar_dirs()
    return CUSTOM_DIR / f"guild_{guild_id}.webp"


def _load_avatar_bytes(path: Path) -> Optional[bytes]:
    if not path.exists():
        return None
    data = path.read_bytes()
    if len(data) > MAX_AVATAR_BYTES:
        return None
    return data


def _get_client_user(bot: discord.Client) -> Optional[discord.ClientUser]:
    return getattr(bot, "user", None)


def _get_bot_member(bot: discord.Client, guild_id: int) -> Optional[discord.Member]:
    guild = bot.get_guild(guild_id)
    if not guild:
        return None
    return guild.me or guild.get_member(bot.user.id if bot.user else 0)


def _member_edit_supports(member: discord.Member, *fields: str) -> bool:
    try:
        parameters = inspect.signature(member.edit).parameters
    except (TypeError, ValueError):
        return False
    return all(field in parameters for field in fields)


async def set_server_avatar(
    bot: discord.Client,
    guild_id: int,
    avatar_bytes: bytes,
) -> tuple[bool, str]:
    """Update the bot avatar, preferring the per-guild member profile on supported versions."""
    if not avatar_bytes:
        return False, "missing"
    if len(avatar_bytes) > MAX_AVATAR_BYTES:
        return False, "size"

    allowed, reason = await can_update_guild_avatar(guild_id)
    if not allowed:
        return False, reason

    guild = bot.get_guild(guild_id)
    if not guild:
        return False, "guild"

    member = _get_bot_member(bot, guild_id)
    if not member:
        return False, "member"

    try:
        if _member_edit_supports(member, "avatar"):
            await member.edit(avatar=avatar_bytes)
        else:
            user = _get_client_user(bot)
            if not user:
                return False, "user"
            await user.edit(avatar=avatar_bytes)
    except TypeError:
        return False, "unsupported"
    except discord.Forbidden:
        return False, "forbidden"
    except discord.HTTPException:
        return False, "http"

    await record_guild_avatar_update(guild_id)
    return True, "ok"


async def clear_server_avatar(
    bot: discord.Client,
    guild_id: int,
) -> tuple[bool, str]:
    """Clear the bot avatar, preferring the per-guild member profile on supported versions."""
    allowed, reason = await can_update_guild_avatar(guild_id)
    if not allowed:
        return False, reason

    guild = bot.get_guild(guild_id)
    if not guild:
        return False, "guild"

    member = _get_bot_member(bot, guild_id)
    if not member:
        return False, "member"

    try:
        if _member_edit_supports(member, "avatar"):
            await member.edit(avatar=None)
        else:
            user = _get_client_user(bot)
            if not user:
                return False, "user"
            await user.edit(avatar=None)
    except TypeError:
        return False, "unsupported"
    except discord.Forbidden:
        return False, "forbidden"
    except discord.HTTPException:
        return False, "http"

    await record_guild_avatar_update(guild_id)
    return True, "ok"


async def set_mode_avatar(
    bot: discord.Client,
    guild_id: int,
    mode: str,
    evil_mode: bool = False,
    force: bool = False,
) -> tuple[bool, str]:
    _ensure_avatar_dirs()
    if mode == "mode_default":
        return await clear_server_avatar(bot, guild_id)
    custom_path = await get_guild_avatar_path(guild_id)
    if custom_path:
        custom_file = Path(custom_path)
        if custom_file.exists():
            if not force:
                return False, "custom"
        else:
            await set_guild_avatar_path(guild_id, None)

    avatar_path = MODE_AVATAR_FILES.get(mode)
    if evil_mode:
        evil_path = EVIL_MODE_AVATAR_FILES.get(mode)
        if evil_path:
            avatar_path = evil_path
    if not avatar_path:
        return False, "missing"

    avatar_bytes = _load_avatar_bytes(avatar_path)
    if not avatar_bytes:
        return False, "missing"

    return await set_server_avatar(bot, guild_id, avatar_bytes)


async def set_custom_avatar(
    bot: discord.Client,
    guild_id: int,
    avatar_bytes: bytes,
) -> tuple[bool, str]:
    if not avatar_bytes:
        return False, "missing"
    if len(avatar_bytes) > MAX_AVATAR_BYTES:
        return False, "size"

    _ensure_avatar_dirs()
    custom_path = get_custom_avatar_file(guild_id)
    try:
        custom_path.write_bytes(avatar_bytes)
    except OSError as exc:
        logger.warning("Failed to write custom avatar for %s: %s", guild_id, exc)
        return False, "write"

    success, reason = await set_server_avatar(bot, guild_id, avatar_bytes)
    if not success:
        try:
            custom_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, reason

    await set_guild_avatar_path(guild_id, str(custom_path))
    return True, "ok"
