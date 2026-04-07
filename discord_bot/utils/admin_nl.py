from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(slots=True)
class AdminNLContext:
    current_channel_id: int | None = None
    channel_mentions: dict[str, int] = field(default_factory=dict)
    role_mentions: dict[str, int] = field(default_factory=dict)
    member_mentions: dict[str, int] = field(default_factory=dict)
    reply_member_id: int | None = None

    def normalized_channels(self) -> dict[str, int]:
        return {_normalize_name(name): channel_id for name, channel_id in self.channel_mentions.items()}

    def normalized_roles(self) -> dict[str, int]:
        return {_normalize_name(name): role_id for name, role_id in self.role_mentions.items()}

    def normalized_members(self) -> dict[str, int]:
        return {_normalize_name(name): member_id for name, member_id in self.member_mentions.items()}


@dataclass(slots=True)
class AdminNLResult:
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    follow_up_question: str | None = None
    requires_confirmation: bool = False
    confirmation_scope: str | None = None


@dataclass(slots=True)
class PendingAdminRequest:
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_scope: str | None = None


def _normalize_name(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = lowered.lstrip("#@&")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _clean_extracted_name(value: str) -> str:
    cleaned = (value or "").strip().rstrip(".!?")
    cleaned = cleaned.strip("\"'`“”‘’")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\b(?:please|pls|thanks|thank you)\b$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _extract_quoted_value(text: str) -> str | None:
    quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", text or "")
    if not quoted:
        return None
    value = _clean_extracted_name(quoted[0])
    return value or None


def _extract_named_tail(text: str, patterns: list[str]) -> str | None:
    quoted = _extract_quoted_value(text)
    if quoted:
        return quoted
    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if not match:
            continue
        value = _clean_extracted_name(match.group(1))
        if value:
            return value
    return None


def _extract_named_reference(text: str, prefix: str, mapping: dict[str, int]) -> int | None:
    normalized = mapping
    for token in re.findall(rf"{re.escape(prefix)}([A-Za-z0-9_\-]+)", text or ""):
        resolved = normalized.get(_normalize_name(token))
        if resolved is not None:
            return resolved
    return None


def _extract_channel_id(text: str, context: AdminNLContext) -> int | None:
    lowered = (text or "").lower()
    match = re.search(r"<#(\d+)>", text or "")
    if match:
        return int(match.group(1))
    if "this channel" in lowered or re.search(r"\bhere\b", lowered):
        return context.current_channel_id
    direct = _extract_named_reference(text, "#", context.normalized_channels())
    if direct is not None:
        return direct
    normalized_text = _normalize_name(text)
    for name, channel_id in sorted(context.normalized_channels().items(), key=lambda item: len(item[0]), reverse=True):
        pattern = r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])"
        if re.search(pattern, normalized_text):
            return channel_id
    return None


def _extract_role_id(text: str, context: AdminNLContext) -> int | None:
    match = re.search(r"<@&(\d+)>", text or "")
    if match:
        return int(match.group(1))
    return _extract_named_reference(text, "@", context.normalized_roles())


def _extract_member_id(text: str, context: AdminNLContext) -> int | None:
    match = re.search(r"<@!?(\d+)>", text or "")
    if match:
        return int(match.group(1))
    return _extract_named_reference(text, "@", context.normalized_members())


def _extract_channel_creation_name(text: str, channel_kind: str) -> str | None:
    pattern_map = {
        "category": [
            r"(?:create|make|add|setup|set up)\s+(?:a\s+)?category(?:\s+(?:named|called))?\s+(.+)$",
        ],
        "voice": [
            r"(?:create|make|add|setup|set up)\s+(?:a\s+)?(?:voice channel|vc)(?:\s+(?:named|called))?\s+(.+)$",
        ],
        "text": [
            r"(?:create|make|add|setup|set up)\s+(?:a\s+)?(?:text\s+channel|channel)(?:\s+(?:named|called))?\s+(.+)$",
        ],
    }
    return _extract_named_tail(text, pattern_map[channel_kind])


def _extract_channel_delete_name(text: str, channel_kind: str | None) -> str | None:
    patterns = [
        r"(?:delete|remove)\s+(?:the\s+)?(?:text\s+channel|channel)(?:\s+(?:named|called))?\s+(.+)$",
        r"(?:delete|remove)\s+(?:the\s+)?(?:voice\s+channel|vc)(?:\s+(?:named|called))?\s+(.+)$",
        r"(?:delete|remove)\s+(?:the\s+)?category(?:\s+(?:named|called))?\s+(.+)$",
    ]
    if channel_kind == "category":
        patterns = [patterns[2]]
    elif channel_kind == "voice":
        patterns = [patterns[1]]
    elif channel_kind == "text":
        patterns = [patterns[0]]
    return _extract_named_tail(text, patterns)


def _extract_follow_up_name(reply_text: str) -> str | None:
    quoted = _extract_quoted_value(reply_text)
    if quoted:
        return quoted
    value = _clean_extracted_name(reply_text)
    return value or None


def _extract_role_name(text: str, *, allow_bare_follow_up: bool = False) -> str | None:
    patterns = [
        r"(?:create|make|add)\s+(?:a\s+)?role(?:\s+(?:named|called))?\s+(.+)$",
        r"(?:delete|remove)\s+(?:the\s+)?role(?:\s+(?:named|called))?\s+(.+)$",
        r"(?:delete|remove)\s+(?:the\s+)?(.+?)\s+role$",
    ]
    value = _extract_named_tail(text, patterns)
    if value:
        return value
    if allow_bare_follow_up:
        return _extract_follow_up_name(text)
    return None


def _detect_channel_kind(text: str) -> str | None:
    lowered = (text or "").lower()
    if "category" in lowered:
        return "category"
    if re.search(r"\bvoice channel\b|\bvc\b", lowered):
        return "voice"
    if "channel" in lowered or "text channel" in lowered:
        return "text"
    return None


def _extract_starboard_emoji_params(text: str) -> dict[str, Any]:
    lowered = (text or "").lower()
    if "any emoji" in lowered or re.search(r"\bany\b.*\bemoji\b", lowered):
        return {"emoji_mode": "any"}
    custom_matches = re.findall(r"<a?:[^>]+>", text or "")
    if custom_matches:
        return {"emoji_mode": "list", "emoji_triggers": custom_matches}
    if "⭐" in (text or "") or "🌟" in (text or "") or re.search(r"\bstars?\b", lowered):
        return {"emoji_mode": "list", "emoji_triggers": ["⭐"]}
    return {}


def _extract_starboard_threshold(text: str) -> int | None:
    more_than = _extract_first_number(r"more than\s+(\d+)\s+reactions?", text)
    if more_than is not None:
        return more_than + 1
    at_least = _extract_first_number(r"at least\s+(\d+)\s+reactions?", text)
    if at_least is not None:
        return at_least
    or_more = _extract_first_number(r"(\d+)\s+(?:reactions?|stars?)\s+or more", text)
    if or_more is not None:
        return or_more
    return (
        _extract_first_number(r"(?:at|of)\s+(\d+)\s+reactions?", text)
        or _extract_first_number(r"(\d+)\s+reactions?", text)
        or _extract_first_number(r"(\d+)\s+stars?", text)
    )


def _extract_url_pattern_values(text: str, keyword: str) -> str | None:
    lowered = (text or "").lower()
    start = lowered.find(keyword)
    if start < 0:
        return None
    segment = (text or "")[start + len(keyword):]
    segment = re.sub(
        r"^\s*(?:links?|urls?)\s+(?:from\s+)?",
        "",
        segment,
        flags=re.IGNORECASE,
    )
    segment = re.split(
        r"\b(?:in\s+url\s+safety|for\s+url\s+safety|on\s+url\s+safety|with\s+url\s+safety|and\s+(?:allow|block|warn|delete)\b)",
        segment,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    segment = segment.strip().rstrip(".!?")
    if not segment:
        return None
    parts = [
        part.strip().rstrip(".!?")
        for part in re.split(r"\s*(?:,|\band\b)\s*", segment, flags=re.IGNORECASE)
        if part.strip()
    ]
    cleaned = [
        part for part in parts
        if part.lower() not in {"link", "links", "url", "urls", "from"}
    ]
    if not cleaned:
        return None
    return ",".join(cleaned)


def _extract_first_number(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _finalize_result(
    *,
    intent: str,
    params: dict[str, Any],
    required: list[str],
    follow_ups: dict[str, str],
    requires_confirmation: bool = False,
    confirmation_scope: str | None = None,
) -> AdminNLResult:
    missing = []
    for name in required:
        value = params.get(name)
        if value is None or value == "" or value == []:
            missing.append(name)
    follow_up_question = follow_ups[missing[0]] if missing else None
    return AdminNLResult(
        intent=intent,
        params=params,
        missing=missing,
        follow_up_question=follow_up_question,
        requires_confirmation=requires_confirmation,
        confirmation_scope=confirmation_scope,
    )


def _parse_starboard_config(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "starboard" not in lowered:
        return None
    if not re.search(r"\b(set|setup|set up|configure|enable|make|create|send)\b", lowered):
        return None

    params: dict[str, Any] = {}
    channel_id = _extract_channel_id(text, context)
    if channel_id is not None:
        params["channel_id"] = channel_id

    params.update(_extract_starboard_emoji_params(text))
    threshold = _extract_starboard_threshold(text)
    if threshold is not None:
        params["threshold"] = threshold

    return _finalize_result(
        intent="starboard.configure",
        params=params,
        required=["channel_id", "emoji_mode", "threshold"],
        follow_ups={
            "channel_id": "Which channel should I use for the starboard?",
            "emoji_mode": "Which emoji should trigger starboard, or should I allow any emoji?",
            "threshold": "How many reactions should a post need before it goes to starboard?",
        },
    )


def _parse_starboard_ignore(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "starboard" not in lowered:
        return None
    if "unignore" in lowered or "watch again" in lowered:
        channel_id = _extract_channel_id(text, context)
        return _finalize_result(
            intent="starboard.unignore_channel",
            params={"channel_id": channel_id} if channel_id is not None else {},
            required=["channel_id"],
            follow_ups={"channel_id": "Which channel should starboard watch again?"},
        )
    if "ignore" in lowered:
        channel_id = _extract_channel_id(text, context)
        return _finalize_result(
            intent="starboard.ignore_channel",
            params={"channel_id": channel_id} if channel_id is not None else {},
            required=["channel_id"],
            follow_ups={"channel_id": "Which channel should starboard ignore?"},
        )
    return None


def _parse_starboard_toggle(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "starboard" not in lowered:
        return None
    if re.search(r"\b(turn off|disable|stop)\b", lowered):
        return _finalize_result(
            intent="starboard.toggle",
            params={"enabled": False},
            required=[],
            follow_ups={},
        )
    if re.search(r"\b(turn on|enable)\b", lowered):
        return _finalize_result(
            intent="starboard.toggle",
            params={"enabled": True},
            required=[],
            follow_ups={},
        )
    return None


def _parse_welcome_dm_toggle(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "welcome" not in lowered or "dm" not in lowered:
        return None
    if re.search(r"\b(turn off|disable|stop|remove|clear)\b", lowered):
        return _finalize_result(
            intent="welcome.dm.toggle",
            params={"dm_enabled": False},
            required=[],
            follow_ups={},
        )
    if re.search(r"\b(turn on|enable)\b", lowered):
        return _finalize_result(
            intent="welcome.dm.toggle",
            params={"dm_enabled": True},
            required=[],
            follow_ups={},
        )
    return None


def _parse_welcome_dm_message(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "welcome" not in lowered or "dm" not in lowered or "message" not in lowered:
        return None
    quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", text or "")
    if not quoted:
        return None
    return _finalize_result(
        intent="welcome.dm.configure",
        params={"dm_message": quoted[0].strip()},
        required=["dm_message"],
        follow_ups={"dm_message": "What DM welcome message should I use?"},
    )


def _parse_welcome_message_clear(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "welcome" not in lowered or ("message" not in lowered and "messages" not in lowered):
        return None
    if not re.search(r"\b(clear|remove|delete|reset)\b", lowered):
        return None
    if re.search(r"\bdm welcome message\b", lowered):
        return _finalize_result(
            intent="welcome.dm.message.clear",
            params={},
            required=[],
            follow_ups={},
        )
    if re.search(r"\bwelcome message\b", lowered):
        return _finalize_result(
            intent="welcome.message.clear",
            params={},
            required=[],
            follow_ups={},
        )
    if re.search(r"\bwelcome messages\b", lowered):
        return _finalize_result(
            intent="welcome.toggle",
            params={"welcome_enabled": False},
            required=[],
            follow_ups={},
        )
    return None


def _parse_welcome_public(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "welcome" not in lowered or "message" not in lowered:
        return None
    if "dm" in lowered:
        return None
    if not re.search(r"\b(set|configure|change|update|edit|use|post)\b", lowered):
        return None
    quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", text or "")
    params: dict[str, Any] = {}
    channel_id = _extract_channel_id(text, context)
    if channel_id is not None:
        params["channel_id"] = channel_id
    if quoted:
        params["message"] = quoted[0].strip()
    return _finalize_result(
        intent="welcome.configure",
        params=params,
        required=["channel_id", "message"],
        follow_ups={
            "channel_id": "Which channel should I use for welcome messages?",
            "message": "What welcome message should I use?",
        },
    )


def _parse_welcome_toggle(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "welcome" not in lowered or "dm" in lowered:
        return None
    if "message" not in lowered and "messages" not in lowered and "welcomes" not in lowered:
        return None
    if re.search(r"\b(turn off|disable|stop|remove)\b", lowered):
        return _finalize_result(
            intent="welcome.toggle",
            params={"welcome_enabled": False},
            required=[],
            follow_ups={},
        )
    if re.search(r"\b(turn on|enable)\b", lowered):
        return _finalize_result(
            intent="welcome.toggle",
            params={"welcome_enabled": True},
            required=[],
            follow_ups={},
        )
    return None


def _parse_spam_config(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "spam" not in lowered and "spammers" not in lowered:
        return None
    if "message" not in lowered or "second" not in lowered or "minute" not in lowered:
        return None
    max_messages = _extract_first_number(r"after\s+(\d+)\s+messages?", text)
    window_seconds = _extract_first_number(r"in\s+(\d+)\s+seconds?", text)
    timeout_minutes = _extract_first_number(r"for\s+(\d+)\s+minutes?", text)
    if max_messages is None or window_seconds is None or timeout_minutes is None:
        return None
    return _finalize_result(
        intent="automod.spam.configure",
        params={
            "spam_timeout_enabled": True,
            "spam_max_messages": max_messages,
            "spam_window_seconds": window_seconds,
            "spam_timeout_minutes": timeout_minutes,
        },
        required=["spam_max_messages", "spam_window_seconds", "spam_timeout_minutes"],
        follow_ups={
            "spam_max_messages": "What spam message threshold should I use?",
            "spam_window_seconds": "What spam time window should I use in seconds?",
            "spam_timeout_minutes": "How many minutes should the spam timeout last?",
        },
    )


def _parse_url_safety(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "url safety" not in lowered and "unsafe url" not in lowered and "unsafe urls" not in lowered and "unsafe link" not in lowered and "unsafe links" not in lowered:
        return None
    if not re.search(r"\b(make|set|configure|update|enable|disable|turn|allow|block|warn|delete)\b", lowered):
        return None
    params: dict[str, Any] = {"url_safety_enabled": True}
    if "delete" in lowered:
        params["url_safety_action"] = "delete"
    elif "warn" in lowered:
        params["url_safety_action"] = "warn"
    allow_values = _extract_url_pattern_values(text, "allow")
    if allow_values:
        params["url_allowlist"] = allow_values
    block_values = _extract_url_pattern_values(text, "block")
    if block_values:
        params["url_blocklist"] = block_values
    required = [] if ("url_allowlist" in params or "url_blocklist" in params or "url_safety_action" in params) else ["url_safety_action"]
    return _finalize_result(
        intent="url_safety.configure",
        params=params,
        required=required,
        follow_ups={"url_safety_action": "Should URL safety warn or delete?"},
    )


def _parse_modlog(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "mod log" not in lowered and "moderation log" not in lowered and "modlog" not in lowered:
        return None
    if re.search(r"\b(clear|disable|remove|turn off)\b", lowered):
        return _finalize_result(
            intent="modlog.clear",
            params={},
            required=[],
            follow_ups={},
        )
    if not re.search(r"\b(set|use|move|configure|change|update)\b", lowered):
        return None
    channel_id = _extract_channel_id(text, context)
    return _finalize_result(
        intent="modlog.set",
        params={"channel_id": channel_id} if channel_id is not None else {},
        required=["channel_id"],
        follow_ups={"channel_id": "Which channel should I use for the mod log?"},
    )


def _parse_autorole(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "autorole" not in lowered:
        return None
    if re.search(r"\b(clear|remove|disable|turn off)\b", lowered):
        return _finalize_result(
            intent="autorole.clear",
            params={},
            required=[],
            follow_ups={},
        )

    params: dict[str, Any] = {}
    role_id = _extract_role_id(text, context)
    if role_id is not None:
        params["role_id"] = role_id
    return _finalize_result(
        intent="autorole.set",
        params=params,
        required=["role_id"],
        follow_ups={"role_id": "Which role should I set as the autorole?"},
    )


def _parse_staff(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "staff" not in lowered:
        return None
    role_id = _extract_role_id(text, context)
    if re.search(r"\b(clear all|clear staff|remove all staff)\b", lowered):
        return _finalize_result(
            intent="staff.clear",
            params={},
            required=[],
            follow_ups={},
        )
    if re.search(r"\b(remove|unmake|take off)\b", lowered):
        return _finalize_result(
            intent="staff.remove",
            params={"role_id": role_id} if role_id is not None else {},
            required=["role_id"],
            follow_ups={"role_id": "Which role should I remove from bot staff?"},
        )
    if re.search(r"\b(make|add|set)\b", lowered):
        params: dict[str, Any] = {}
        if role_id is not None:
            params["role_id"] = role_id
        level = _extract_first_number(r"level\s+(\d+)", text)
        if level is not None:
            params["permission_level"] = level
        return _finalize_result(
            intent="staff.add",
            params=params,
            required=["role_id", "permission_level"],
            follow_ups={
                "role_id": "Which role should I add as bot staff?",
                "permission_level": "What staff level should I use?",
            },
        )
    return None


def _parse_automod_keyword(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "containing" not in lowered and "keyword" not in lowered:
        return None
    quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", text or "")
    keyword = quoted[0].strip() if quoted else None
    if not keyword:
        return None
    if "remove" in lowered or "delete rule" in lowered:
        return _finalize_result(
            intent="automod.keyword.remove",
            params={"keyword": keyword},
            required=["keyword"],
            follow_ups={"keyword": "Which keyword rule should I remove?"},
        )
    action = None
    if re.search(r"\bdelete\b", lowered):
        action = "delete"
    elif re.search(r"\btimeout\b", lowered):
        action = "timeout"
    elif re.search(r"\bkick\b", lowered):
        action = "kick"
    elif re.search(r"\bban\b", lowered):
        action = "ban"
    if not action:
        return None
    params = {"keyword": keyword, "action": action}
    duration = _extract_first_number(r"for\s+(\d+)\s+minutes?", text)
    if duration is not None:
        params["duration"] = duration
    return _finalize_result(
        intent="automod.keyword.add",
        params=params,
        required=["keyword", "action"],
        follow_ups={
            "keyword": "Which keyword should I use for the automod rule?",
            "action": "What action should the automod rule take?",
        },
    )


def _extract_reason_after_target(text: str) -> str | None:
    match = re.search(r"\bfor\s+(.+)$", text.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    reason = match.group(1).strip().rstrip(".!?")
    return reason or None


def _parse_ban(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\bban\b", lowered):
        return None
    target_id = _extract_member_id(text, context)
    if target_id is None and context.reply_member_id is not None:
        if re.search(r"\b(them|that user|this user|that member|this member)\b", lowered) or lowered.strip() == "ban":
            target_id = context.reply_member_id
    params: dict[str, Any] = {}
    if target_id is not None:
        params["target_id"] = target_id
    reason = _extract_reason_after_target(text)
    if reason:
        params["reason"] = reason
    return _finalize_result(
        intent="moderation.ban",
        params=params,
        required=["target_id"],
        follow_ups={"target_id": "Who should I ban?"},
    )


def _parse_timeout(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\b(timeout|mute)\b", lowered):
        return None
    params: dict[str, Any] = {}
    target_id = _extract_member_id(text, context)
    if target_id is None and context.reply_member_id is not None:
        if re.search(r"\b(them|that user|this user|that member|this member)\b", lowered) or lowered.strip() in {"timeout", "mute"}:
            target_id = context.reply_member_id
    if target_id is not None:
        params["target_id"] = target_id
    duration = _extract_first_number(r"for\s+(\d+)\s+minutes?", text)
    if duration is not None:
        params["duration"] = duration
    return _finalize_result(
        intent="moderation.timeout",
        params=params,
        required=["target_id", "duration"],
        follow_ups={
            "target_id": "Who should I timeout?",
            "duration": "How many minutes should the timeout last?",
        },
    )


def _parse_kick(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\bkick\b", lowered):
        return None
    target_id = _extract_member_id(text, context)
    if target_id is None and context.reply_member_id is not None:
        if re.search(r"\b(them|that user|this user|that member|this member)\b", lowered) or lowered.strip() == "kick":
            target_id = context.reply_member_id
    params: dict[str, Any] = {}
    if target_id is not None:
        params["target_id"] = target_id
    return _finalize_result(
        intent="moderation.kick",
        params=params,
        required=["target_id"],
        follow_ups={"target_id": "Who should I kick?"},
    )


def _parse_unban(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\bunban\b", lowered):
        return None
    target_id = _extract_member_id(text, context)
    if target_id is None and context.reply_member_id is not None:
        if re.search(r"\b(them|that user|this user|that member|this member)\b", lowered) or lowered.strip() == "unban":
            target_id = context.reply_member_id
    params: dict[str, Any] = {}
    if target_id is not None:
        params["target_id"] = target_id
    return _finalize_result(
        intent="moderation.unban",
        params=params,
        required=["target_id"],
        follow_ups={"target_id": "Who should I unban?"},
    )


def _parse_channel_delete(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\b(delete|remove)\b", lowered):
        return None
    if "channel" not in lowered and "category" not in lowered:
        return None
    channel_kind = _detect_channel_kind(text)
    channel_id = _extract_channel_id(text, context)
    channel_name = None if channel_id is not None else _extract_channel_delete_name(text, channel_kind)
    params: dict[str, Any] = {}
    if channel_id is not None:
        params["channel_id"] = channel_id
    if channel_name:
        params["channel_name"] = channel_name
    if channel_kind:
        params["channel_kind"] = channel_kind
    intent = "channel.delete"
    confirmation_scope = "delete_channel_or_category"
    follow_up = "Which channel or category should I delete?"
    required = [] if channel_id is not None or channel_name else ["channel_id"]
    return _finalize_result(
        intent=intent,
        params=params,
        required=required,
        follow_ups={"channel_id": follow_up},
        requires_confirmation=True,
        confirmation_scope=confirmation_scope,
    )


def _parse_channel_create(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\b(create|make|add|setup|set up)\b", lowered):
        return None
    channel_kind = _detect_channel_kind(text)
    if channel_kind is None:
        return None
    channel_name = _extract_channel_creation_name(text, channel_kind)
    intent_map = {
        "text": "channel.create_text",
        "voice": "channel.create_voice",
        "category": "channel.create_category",
    }
    return _finalize_result(
        intent=intent_map[channel_kind],
        params={"channel_name": channel_name} if channel_name else {},
        required=["channel_name"],
        follow_ups={"channel_name": "What should I name it?"},
    )


def _parse_role_assign(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\b(give|add|assign|grant)\b", lowered):
        return None
    role_id = _extract_role_id(text, context)
    if role_id is None:
        return None
    target_id = _extract_member_id(text, context)
    params: dict[str, Any] = {"role_id": role_id}
    if target_id is not None:
        params["target_id"] = target_id
    return _finalize_result(
        intent="role.assign",
        params=params,
        required=["role_id", "target_id"],
        follow_ups={
            "role_id": "Which role should I assign?",
            "target_id": "Who should I give that role to?",
        },
    )


def _parse_role_remove(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if not re.search(r"\b(remove|take|unassign)\b", lowered):
        return None
    if " from " not in lowered and " off " not in lowered:
        return None
    role_id = _extract_role_id(text, context)
    if role_id is None:
        return None
    target_id = _extract_member_id(text, context)
    params: dict[str, Any] = {"role_id": role_id}
    if target_id is not None:
        params["target_id"] = target_id
    return _finalize_result(
        intent="role.remove",
        params=params,
        required=["role_id", "target_id"],
        follow_ups={
            "role_id": "Which role should I remove?",
            "target_id": "Who should I remove that role from?",
        },
    )


def _parse_role_create(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "role" not in lowered:
        return None
    if not re.search(r"\b(create|make|add)\b", lowered):
        return None
    role_name = _extract_role_name(text)
    return _finalize_result(
        intent="role.create",
        params={"role_name": role_name} if role_name else {},
        required=["role_name"],
        follow_ups={"role_name": "What should I name the role?"},
    )


def _parse_role_delete(text: str, context: AdminNLContext) -> AdminNLResult | None:
    lowered = (text or "").lower()
    if "role" not in lowered:
        return None
    if not re.search(r"\b(delete|remove)\b", lowered):
        return None
    if " from " in lowered:
        return None
    role_id = _extract_role_id(text, context)
    role_name = None if role_id is not None else _extract_role_name(text)
    params: dict[str, Any] = {}
    if role_id is not None:
        params["role_id"] = role_id
    if role_name:
        params["role_name"] = role_name
    required = [] if role_id is not None or role_name else ["role_name"]
    return _finalize_result(
        intent="role.delete",
        params=params,
        required=required,
        follow_ups={"role_name": "Which role should I delete?"},
    )


def _parse_mode_change(text: str) -> AdminNLResult | None:
    lowered = (text or "").lower()
    mode_match = re.search(r"\b(femboy|tsundere|oneesan|default|clanker)\b", lowered)
    if not mode_match:
        return None
    if not re.search(r"\b(mode|persona)\b", lowered) and not re.search(r"\b(set|switch|change|use)\b", lowered):
        return None
    return _finalize_result(
        intent="config.mode",
        params={"mode": mode_match.group(1)},
        required=["mode"],
        follow_ups={"mode": "Which mode should I switch the server to?"},
    )


def interpret_admin_request(text: str, context: AdminNLContext) -> AdminNLResult | None:
    for parser in (
        _parse_channel_create,
        _parse_role_assign,
        _parse_role_remove,
        _parse_role_create,
        _parse_role_delete,
        _parse_starboard_ignore,
        _parse_starboard_toggle,
        _parse_starboard_config,
        _parse_welcome_message_clear,
        _parse_welcome_dm_message,
        _parse_welcome_dm_toggle,
        _parse_welcome_toggle,
        _parse_welcome_public,
        _parse_mode_change,
        _parse_spam_config,
        _parse_url_safety,
        _parse_modlog,
        _parse_autorole,
        _parse_staff,
        _parse_automod_keyword,
        _parse_timeout,
        _parse_kick,
        _parse_unban,
        _parse_ban,
        _parse_channel_delete,
    ):
        if parser in {
            _parse_role_assign,
            _parse_role_remove,
            _parse_role_delete,
            _parse_starboard_ignore,
            _parse_starboard_config,
            _parse_welcome_public,
            _parse_modlog,
            _parse_autorole,
            _parse_staff,
            _parse_ban,
            _parse_timeout,
            _parse_kick,
            _parse_unban,
            _parse_channel_delete,
        }:
            result = parser(text, context)
        else:
            result = parser(text)
        if result is not None:
            return result
    return None


def _merge_params(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if value not in {None, "", []}:
            merged[key] = value
    return merged


def resume_admin_request(
    pending: PendingAdminRequest,
    reply_text: str,
    context: AdminNLContext,
) -> AdminNLResult:
    if pending.intent == "starboard.configure":
        params = dict(pending.params)
        channel_id = _extract_channel_id(reply_text, context)
        if channel_id is not None:
            params["channel_id"] = channel_id
        params.update(_extract_starboard_emoji_params(reply_text))
        threshold = _extract_starboard_threshold(reply_text)
        if threshold is not None:
            params["threshold"] = threshold
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["channel_id", "emoji_mode", "threshold"],
            follow_ups={
                "channel_id": "Which channel should I use for the starboard?",
                "emoji_mode": "Which emoji should trigger starboard, or should I allow any emoji?",
                "threshold": "How many reactions should a post need before it goes to starboard?",
            },
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "autorole.set":
        params = dict(pending.params)
        role_id = _extract_role_id(reply_text, context)
        if role_id is not None:
            params["role_id"] = role_id
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["role_id"],
            follow_ups={"role_id": "Which role should I set as the autorole?"},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "welcome.configure":
        params = dict(pending.params)
        channel_id = _extract_channel_id(reply_text, context)
        if channel_id is not None:
            params["channel_id"] = channel_id
        quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", reply_text or "")
        if quoted:
            params["message"] = quoted[0].strip()
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["channel_id", "message"],
            follow_ups={
                "channel_id": "Which channel should I use for welcome messages?",
                "message": "What welcome message should I use?",
            },
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent in {"starboard.ignore_channel", "starboard.unignore_channel", "modlog.set"}:
        params = dict(pending.params)
        channel_id = _extract_channel_id(reply_text, context)
        if channel_id is not None:
            params["channel_id"] = channel_id
        follow_up_map = {
            "starboard.ignore_channel": "Which channel should starboard ignore?",
            "starboard.unignore_channel": "Which channel should starboard watch again?",
            "modlog.set": "Which channel should I use for the mod log?",
        }
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["channel_id"],
            follow_ups={"channel_id": follow_up_map[pending.intent]},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "moderation.ban":
        params = dict(pending.params)
        target_id = _extract_member_id(reply_text, context)
        if target_id is not None:
            params["target_id"] = target_id
        reason = _extract_reason_after_target(reply_text)
        if reason:
            params["reason"] = reason
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["target_id"],
            follow_ups={"target_id": "Who should I ban?"},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "moderation.timeout":
        params = dict(pending.params)
        target_id = _extract_member_id(reply_text, context)
        if target_id is not None:
            params["target_id"] = target_id
        duration = _extract_first_number(r"for\s+(\d+)\s+minutes?", reply_text) or _extract_first_number(r"(\d+)\s+minutes?", reply_text)
        if duration is not None:
            params["duration"] = duration
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["target_id", "duration"],
            follow_ups={
                "target_id": "Who should I timeout?",
                "duration": "How many minutes should the timeout last?",
            },
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent in {"moderation.kick", "moderation.unban"}:
        params = dict(pending.params)
        target_id = _extract_member_id(reply_text, context)
        if target_id is not None:
            params["target_id"] = target_id
        follow_up = "Who should I kick?" if pending.intent == "moderation.kick" else "Who should I unban?"
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["target_id"],
            follow_ups={"target_id": follow_up},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "staff.remove":
        params = dict(pending.params)
        role_id = _extract_role_id(reply_text, context)
        if role_id is not None:
            params["role_id"] = role_id
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["role_id"],
            follow_ups={"role_id": "Which role should I remove from bot staff?"},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "url_safety.configure":
        params = dict(pending.params)
        lowered = (reply_text or "").lower()
        if "delete" in lowered:
            params["url_safety_action"] = "delete"
        elif "warn" in lowered:
            params["url_safety_action"] = "warn"
        allow_values = _extract_url_pattern_values(reply_text, "allow")
        if allow_values:
            params["url_allowlist"] = allow_values
        block_values = _extract_url_pattern_values(reply_text, "block")
        if block_values:
            params["url_blocklist"] = block_values
        required = [] if (
            "url_safety_action" in params
            or "url_allowlist" in params
            or "url_blocklist" in params
        ) else ["url_safety_action"]
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=required,
            follow_ups={"url_safety_action": "Should URL safety warn or delete?"},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "channel.delete":
        params = dict(pending.params)
        channel_id = _extract_channel_id(reply_text, context)
        if channel_id is not None:
            params["channel_id"] = channel_id
            params.pop("channel_name", None)
        elif "channel_name" not in params:
            channel_name = _extract_channel_delete_name(reply_text, params.get("channel_kind"))
            if channel_name is None:
                channel_name = _extract_follow_up_name(reply_text)
            if channel_name:
                params["channel_name"] = channel_name
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=[] if params.get("channel_id") is not None or params.get("channel_name") else ["channel_id"],
            follow_ups={"channel_id": "Which channel or category should I delete?"},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent in {"channel.create_text", "channel.create_voice", "channel.create_category"}:
        params = dict(pending.params)
        channel_name = _extract_follow_up_name(reply_text)
        if channel_name:
            params["channel_name"] = channel_name
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["channel_name"],
            follow_ups={"channel_name": "What should I name it?"},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent in {"role.create", "role.delete"}:
        params = dict(pending.params)
        role_id = _extract_role_id(reply_text, context)
        if role_id is not None:
            params["role_id"] = role_id
        elif "role_name" not in params:
            role_name = _extract_role_name(reply_text, allow_bare_follow_up=True)
            if role_name:
                params["role_name"] = role_name
        required = [] if params.get("role_id") is not None or params.get("role_name") else ["role_name"]
        follow_up = "What should I name the role?" if pending.intent == "role.create" else "Which role should I delete?"
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=required,
            follow_ups={"role_name": follow_up},
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent in {"role.assign", "role.remove"}:
        params = dict(pending.params)
        role_id = _extract_role_id(reply_text, context)
        if role_id is not None:
            params["role_id"] = role_id
        target_id = _extract_member_id(reply_text, context)
        if target_id is not None:
            params["target_id"] = target_id
        follow_ups = {
            "role.assign": {
                "role_id": "Which role should I assign?",
                "target_id": "Who should I give that role to?",
            },
            "role.remove": {
                "role_id": "Which role should I remove?",
                "target_id": "Who should I remove that role from?",
            },
        }
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["role_id", "target_id"],
            follow_ups=follow_ups[pending.intent],
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    if pending.intent == "staff.add":
        params = dict(pending.params)
        role_id = _extract_role_id(reply_text, context)
        if role_id is not None:
            params["role_id"] = role_id
        level = _extract_first_number(r"level\s+(\d+)", reply_text)
        if level is not None:
            params["permission_level"] = level
        return _finalize_result(
            intent=pending.intent,
            params=params,
            required=["role_id", "permission_level"],
            follow_ups={
                "role_id": "Which role should I add as bot staff?",
                "permission_level": "What staff level should I use?",
            },
            requires_confirmation=pending.requires_confirmation,
            confirmation_scope=pending.confirmation_scope,
        )

    params = dict(pending.params)
    if pending.requires_confirmation and reply_text.strip().lower() in {"confirm", "yes", "ok", "okay"}:
        params["_confirmed"] = True
    return _finalize_result(
        intent=pending.intent,
        params=params,
        required=list(pending.missing),
        follow_ups={name: f"Please provide {name}." for name in pending.missing},
        requires_confirmation=pending.requires_confirmation,
        confirmation_scope=pending.confirmation_scope,
    )
