from __future__ import annotations

from datetime import timedelta
import json
import re
from typing import Any, Dict, List, Optional

import discord

from utils.db_handler import (
    add_guild_config_audit,
    add_automod_rule,
    add_staff_role,
    add_starboard_ignored_channel,
    get_starboard_settings,
    get_staff_roles,
    get_welcome_config,
    remove_automod_rule,
    remove_staff_role,
    remove_starboard_ignored_channel,
    set_autorole_enabled,
    set_autorole_id,
    set_dm_welcome_message,
    set_dm_welcome_enabled,
    set_mod_log_channel_id,
    set_server_mode,
    set_spam_config,
    set_starboard_enabled,
    set_url_safety_config,
    set_welcome_enabled,
    set_welcome_channel_id,
    set_welcome_message_template,
    upsert_starboard_settings,
)

ADMIN_ACTIONS = {
    "STARBOARD_SETUP": "execute_starboard_setup",
    "STARBOARD_TOGGLE": "intent:starboard.toggle",
    "STARBOARD_IGNORE": "intent:starboard.ignore_channel",
    "STARBOARD_UNIGNORE": "intent:starboard.unignore_channel",
    "WELCOME_SETUP": "execute_welcome_setup",
    "WELCOME_TOGGLE": "intent:welcome.toggle",
    "WELCOME_DM_CONFIG": "intent:welcome.dm.configure",
    "WELCOME_DM_TOGGLE": "intent:welcome.dm.toggle",
    "AUTOMOD_ADD": "execute_automod_add",
    "AUTOMOD_REMOVE": "execute_automod_remove",
    "SPAM_CONFIG": "intent:automod.spam.configure",
    "URL_SAFETY_CONFIG": "intent:url_safety.configure",
    "AUTOROLE_SET": "intent:autorole.set",
    "AUTOROLE_CLEAR": "intent:autorole.clear",
    "STAFF_ADD": "intent:staff.add",
    "STAFF_REMOVE": "intent:staff.remove",
    "STAFF_CLEAR": "intent:staff.clear",
    "CONFIG_MODE": "execute_config_mode",
    "CONFIG_LOG": "execute_config_log",
    "CONFIG_LOG_CLEAR": "intent:modlog.clear",
}

CUSTOM_EMOJI_RE = re.compile(r"<a?:\w+:(\d+)>")


async def get_admin_permission_level(executor: discord.Member | None) -> int:
    if not executor or not getattr(executor, "guild", None):
        return 0

    guild = executor.guild
    if getattr(guild, "owner_id", None) == getattr(executor, "id", None):
        return 2

    permissions = getattr(executor, "guild_permissions", None)
    if permissions and (
        bool(getattr(permissions, "administrator", False))
        or bool(getattr(permissions, "manage_guild", False))
    ):
        return 2

    roles = getattr(executor, "roles", None) or []
    role_ids = {int(getattr(role, "id", 0)) for role in roles if getattr(role, "id", None) is not None}
    if not role_ids:
        return 0

    level = 0
    for role_id, permission_level in await get_staff_roles(int(guild.id)):
        if int(role_id) in role_ids:
            level = max(level, int(permission_level))
    return level


def required_admin_intent_permission_level(intent: str) -> int:
    normalized = str(intent or "").strip().lower()
    if normalized in {"moderation.timeout", "moderation.kick"}:
        return 1
    return 2


def required_admin_action_permission_level(action: str) -> int:
    return required_admin_intent_permission_level(str(action or "").strip().lower())


def _normalize_lookup_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.lstrip("#@&")
    return re.sub(r"\s+", " ", text)


def _iter_guild_channels(guild: discord.Guild) -> list[Any]:
    channels = []
    for attr in ("channels", "text_channels", "voice_channels", "categories"):
        value = getattr(guild, attr, None) or []
        for channel in value:
            if channel not in channels:
                channels.append(channel)
    return channels


def _resolve_guild_channel(
    guild: discord.Guild,
    *,
    channel_id: Any = None,
    channel_name: Any = None,
    channel_kind: Any = None,
) -> Any:
    try:
        resolved_id = int(channel_id) if channel_id is not None else None
    except (TypeError, ValueError):
        resolved_id = None
    if resolved_id is not None and hasattr(guild, "get_channel"):
        channel = guild.get_channel(resolved_id)
        if channel is not None:
            return channel

    normalized_name = _normalize_lookup_name(channel_name)
    if not normalized_name:
        return None

    normalized_kind = str(channel_kind or "").strip().lower()
    for channel in _iter_guild_channels(guild):
        if normalized_kind == "category" and channel not in getattr(guild, "categories", []):
            continue
        if normalized_kind == "voice" and channel in getattr(guild, "categories", []):
            continue
        if normalized_kind == "text" and channel in getattr(guild, "categories", []):
            continue
        if _normalize_lookup_name(getattr(channel, "name", "")) == normalized_name:
            return channel
    return None


def _resolve_guild_role(
    guild: discord.Guild,
    *,
    role_id: Any = None,
    role_name: Any = None,
) -> Any:
    try:
        resolved_id = int(role_id) if role_id is not None else None
    except (TypeError, ValueError):
        resolved_id = None
    if resolved_id is not None and hasattr(guild, "get_role"):
        role = guild.get_role(resolved_id)
        if role is not None:
            return role

    normalized_name = _normalize_lookup_name(role_name)
    if not normalized_name:
        return None
    for role in getattr(guild, "roles", []) or []:
        if _normalize_lookup_name(getattr(role, "name", "")) == normalized_name:
            return role
    return None


def _resolve_guild_member(
    guild: discord.Guild,
    *,
    member_id: Any,
) -> Any:
    try:
        resolved_id = int(member_id)
    except (TypeError, ValueError):
        return None
    if hasattr(guild, "get_member"):
        member = guild.get_member(resolved_id)
        if member is not None:
            return member
    return None


def _normalize_emoji_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    items = parsed
                else:
                    items = [text]
            except json.JSONDecodeError:
                items = re.split(r"[\s,]+", text)
        else:
            items = re.split(r"[\s,]+", text)
    else:
        return []

    cleaned = []
    for item in items:
        if item is None:
            continue
        token = str(item).strip()
        if token:
            cleaned.append(token)
    return cleaned


def _parse_optional_bool(raw: Any) -> Optional[bool]:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw).strip().lower()
    if not text:
        return None
    if text in {"true", "yes", "on", "1", "enable", "enabled"}:
        return True
    if text in {"false", "no", "off", "0", "disable", "disabled"}:
        return False
    return None


def _resolve_emoji_token(guild: discord.Guild, token: str) -> Optional[str]:
    token = token.strip()
    if not token:
        return None

    match = CUSTOM_EMOJI_RE.match(token)
    if match:
        emoji_id = int(match.group(1))
        emoji_obj = discord.utils.get(guild.emojis, id=emoji_id)
        return str(emoji_obj) if emoji_obj else None

    if token.startswith(":") and token.endswith(":") and len(token) > 2:
        name = token.strip(":")
        emoji_obj = discord.utils.get(guild.emojis, name=name)
        return str(emoji_obj) if emoji_obj else None

    # Assume unicode emoji for anything else.
    return token


def _summarize_starboard_params(
    channel_id: Optional[int],
    emoji_mode: str,
    emoji_triggers: List[str],
    threshold: Optional[int],
) -> str:
    parts = []
    if channel_id:
        parts.append(f"channel <#{channel_id}>")
    if emoji_mode == "any":
        parts.append("triggers: any emoji")
    elif emoji_triggers:
        parts.append("triggers: " + " ".join(emoji_triggers))
    if threshold is not None:
        parts.append(f"threshold: {threshold}")
    return ", ".join(parts) if parts else "no details parsed"


def _summarize_welcome_params(
    channel_id: Optional[int],
    message: Optional[str],
    dm_message: Optional[str],
    dm_enabled: Optional[bool],
) -> str:
    parts = []
    if channel_id:
        parts.append(f"channel <#{channel_id}>")
    if message:
        parts.append("message set")
    if dm_message:
        parts.append("dm message set")
    if dm_enabled is not None:
        parts.append(f"dm enabled: {dm_enabled}")
    return ", ".join(parts) if parts else "no details parsed"


def _summarize_automod_params(
    keyword: Optional[str],
    action: Optional[str],
    duration: Optional[int],
) -> str:
    parts = []
    if keyword:
        parts.append(f"keyword '{keyword}'")
    if action:
        parts.append(f"action {action}")
    if duration is not None:
        parts.append(f"duration {duration}m")
    return ", ".join(parts) if parts else "no details parsed"


def _summarize_config_mode(mode: Optional[str]) -> str:
    return f"mode {mode}" if mode else "no mode parsed"


def _summarize_config_log(channel_id: Optional[int]) -> str:
    return f"mod log <#{channel_id}>" if channel_id else "no channel parsed"


async def execute_admin_action(
    action: str,
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
    bot: Optional[discord.Client] = None,
    current_channel_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not action:
        return {"success": False, "error": "Missing action."}

    action = action.upper().strip()
    if action not in ADMIN_ACTIONS:
        return {"success": False, "error": "Unknown action."}

    if await get_admin_permission_level(executor) < required_admin_action_permission_level(action):
        return {"success": False, "error": "Insufficient permissions."}

    handler_name = ADMIN_ACTIONS[action]
    if handler_name.startswith("intent:"):
        return await execute_admin_intent(
            handler_name.split(":", 1)[1],
            params or {},
            guild,
            executor,
            bot=bot,
            current_channel_id=current_channel_id,
        )
    handler = globals().get(handler_name)
    if not handler:
        return {"success": False, "error": "Action handler missing."}

    if handler_name == "execute_config_mode":
        return await handler(params or {}, guild, executor, bot=bot)
    if handler_name in {"execute_starboard_setup", "execute_config_log"}:
        return await handler(params or {}, guild, executor, current_channel_id=current_channel_id)
    return await handler(params or {}, guild, executor)


async def execute_admin_intent(
    intent: str,
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
    bot: Optional[discord.Client] = None,
    current_channel_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not intent:
        return {"success": False, "error": "Missing intent."}
    if await get_admin_permission_level(executor) < required_admin_intent_permission_level(intent):
        return {"success": False, "error": "Insufficient permissions."}

    params = params or {}
    normalized_intent = intent.strip().lower()

    if normalized_intent == "moderation.ban":
        target_id = params.get("target_id")
        try:
            target_id = int(target_id) if target_id is not None else None
        except (TypeError, ValueError):
            target_id = None
        if not target_id:
            return {"success": False, "error": "Missing target_id."}
        reason = str(params.get("reason") or "Natural-language moderation command")
        await guild.ban(discord.Object(id=target_id), reason=reason)
        return {"success": True, "message": f"Banned user `{target_id}`."}

    if normalized_intent == "moderation.unban":
        target_id = params.get("target_id")
        try:
            target_id = int(target_id) if target_id is not None else None
        except (TypeError, ValueError):
            target_id = None
        if not target_id:
            return {"success": False, "error": "Missing target_id."}
        reason = str(params.get("reason") or "Natural-language moderation command")
        await guild.unban(discord.Object(id=target_id), reason=reason)
        return {"success": True, "message": f"Unbanned user `{target_id}`."}

    if normalized_intent == "moderation.kick":
        member = _resolve_guild_member(guild, member_id=params.get("target_id"))
        if member is None:
            return {"success": False, "error": "Missing or unknown target_id."}
        reason = str(params.get("reason") or "Natural-language moderation command")
        await member.kick(reason=reason)
        return {"success": True, "message": f"Kicked {getattr(member, 'mention', getattr(member, 'id', 'that member'))}."}

    if normalized_intent == "moderation.timeout":
        member = _resolve_guild_member(guild, member_id=params.get("target_id"))
        if member is None:
            return {"success": False, "error": "Missing or unknown target_id."}
        duration_raw = params.get("duration")
        try:
            duration_minutes = int(str(duration_raw).strip()) if duration_raw is not None else 10
        except (TypeError, ValueError):
            duration_minutes = 10
        duration_minutes = max(1, min(duration_minutes, 40320))
        reason = str(params.get("reason") or "Natural-language moderation command")
        await member.timeout(
            discord.utils.utcnow() + timedelta(minutes=duration_minutes),
            reason=reason,
        )
        return {
            "success": True,
            "message": f"Timed out {getattr(member, 'mention', getattr(member, 'id', 'that member'))} for {duration_minutes} minute(s).",
        }

    if normalized_intent == "channel.create_text":
        channel_name = str(params.get("channel_name") or "").strip()
        if not channel_name:
            return {"success": False, "error": "Missing channel_name."}
        await guild.create_text_channel(channel_name)
        return {"success": True, "message": f"Created text channel '{channel_name}'."}

    if normalized_intent == "channel.create_voice":
        channel_name = str(params.get("channel_name") or "").strip()
        if not channel_name:
            return {"success": False, "error": "Missing channel_name."}
        await guild.create_voice_channel(channel_name)
        return {"success": True, "message": f"Created voice channel '{channel_name}'."}

    if normalized_intent == "channel.create_category":
        channel_name = str(params.get("channel_name") or "").strip()
        if not channel_name:
            return {"success": False, "error": "Missing channel_name."}
        await guild.create_category(channel_name)
        return {"success": True, "message": f"Created category '{channel_name}'."}

    if normalized_intent == "channel.delete":
        channel = _resolve_guild_channel(
            guild,
            channel_id=params.get("channel_id"),
            channel_name=params.get("channel_name"),
            channel_kind=params.get("channel_kind"),
        )
        if not params.get("channel_id") and not params.get("channel_name"):
            return {"success": False, "error": "Missing channel target."}
        if channel is None:
            return {"success": False, "error": "I couldn't find that channel."}
        await channel.delete()
        return {
            "success": True,
            "message": f"Deleted channel '{getattr(channel, 'name', 'unknown')}'.",
        }

    if normalized_intent == "role.create":
        role_name = str(params.get("role_name") or "").strip()
        if not role_name:
            return {"success": False, "error": "Missing role_name."}
        await guild.create_role(name=role_name)
        return {"success": True, "message": f"Created role '{role_name}'."}

    if normalized_intent == "role.delete":
        if not params.get("role_id") and not params.get("role_name"):
            return {"success": False, "error": "Missing role target."}
        role = _resolve_guild_role(
            guild,
            role_id=params.get("role_id"),
            role_name=params.get("role_name"),
        )
        if role is None:
            return {"success": False, "error": "I couldn't find that role."}
        await role.delete()
        return {"success": True, "message": f"Deleted role '{getattr(role, 'name', 'unknown')}'."}

    if normalized_intent == "role.assign":
        if not params.get("target_id"):
            return {"success": False, "error": "Missing target_id."}
        if not params.get("role_id") and not params.get("role_name"):
            return {"success": False, "error": "Missing role target."}
        role = _resolve_guild_role(
            guild,
            role_id=params.get("role_id"),
            role_name=params.get("role_name"),
        )
        if role is None:
            return {"success": False, "error": "I couldn't find that role."}
        member = _resolve_guild_member(guild, member_id=params.get("target_id"))
        if member is None:
            return {"success": False, "error": "I couldn't find that member."}
        await member.add_roles(role)
        return {
            "success": True,
            "message": f"Gave '{getattr(role, 'name', 'unknown')}' to <@{int(params['target_id'])}>.",
        }

    if normalized_intent == "role.remove":
        if not params.get("target_id"):
            return {"success": False, "error": "Missing target_id."}
        if not params.get("role_id") and not params.get("role_name"):
            return {"success": False, "error": "Missing role target."}
        role = _resolve_guild_role(
            guild,
            role_id=params.get("role_id"),
            role_name=params.get("role_name"),
        )
        if role is None:
            return {"success": False, "error": "I couldn't find that role."}
        member = _resolve_guild_member(guild, member_id=params.get("target_id"))
        if member is None:
            return {"success": False, "error": "I couldn't find that member."}
        await member.remove_roles(role)
        return {
            "success": True,
            "message": f"Removed '{getattr(role, 'name', 'unknown')}' from <@{int(params['target_id'])}>.",
        }

    if normalized_intent == "starboard.configure":
        return await execute_starboard_setup(
            params,
            guild,
            executor,
            current_channel_id=current_channel_id,
        )

    if normalized_intent == "starboard.toggle":
        enabled = bool(params.get("enabled"))
        await set_starboard_enabled(guild.id, enabled)
        return {
            "success": True,
            "message": f"Starboard {'enabled' if enabled else 'disabled'}.",
        }

    if normalized_intent == "starboard.ignore_channel":
        channel_id = params.get("channel_id")
        if not channel_id:
            return {"success": False, "error": "Missing channel_id."}
        await add_starboard_ignored_channel(guild.id, int(channel_id))
        return {"success": True, "message": f"Starboard will ignore <#{int(channel_id)}>."}

    if normalized_intent == "starboard.unignore_channel":
        channel_id = params.get("channel_id")
        if not channel_id:
            return {"success": False, "error": "Missing channel_id."}
        removed = await remove_starboard_ignored_channel(guild.id, int(channel_id))
        if removed:
            return {"success": True, "message": f"Starboard will watch <#{int(channel_id)}> again."}
        return {"success": False, "error": "That channel was not ignored."}

    if normalized_intent == "welcome.configure":
        return await execute_welcome_setup(params, guild, executor)

    if normalized_intent == "welcome.toggle":
        enabled = bool(params.get("welcome_enabled"))
        await set_welcome_enabled(guild.id, enabled)
        return {
            "success": True,
            "message": f"Welcome messages {'enabled' if enabled else 'disabled'}.",
        }

    if normalized_intent == "welcome.dm.toggle":
        enabled = bool(params.get("dm_enabled"))
        await set_dm_welcome_enabled(guild.id, enabled)
        return {
            "success": True,
            "message": f"DM welcomes {'enabled' if enabled else 'disabled'}.",
        }

    if normalized_intent == "welcome.dm.configure":
        dm_message = (params.get("dm_message") or "").strip()
        if not dm_message:
            return {"success": False, "error": "Missing dm_message."}
        await set_dm_welcome_message(guild.id, dm_message)
        return {"success": True, "message": "DM welcome message updated."}

    if normalized_intent == "welcome.message.clear":
        await set_welcome_message_template(guild.id, None)
        return {"success": True, "message": "Welcome message template cleared."}

    if normalized_intent == "welcome.dm.message.clear":
        await set_dm_welcome_message(guild.id, None)
        return {"success": True, "message": "DM welcome message cleared."}

    if normalized_intent == "automod.keyword.add":
        return await execute_automod_add(params, guild, executor)

    if normalized_intent == "automod.keyword.remove":
        return await execute_automod_remove(params, guild, executor)

    if normalized_intent == "automod.spam.configure":
        updates = {}
        for key in ("spam_max_messages", "spam_window_seconds", "spam_timeout_minutes"):
            if params.get(key) is not None:
                updates[key] = int(params[key])
        if params.get("spam_timeout_enabled") is not None:
            updates["spam_timeout_enabled"] = int(bool(params["spam_timeout_enabled"]))
        await set_spam_config(guild.id, updates)
        return {"success": True, "message": "Spam automod updated."}

    if normalized_intent == "url_safety.configure":
        updates = {}
        for key in ("url_allowlist", "url_blocklist", "url_safety_action"):
            if params.get(key) is not None:
                updates[key] = params[key]
        if params.get("url_safety_enabled") is not None:
            updates["url_safety_enabled"] = int(bool(params["url_safety_enabled"]))
        await set_url_safety_config(guild.id, updates)
        return {"success": True, "message": "URL safety updated."}

    if normalized_intent == "modlog.set":
        return await execute_config_log(
            params,
            guild,
            executor,
            current_channel_id=current_channel_id,
        )

    if normalized_intent == "modlog.clear":
        await set_mod_log_channel_id(guild.id, None)
        return {"success": True, "message": "Mod log disabled."}

    if normalized_intent == "autorole.set":
        role_id = params.get("role_id")
        if not role_id:
            return {"success": False, "error": "Missing role_id."}
        await set_autorole_id(guild.id, int(role_id))
        await set_autorole_enabled(guild.id, True)
        return {"success": True, "message": f"Autorole set to <@&{int(role_id)}>."}

    if normalized_intent == "autorole.clear":
        await set_autorole_id(guild.id, None)
        await set_autorole_enabled(guild.id, False)
        return {"success": True, "message": "Autorole disabled."}

    if normalized_intent == "staff.add":
        role_id = params.get("role_id")
        permission_level = params.get("permission_level")
        if not role_id or permission_level is None:
            return {"success": False, "error": "Missing role_id or permission_level."}
        await add_staff_role(guild.id, int(role_id), int(permission_level))
        return {
            "success": True,
            "message": f"Added <@&{int(role_id)}> as bot staff level {int(permission_level)}.",
        }

    if normalized_intent == "staff.remove":
        role_id = params.get("role_id")
        if not role_id:
            return {"success": False, "error": "Missing role_id."}
        removed = await remove_staff_role(guild.id, int(role_id))
        if removed:
            return {"success": True, "message": f"Removed <@&{int(role_id)}> from bot staff."}
        return {"success": False, "error": "That role was not configured as bot staff."}

    if normalized_intent == "staff.clear":
        entries = await get_staff_roles(guild.id)
        for role_id, _level in entries:
            await remove_staff_role(guild.id, int(role_id))
        return {"success": True, "message": "Cleared all configured staff roles."}

    if normalized_intent == "config.mode":
        return await execute_config_mode(params, guild, executor, bot=bot)

    return {"success": False, "error": f"Unknown admin intent '{intent}'."}


async def execute_starboard_setup(
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
    current_channel_id: Optional[int] = None,
) -> Dict[str, Any]:
    channel_id = params.get("channel_id")
    try:
        channel_id = int(channel_id) if channel_id is not None else None
    except (TypeError, ValueError):
        channel_id = None

    if channel_id is None:
        channel_hint = str(params.get("channel") or params.get("destination") or "").strip().lower()
        if channel_hint in {"this channel", "current channel", "here"}:
            channel_id = current_channel_id
    if channel_id is None and current_channel_id and params.get("use_current_channel"):
        channel_id = current_channel_id
    allow_self_star_override = _parse_optional_bool(params.get("allow_self_star"))

    emoji_mode = (params.get("emoji_mode") or "list").strip().lower()
    emoji_triggers = _normalize_emoji_list(params.get("emoji_triggers"))

    if not emoji_triggers:
        fallback = params.get("emoji") or params.get("emoji_trigger")
        if fallback:
            emoji_triggers = _normalize_emoji_list(fallback)

    if emoji_mode in {"any", "all"}:
        emoji_mode = "any"
        emoji_triggers = []
    else:
        emoji_mode = "list"

    threshold_raw = params.get("threshold")
    try:
        threshold = int(threshold_raw) if threshold_raw is not None else None
    except (TypeError, ValueError):
        threshold = None

    threshold = max(1, threshold) if threshold is not None else 3

    if not channel_id:
        return {
            "success": False,
            "needs_confirmation": True,
            "missing": ["channel"],
            "summary": _summarize_starboard_params(channel_id, emoji_mode, emoji_triggers, threshold),
            "defaults": {
                "emoji_mode": "list" if emoji_mode != "any" else "any",
                "emoji_triggers": emoji_triggers if emoji_triggers else ["⭐"],
                "threshold": threshold,
            },
        }

    target_channel = guild.get_channel(channel_id)
    if target_channel is None:
        try:
            target_channel = await guild.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            target_channel = None
    if not isinstance(target_channel, discord.TextChannel):
        return {
            "success": False,
            "error": "Starboard channel must be a server text channel.",
        }

    if emoji_mode != "any" and not emoji_triggers:
        emoji_triggers = ["⭐"]

    resolved_emojis = []
    invalid = []
    for token in emoji_triggers:
        resolved = _resolve_emoji_token(guild, token)
        if resolved:
            resolved_emojis.append(resolved)
        else:
            invalid.append(token)

    if invalid:
        return {
            "success": False,
            "error": "Unknown emoji: " + ", ".join(invalid),
        }

    existing = await get_starboard_settings(guild.id)
    allow_self_star = (
        allow_self_star_override
        if allow_self_star_override is not None
        else (bool(existing.get("allow_self_star")) if existing else False)
    )
    enabled = True

    await upsert_starboard_settings(
        guild.id,
        channel_id,
        resolved_emojis,
        threshold,
        allow_self_star=allow_self_star,
        enabled=enabled,
        emoji_mode=emoji_mode,
    )

    display_emojis = "any emoji" if emoji_mode == "any" else " ".join(resolved_emojis)
    return {
        "success": True,
        "message": (
            f"Starboard configured: <#{channel_id}>, triggers: {display_emojis}, "
            f"threshold: {threshold} reactions"
        ),
    }


async def execute_welcome_setup(
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
) -> Dict[str, Any]:
    channel_id = params.get("channel_id")
    try:
        channel_id = int(channel_id) if channel_id is not None else None
    except (TypeError, ValueError):
        channel_id = None

    message = (params.get("message") or params.get("welcome_message") or "").strip()
    dm_message = (params.get("dm_message") or params.get("dm_welcome_message") or "").strip()
    dm_enabled_raw = params.get("dm_enabled")
    dm_enabled = None
    if dm_enabled_raw is not None:
        if isinstance(dm_enabled_raw, str):
            dm_enabled = dm_enabled_raw.strip().lower() in {"true", "yes", "on", "1", "enable", "enabled"}
        else:
            dm_enabled = bool(dm_enabled_raw)

    existing = await get_welcome_config(guild.id)
    if channel_id is None:
        channel_id = existing.get("welcome_channel_id")
    if not message:
        message = existing.get("welcome_message_template") or ""

    missing = []
    if not channel_id:
        missing.append("channel")

    if missing:
        summary = _summarize_welcome_params(channel_id, message, dm_message, dm_enabled)
        return {
            "success": False,
            "needs_confirmation": True,
            "missing": missing,
            "summary": summary,
        }

    await set_welcome_channel_id(guild.id, channel_id)
    if message:
        await set_welcome_message_template(guild.id, message)
    if dm_message:
        await set_dm_welcome_message(guild.id, dm_message)
    if dm_enabled is not None:
        await set_dm_welcome_enabled(guild.id, dm_enabled)

    return {
        "success": True,
        "message": f"Welcome system configured for <#{channel_id}>.",
    }


async def execute_automod_add(
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
) -> Dict[str, Any]:
    keyword = (params.get("keyword") or "").strip()
    action = (params.get("action") or "").strip().lower()
    allowed_actions = {"delete", "timeout", "mute", "kick", "ban"}
    if action and action not in allowed_actions:
        return {"success": False, "error": f"Invalid automod action '{action}'."}
    duration_raw = params.get("duration")
    try:
        duration = int(duration_raw) if duration_raw is not None else None
    except (TypeError, ValueError):
        duration = None

    missing = []
    if not keyword:
        missing.append("keyword")
    if not action:
        missing.append("action")

    if action in {"timeout", "mute"} and duration is None:
        duration = 10

    if missing:
        summary = _summarize_automod_params(keyword, action, duration)
        return {
            "success": False,
            "needs_confirmation": True,
            "missing": missing,
            "summary": summary,
            "defaults": {
                "duration": duration if duration is not None else 10,
            },
        }

    await add_automod_rule(guild.id, keyword, action, duration_minutes=duration or 0)
    return {
        "success": True,
        "message": f"Automod rule set: '{keyword}' -> {action}.",
    }


async def execute_automod_remove(
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
) -> Dict[str, Any]:
    keyword = (params.get("keyword") or "").strip()
    if not keyword:
        summary = _summarize_automod_params(keyword, None, None)
        return {
            "success": False,
            "needs_confirmation": True,
            "missing": ["keyword"],
            "summary": summary,
        }

    removed = await remove_automod_rule(guild.id, keyword)
    if not removed:
        return {"success": False, "error": f"No automod rule found for '{keyword}'."}
    return {"success": True, "message": f"Automod rule removed: '{keyword}'."}


async def execute_config_mode(
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
    bot: Optional[discord.Client] = None,
) -> Dict[str, Any]:
    mode = (params.get("mode") or params.get("mode_name") or "").strip().lower()
    mode_map = {
        "default": "mode_default",
        "clanker": "mode_default",
        "femboy": "mode_femboy",
        "tsundere": "mode_tsundere",
        "oneesan": "mode_oneesan",
        "mode_default": "mode_default",
        "mode_femboy": "mode_femboy",
        "mode_tsundere": "mode_tsundere",
        "mode_oneesan": "mode_oneesan",
    }
    resolved = mode_map.get(mode)
    if not resolved:
        summary = _summarize_config_mode(mode)
        return {
            "success": False,
            "needs_confirmation": True,
            "missing": ["mode"],
            "summary": summary,
        }

    await set_server_mode(guild.id, resolved)
    if bot:
        social = bot.get_cog("Social")
        if social and hasattr(social, "_apply_mode_profile_updates"):
            try:
                await social._apply_mode_profile_updates(guild.id, resolved, None)
            except Exception:
                pass
    return {"success": True, "message": f"Mode switched to {resolved}."}


async def execute_config_log(
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member,
    current_channel_id: Optional[int] = None,
) -> Dict[str, Any]:
    channel_id = params.get("channel_id")
    try:
        channel_id = int(channel_id) if channel_id is not None else None
    except (TypeError, ValueError):
        channel_id = None

    if channel_id is None:
        channel_hint = str(params.get("channel") or "").strip().lower()
        if channel_hint in {"this channel", "current channel", "here"}:
            channel_id = current_channel_id

    if not channel_id:
        summary = _summarize_config_log(channel_id)
        return {
            "success": False,
            "needs_confirmation": True,
            "missing": ["channel"],
            "summary": summary,
        }

    await set_mod_log_channel_id(guild.id, channel_id)
    return {"success": True, "message": f"Mod log set to <#{channel_id}>."}
