from __future__ import annotations

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
    "mode_default": AVATAR_DIR / "mode_default.png",
    "mode_femboy": AVATAR_DIR / "mode_femboy.png",
    "mode_tsundere": AVATAR_DIR / "mode_tsundere.png",
    "mode_oneesan": AVATAR_DIR / "mode_oneesan.png",
}

EVIL_MODE_AVATAR_FILES = {
    "mode_femboy": AVATAR_DIR / "mode_femboy_evil.png",
    "mode_tsundere": AVATAR_DIR / "mode_tsundere_evil.png",
    "mode_oneesan": AVATAR_DIR / "mode_oneesan_evil.png",
}


def _ensure_avatar_dirs() -> None:
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)


def get_custom_avatar_file(guild_id: int) -> Path:
    _ensure_avatar_dirs()
    return CUSTOM_DIR / f"guild_{guild_id}.png"


def _load_avatar_bytes(path: Path) -> Optional[bytes]:
    if not path.exists():
        return None
    data = path.read_bytes()
    if len(data) > MAX_AVATAR_BYTES:
        return None
    return data


async def set_server_avatar(
    bot: discord.Client,
    guild_id: int,
    avatar_bytes: bytes,
) -> tuple[bool, str]:
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

    member = guild.me or guild.get_member(bot.user.id if bot.user else 0)
    if not member:
        return False, "member"

    try:
        await member.edit(avatar=avatar_bytes)
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
    custom_path = await get_guild_avatar_path(guild_id)
    if custom_path:
        custom_file = Path(custom_path)
        if custom_file.exists():
            if not force:
                return False, "custom"
        else:
            await set_guild_avatar_path(guild_id, None)

    avatar_path = MODE_AVATAR_FILES.get(mode, MODE_AVATAR_FILES.get("mode_default"))
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
