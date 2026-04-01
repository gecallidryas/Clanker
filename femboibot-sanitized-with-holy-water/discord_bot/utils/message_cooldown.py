from __future__ import annotations

from datetime import datetime
from typing import Mapping, MutableMapping, Optional

import discord

COOLDOWN_OFF = "off"
COOLDOWN_PER_USER = "per_user"
COOLDOWN_PER_CHANNEL = "per_channel"
COOLDOWN_SERVER_WIDE = "server_wide"
COOLDOWN_STRICT_SERVER_WIDE = "strict_server_wide"

VALID_COOLDOWN_TYPES = {
    COOLDOWN_OFF,
    COOLDOWN_PER_USER,
    COOLDOWN_PER_CHANNEL,
    COOLDOWN_SERVER_WIDE,
    COOLDOWN_STRICT_SERVER_WIDE,
}

# Key format used inside runtime cooldown map.
# ("user", user_id), ("channel", channel_id), ("server", guild_id)
CooldownKey = tuple[str, int]


def normalize_cooldown_type(raw: object) -> str:
    value = str(raw or "").strip().lower()
    legacy_map = {
        "0": COOLDOWN_OFF,
        "1": COOLDOWN_PER_USER,
        "2": COOLDOWN_PER_CHANNEL,
        "3": COOLDOWN_SERVER_WIDE,
        "4": COOLDOWN_STRICT_SERVER_WIDE,
    }
    if value in legacy_map:
        return legacy_map[value]
    if value in VALID_COOLDOWN_TYPES:
        return value
    return COOLDOWN_PER_USER


def is_exempt_from_cooldown(
    member: Optional[discord.Member],
    cooldown_type: str,
) -> bool:
    normalized = normalize_cooldown_type(cooldown_type)
    if normalized in {COOLDOWN_OFF, COOLDOWN_STRICT_SERVER_WIDE}:
        return False
    return bool(member and member.guild_permissions.manage_guild)


def build_cooldown_key(
    *,
    cooldown_type: str,
    guild_id: int,
    channel_id: int,
    user_id: int,
) -> CooldownKey | None:
    normalized = normalize_cooldown_type(cooldown_type)
    if normalized == COOLDOWN_OFF:
        return None
    if normalized == COOLDOWN_PER_CHANNEL:
        return ("channel", int(channel_id))
    if normalized in {COOLDOWN_SERVER_WIDE, COOLDOWN_STRICT_SERVER_WIDE}:
        return ("server", int(guild_id))
    return ("user", int(user_id))


def check_reply_cooldown(
    cooldowns: Mapping[CooldownKey, datetime],
    *,
    cooldown_type: str,
    cooldown_seconds: int,
    guild_id: int,
    channel_id: int,
    user_id: int,
    member: Optional[discord.Member] = None,
    now: Optional[datetime] = None,
) -> tuple[bool, int]:
    if cooldown_seconds <= 0:
        return False, 0
    normalized = normalize_cooldown_type(cooldown_type)
    if normalized == COOLDOWN_OFF:
        return False, 0
    if is_exempt_from_cooldown(member, normalized):
        return False, 0
    key = build_cooldown_key(
        cooldown_type=normalized,
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
    )
    if key is None:
        return False, 0
    last_reply = cooldowns.get(key)
    if not last_reply:
        return False, 0
    now_dt = now or datetime.now()
    elapsed = (now_dt - last_reply).total_seconds()
    if elapsed < cooldown_seconds:
        return True, max(0, int(cooldown_seconds - elapsed))
    return False, 0


def set_reply_cooldown(
    cooldowns: MutableMapping[CooldownKey, datetime],
    *,
    cooldown_type: str,
    guild_id: int,
    channel_id: int,
    user_id: int,
    now: Optional[datetime] = None,
) -> CooldownKey | None:
    key = build_cooldown_key(
        cooldown_type=cooldown_type,
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
    )
    if key is None:
        return None
    cooldowns[key] = now or datetime.now()
    return key


def clear_channel_scoped_reply_cooldowns(
    cooldowns: MutableMapping[CooldownKey, datetime],
    channel_id: int,
) -> None:
    # Remove new-style per-channel keys.
    to_delete = [key for key in cooldowns.keys() if key[0] == "channel" and key[1] == channel_id]
    for key in to_delete:
        cooldowns.pop(key, None)

