from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import discord

from utils.db_handler import (
    add_automod_rule,
    get_starboard_settings,
    get_welcome_config,
    remove_automod_rule,
    set_dm_welcome_message,
    set_dm_welcome_enabled,
    set_mod_log_channel_id,
    set_server_mode,
    set_welcome_channel_id,
    set_welcome_message_template,
    upsert_starboard_settings,
)

ADMIN_ACTIONS = {
    "STARBOARD_SETUP": "execute_starboard_setup",
    "WELCOME_SETUP": "execute_welcome_setup",
    "AUTOMOD_ADD": "execute_automod_add",
    "AUTOMOD_REMOVE": "execute_automod_remove",
    "CONFIG_MODE": "execute_config_mode",
    "CONFIG_LOG": "execute_config_log",
}

CUSTOM_EMOJI_RE = re.compile(r"<a?:\w+:(\d+)>")


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

    if not (executor.guild_permissions.administrator or executor.guild_permissions.manage_guild):
        return {"success": False, "error": "Insufficient permissions."}

    handler_name = ADMIN_ACTIONS[action]
    handler = globals().get(handler_name)
    if not handler:
        return {"success": False, "error": "Action handler missing."}

    if handler_name == "execute_config_mode":
        return await handler(params or {}, guild, executor, bot=bot)
    if handler_name in {"execute_starboard_setup", "execute_config_log"}:
        return await handler(params or {}, guild, executor, current_channel_id=current_channel_id)
    return await handler(params or {}, guild, executor)


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
    allow_self_star = bool(existing.get("allow_self_star")) if existing else False
    enabled = True if existing is None else bool(existing.get("enabled", True))

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
