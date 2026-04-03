"""
AI Brain Cog for Femmy Discord Bot
===================================
Core AI functionality using Google Gemini API.
Handles conversation context, persona switching, and response generation.

Features:
    - 30-minute rolling context window (deque)
    - Three distinct personality modes
    - User fact injection into prompts
    - Chain memory for multi-user attribution

Usage:
    !mode femboy    - Switch to obedient femboy brother
    !mode tsundere  - Switch to tsundere younger sister  
    !mode oneesan   - Switch to caring older sister
"""

from collections import deque
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional
import json
import os
import re
import tempfile

import discord
import pytz
from PIL import Image
from discord.ext import commands

from utils.db_handler import (
    get_server_mode,
    increment_stat,
    get_affection_by_mode,
    get_evil_mode,
    get_strict_alias,
    get_gender_roles,
    get_user,
    get_last_wellbeing_date,
    set_last_wellbeing_date,
    get_staff_roles,
    get_mod_log_channel_id,
    get_guild_config,
    get_server_memory,
    get_persona_attributes,
    get_sample_dialogues,
    get_guild_custom_personas,
    delete_short_term_facts_for_channel,
    get_channel_recency_summary,
    get_guild_recency_summary,
    get_personal_memories,
    get_mention_lookup_personal_memories,
)
try:
    from utils.db_handler import get_active_persona_modes
except ImportError:  # Backward-compatible fallback until persona runtime config is present.
    get_active_persona_modes = None
from utils.api_manager import UserInputError, stream_events_from_text
from utils.expression_cache import ExpressionService, get_expression_service
from utils.guild_ai import (
    generate_guild_gemini_text,
    generate_guild_gemini_vision,
    generate_guild_openrouter_text,
    generate_guild_custom_text,
    stream_guild_gemini_text,
    stream_guild_openrouter_text,
    stream_guild_custom_text,
    get_guild_gemini_keys,
    get_guild_gemini_model,
    GuildConfigError,
)
from utils.admin_actions import execute_admin_action
from modes import get_mode_profile, get_all_modes
from utils.rate_limiter import StreamSendBudget, ai_limiter, get_rate_limit_message
from utils.logger import get_logger, log_stream_event, log_stream_result
from utils.tool_registry import (
    register_builtin_tools,
    execute_tool,
)
from utils.tool_context import ToolContext
from tools.contracts import ToolCallEnvelope, ToolInvocationMode, ToolTurnContext
from tools.executor import execute_tool_envelope
from tools.transports.prompt_emulated import (
    build_prompt_tool_schemas,
    parse_prompt_tool_call,
    render_prompt_tool_definitions,
    strip_prompt_tool_call,
)
from utils.rag_store import get_rag_context
from utils.text_splitter import split_message
from utils.context_builder import (
    build_structured_prompt,
    build_memory_context_sections,
    section_from_lines,
    section_from_text,
    ContextSection,
)
from utils.emoji_penalty import filter_duplicate_custom_emojis
from utils.output_cleaner import clean_llm_output, normalize_custom_emojis_for_llm
from utils.message_cooldown import (
    check_reply_cooldown,
    clear_channel_scoped_reply_cooldowns,
    normalize_cooldown_type,
    set_reply_cooldown,
)
from utils.streaming.discord_sender import DiscordReplySession
from utils.streaming.buffer import SemanticBuffer
from utils.streaming.orchestrator import StreamOrchestrator
from utils.streaming.session_registry import ChannelStreamBusyError, ChannelStreamRegistry
from utils.streaming.thought_logger import ThoughtLogger
from utils.streaming.types import DiscordSendPolicy, StreamEvent, ThoughtLogSettings
from utils.streaming.typing_manager import TypingKeepalive
from utils.persona_queue import PersonaInvocationJob, PersonaQueueManager
from utils.webhook_identity import ChannelWebhookIdentityManager, build_persona_webhook_context

# Context window: stores last 20 messages within 30 minutes
MAX_CONTEXT_SIZE = 20
CONTEXT_EXPIRY_MINUTES = 30
CHAIN_MEMORY_LIMIT = 1000
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_AUTO_IMAGE_COUNT = 3
MAX_AUTO_VIDEO_COUNT = 1
SUPPORTED_IMAGE_FORMATS = {"image/png", "image/jpeg", "image/gif", "image/webp"}
SUPPORTED_VIDEO_FORMATS = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/mpeg",
    "video/ogg",
}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mpeg", ".mpg", ".ogv", ".mkv"}

# Conversation continuation settings
ACTIVE_CONVO_MESSAGES = 3  # Stay engaged for N messages after trigger
ACTIVE_CONVO_TIMEOUT = 300  # 5 minutes timeout


logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
WELLBEING_NIGHT_START = 20
WELLBEING_NIGHT_END = 23


AGENTIC_JSON_PATTERN = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)
AGENTIC_JSON_BARE_PATTERN = re.compile(r"^\s*(\{.*\})\s*$", re.DOTALL)
ADMIN_ACTION_PATTERN = re.compile(r"```admin_action\s*(\{.*?\})\s*```", re.DOTALL)
ADMIN_CONFIRM_TOKENS = {"confirm", "yes", "y", "ok", "okay"}
ADMIN_CANCEL_TOKENS = {"cancel", "stop", "never mind", "nevermind"}
ADMIN_PENDING_TTL_SECONDS = 180
CUSTOM_EMOJI_CANDIDATE_PATTERN = re.compile(r"<a?:[^>]+>|(?<!<a)(?<!<):[A-Za-z0-9_]+:?|[A-Za-z0-9_]+:\d{5,}")
PROCESSING_ACK_MARKERS = (
    "i am processing",
    "i'm processing",
    "processing the request",
    "processing your request",
    "working on your request",
    "working on it",
    "let me check",
    "let me look",
    "one moment",
    "please wait",
    "searching for",
    "looking that up",
)
AUTO_CONTINUE_PROMPT = (
    "Continue now and provide the final answer to the user. "
    "Do not say that you are processing or working on it. "
    "If a tool is required, output only a tool code block."
)

AGENTIC_TOOL_INSTRUCTIONS = """
[AGENTIC TOOL USE]
You can manage roles and moderate users only when the user has agentic permission.
If the user has permission and asks for a role or moderation action, respond ONLY with a JSON code block in this schema:

```json
{
  "action": "manage_role" | "moderate_user" | "manage_channel",
  "sub_action": "create" | "give" | "remove" | "delete" | "ban" | "unban" | "kick" | "timeout" | "mute"
               | "create_category" | "create_text_channel" | "create_voice_channel"
               | "delete_category" | "delete_text_channel" | "delete_voice_channel",
  "target_name": "Role name (if applicable)",
  "channel_name": "Channel or category name (if applicable)",
  "parent_name": "Category name to place channel under (optional)",
  "parent_id": "Category ID to place channel under (optional)",
  "target_id": "USER_ID_NUMERIC",
  "duration": "Timeout duration in minutes (if timeout/mute)",
  "reason": "Reason for action",
  "reply": "Conversational confirmation for the user"
}
```

Notes:
- For role creation only, target_id is optional. If provided, also grant the role.
- For role give/remove and all moderation actions, target_id is required.
- If the user says "me", use the provided User ID for target_id.
- If you need a target_id but it is missing, ask for a mention or numeric ID instead of refusing.
- Agentic actions are administrative tasks. If agentic access is granted, comply regardless of affection level.
- For channels, use manage_channel with create/delete actions and include parent_name or parent_id when asked.

If the user does NOT have permission, refuse politely and do NOT output JSON.
""".strip()

ADMIN_ACTION_INSTRUCTIONS = """
[ADMIN CONFIG ACTIONS]
Only if [Admin config access: yes], you can configure server settings with admin_action JSON.
Supported actions:
- STARBOARD_SETUP: channel_id, emoji_triggers (list) or emoji_mode "any", threshold
- WELCOME_SETUP: channel_id, message, dm_message, dm_enabled
- AUTOMOD_ADD: keyword, action (delete/timeout/kick/ban), duration (minutes)
- AUTOMOD_REMOVE: keyword
- CONFIG_MODE: mode (femboy/tsundere/oneesan)
- CONFIG_LOG: channel_id

If the user asks to configure starboard, respond with:

```admin_action
{"action": "STARBOARD_SETUP", "params": {"channel_id": 123, "emoji_triggers": ["⭐", "🌟"], "emoji_mode": "list", "threshold": 5}}
```

Rules:
- If channel, emojis (list or any), or threshold is missing, ask a short confirmation question and do NOT output admin_action.
- "more than X" -> threshold = X + 1.
- "at least X" or "X or more" -> threshold = X.
- "any emoji" -> emoji_mode = "any" and omit emoji_triggers.
""".strip()

TOOL_CALL_INSTRUCTIONS = """
[TOOLS]
If you need a tool, respond ONLY with a tool code block in this schema:

```tool
{"tool": "tool_name", "args": {"key": "value"}}
```

Do NOT include any other text outside the tool block.
If the user asks what you can do, call the `review_capabilities` tool.
""".strip()

DEFAULT_ROLE_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    add_reactions=True,
    use_external_emojis=True,
)

def _select_relevant_lines(
    items: list[str],
    query: str,
    *,
    limit: int,
) -> list[str]:
    query_tokens = {token for token in re.findall(r"\w+", (query or "").lower()) if len(token) > 2}
    if not items:
        return []
    if not query_tokens:
        return items[:limit]

    scored: list[tuple[int, int, str]] = []
    for index, item in enumerate(items):
        item_tokens = set(re.findall(r"\w+", (item or "").lower()))
        overlap = len(query_tokens & item_tokens)
        scored.append((overlap, -index, item))
    scored.sort(reverse=True)
    selected = [item for score, _neg_index, item in scored if score > 0][:limit]
    if len(selected) < limit:
        seen = set(selected)
        for item in items:
            if item in seen:
                continue
            selected.append(item)
            if len(selected) >= limit:
                break
    return selected


def _find_agentic_json_block(response_text: str) -> Optional[str]:
    if not response_text:
        return None
    match = AGENTIC_JSON_PATTERN.search(response_text)
    if match:
        return match.group(1)

    stripped = response_text.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    if "\"action\"" not in stripped or "\"sub_action\"" not in stripped:
        return None
    bare_match = AGENTIC_JSON_BARE_PATTERN.match(stripped)
    return bare_match.group(1) if bare_match else None


def _find_admin_action_block(response_text: str) -> Optional[str]:
    match = ADMIN_ACTION_PATTERN.search(response_text or "")
    return match.group(1) if match else None


def _strip_admin_action_block(response_text: str) -> str:
    if not response_text:
        return ""
    return ADMIN_ACTION_PATTERN.sub("", response_text).strip()


def _strip_agentic_json_block(response_text: str) -> str:
    if not response_text:
        return ""
    cleaned = AGENTIC_JSON_PATTERN.sub("", response_text).strip()
    if cleaned != response_text:
        return cleaned
    stripped = response_text.strip()
    if AGENTIC_JSON_BARE_PATTERN.match(stripped):
        return ""
    return response_text


def _is_processing_ack_response(response_text: str) -> bool:
    text = (response_text or "").strip().lower()
    if not text:
        return False
    if len(text) > 280:
        return False
    if "http://" in text or "https://" in text:
        return False
    if "\n" in text and len(text.splitlines()) > 2:
        return False
    return any(marker in text for marker in PROCESSING_ACK_MARKERS)


def _apply_bot_controlled_custom_emojis(
    response_text: str,
    user_text: str,
    emoji_manager,
    *,
    emoji_usage_enabled: bool,
    mode: str,
    affection: int,
    evil_mode: bool,
) -> str:
    if not response_text or not emoji_manager or not emoji_usage_enabled:
        return response_text

    stripped = emoji_manager.strip_known_shortcodes(response_text)
    return emoji_manager.append_contextual_emoji(
        response_text=stripped,
        user_text=user_text,
        mode=mode,
        affection=affection,
        evil_mode=evil_mode,
    )


def _should_assign_created_role(message: discord.Message) -> bool:
    content = (message.content or "").lower()
    if not content:
        return False
    triggers = [
        "give it to me",
        "give me",
        "for me",
        "to me",
        "assign me",
        "add me",
        "make me",
    ]
    return any(trigger in content for trigger in triggers)


def _extract_role_name_from_text(content: str) -> Optional[str]:
    if not content:
        return None
    quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", content)
    for token in quoted:
        name = token.strip()
        if name:
            return name

    patterns = [
        r"(?:make|give|assign|add)\s+me\s+(?:the\s+)?(.+?)\s+role\b",
        r"create\s+(?:a\s+)?role\s+(?:named|called)?\s*(.+?)(?:\s+for\s+me|\s+and\s+give|\s*$)",
        r"create\s+(.+?)\s+role\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name:
                return name
    return None


def _extract_role_request(content: str) -> Optional[Dict[str, str]]:
    if not content:
        return None
    lowered = content.lower()
    if "role" not in lowered:
        return None

    quoted = re.findall(r"[\"â€œâ€'â€˜â€™]([^\"â€œâ€'â€˜â€™]+)[\"â€œâ€'â€˜â€™]", content)
    quoted_name = quoted[0].strip() if quoted else ""

    delete_patterns = [
        r"(?:delete|remove)\s+(?:the\s+)?(.+?)\s+role(?:\s+from\s+server|\s+entirely|\s*$)",
        r"(?:delete|remove)\s+role\s+(?:named|called)?\s*(.+?)\s*$",
    ]
    for pattern in delete_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match:
            role_name = match.group(1).strip() if match.group(1) else quoted_name
            role_name = role_name or quoted_name
            if role_name:
                role_name = role_name.strip("\"'`“”‘’ ")
                return {"sub_action": "delete", "target_name": role_name}

    role_name = quoted_name or _extract_role_name_from_text(content)
    if role_name:
        return {"sub_action": "create", "target_name": role_name}
    return None


def _extract_target_member_id(message: discord.Message) -> Optional[int]:
    if not message.mentions:
        return None
    for member in message.mentions:
        if member.bot:
            continue
        return member.id
    return None


def _clean_channel_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    name = re.sub(r"(?:please|pls|thanks|thank you)$", "", name, flags=re.IGNORECASE).strip()
    name = name.strip("\"'“”‘’")
    return name.strip()


def _extract_quoted_items(content: str) -> list[str]:
    quotes = re.findall(r"[\"â€œâ€'â€˜â€™]([^\"â€œâ€'â€˜â€™]+)[\"â€œâ€'â€˜â€™]", content or "")
    return [_clean_channel_name(item) for item in quotes if _clean_channel_name(item)]


def _extract_channel_request(content: str) -> Optional[dict]:
    return _extract_channel_request_v2(content)


def _extract_channel_request_v2(content: str) -> Optional[dict]:
    return _extract_channel_request_v3(content)


def _extract_channel_request_v3(content: str) -> Optional[dict]:
    return _extract_channel_request_resolved(content)


def _extract_channel_request_resolved(content: str) -> Optional[dict]:
    return _extract_channel_request_new(content)


def _extract_channel_request_new(content: str) -> Optional[dict]:
    if not content:
        return None
    content_lower = content.lower()
    has_category = "category" in content_lower
    has_voice = bool(re.search(r"\bvoice channel\b|\bvc\b", content_lower))
    has_text = "text channel" in content_lower
    has_channel = "channel" in content_lower or has_voice or has_text
    if not has_category and not has_channel:
        return None

    quoted_items = _extract_quoted_items(content)

    create_match = re.search(r"\b(create|make|add|setup|set up)\b", content_lower)
    delete_match = re.search(r"\b(delete|remove)\b", content_lower)
    is_delete = bool(delete_match and (not create_match or delete_match.start() <= create_match.start()))

    if has_category:
        channel_kind = "category"
    elif has_voice:
        channel_kind = "voice"
    else:
        channel_kind = "text"

    if channel_kind == "category":
        sub_action = "delete_category" if is_delete else "create_category"
    elif channel_kind == "voice":
        sub_action = "delete_voice_channel" if is_delete else "create_voice_channel"
    else:
        sub_action = "delete_text_channel" if is_delete else "create_text_channel"

    channel_name: Optional[str] = None
    parent_name: Optional[str] = None

    if quoted_items:
        if not is_delete and sub_action in {"create_text_channel", "create_voice_channel"} and len(quoted_items) >= 2:
            channel_name = quoted_items[0]
            parent_name = quoted_items[1]
        else:
            channel_name = quoted_items[0]

    if not channel_name:
        name_patterns = []
        if is_delete:
            if channel_kind == "category":
                name_patterns.append(
                    r"(?:delete|remove)\s+(?:the\s+)?(?:category\s+)?(?:named|called)?\s*([^\n,]+)"
                )
            elif channel_kind == "voice":
                name_patterns.append(
                    r"(?:delete|remove)\s+(?:the\s+)?(?:voice\s+channel|vc)\s+(?:named|called)?\s*([^\n,]+)"
                )
            else:
                name_patterns.append(
                    r"(?:delete|remove)\s+(?:the\s+)?(?:text\s+)?channel\s+(?:named|called)?\s*([^\n,]+)"
                )
        else:
            if channel_kind == "category":
                name_patterns.append(
                    r"(?:create|make|add)\s+(?:a\s+)?category\s+(?:named|called)?\s*([^\n,]+)"
                )
            elif channel_kind == "voice":
                name_patterns.append(
                    r"(?:create|make|add)\s+(?:a\s+)?(?:voice\s+channel|vc)\s+(?:named|called)?\s*([^\n,]+)"
                )
            else:
                name_patterns.append(
                    r"(?:create|make|add)\s+(?:a\s+)?(?:text\s+)?channel\s+(?:named|called)?\s*([^\n,]+)"
                )

        for pattern in name_patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if not match:
                continue
            candidate = _clean_channel_name(match.group(1))
            candidate = re.split(r"\s+(?:under|in)\s+", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if candidate:
                channel_name = candidate
                break

    if not is_delete and sub_action in {"create_text_channel", "create_voice_channel"} and not parent_name:
        parent_match = re.search(
            r"(?:under|inside|in)\s+(?:the\s+)?(?:category\s+)?([#\w\-\s]+)$",
            content,
            flags=re.IGNORECASE,
        )
        if parent_match:
            parent_name = _clean_channel_name(parent_match.group(1))

    if not channel_name:
        return None

    return {
        "sub_action": sub_action,
        "channel_name": channel_name,
        "parent_name": parent_name or None,
    }
    content_lower = content.lower()
    has_category = "category" in content_lower
    has_channel = "channel" in content_lower
    if not has_category and not has_channel:
        return None

    quotes = re.findall(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]", content)
    quote_names = [_clean_channel_name(item) for item in quotes if _clean_channel_name(item)]

    if has_category and has_channel and len(quote_names) >= 2:
        return {
            "sub_action": "create_text_channel",
            "channel_name": quote_names[1],
            "parent_name": quote_names[0],
        }
    if has_category and len(quote_names) >= 1:
        return {
            "sub_action": "create_category",
            "channel_name": quote_names[0],
            "parent_name": None,
        }
    if has_channel and len(quote_names) >= 2 and ("under" in content_lower or "in " in content_lower):
        return {
            "sub_action": "create_text_channel",
            "channel_name": quote_names[0],
            "parent_name": quote_names[1],
        }
    if has_channel and len(quote_names) >= 1:
        return {
            "sub_action": "create_text_channel",
            "channel_name": quote_names[0],
            "parent_name": None,
        }

    category_match = re.search(
        r"(?:create|make|add)\s+(?:a\s+)?category\s+(?:named|called)?\s*([\\w\\- ]+)",
        content,
        flags=re.IGNORECASE,
    )
    if category_match:
        name = _clean_channel_name(category_match.group(1))
        if name:
            return {"sub_action": "create_category", "channel_name": name, "parent_name": None}

    channel_match = re.search(
        r"(?:create|make|add)\s+(?:a\s+)?channel\s+(?:named|called)?\s*([\\w\\- ]+)",
        content,
        flags=re.IGNORECASE,
    )
    if channel_match:
        name = _clean_channel_name(channel_match.group(1))
        if name:
            parent_match = re.search(
                r"(?:under|in)\s+(?:the\s+)?([\\w\\- ]+?)\\s*(?:category)?(?:\\b|$)",
                content,
                flags=re.IGNORECASE,
            )
            parent_name = _clean_channel_name(parent_match.group(1)) if parent_match else None
            return {
                "sub_action": "create_text_channel",
                "channel_name": name,
                "parent_name": parent_name or None,
            }

    return None


def _extract_starboard_request(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if "starboard" not in lowered:
        return None
    if not re.search(r"\b(set|setup|configure|enable|send|create)\b", lowered):
        return None

    params: Dict[str, Any] = {}
    channel_match = re.search(r"<#(\d+)>", text)
    if channel_match:
        params["channel_id"] = int(channel_match.group(1))
    elif "this channel" in lowered or "here" in lowered:
        params["channel"] = "this channel"

    if "any emoji" in lowered or re.search(r"\bany\b.*\bemoji\b", lowered):
        params["emoji_mode"] = "any"
    else:
        custom_emoji_tokens = re.findall(r"<a?:\w+:\d+>", text)
        if custom_emoji_tokens:
            params["emoji_triggers"] = custom_emoji_tokens

    threshold: Optional[int] = None
    more_than_match = re.search(r"more than\s+(\d+)", lowered)
    if more_than_match:
        threshold = int(more_than_match.group(1)) + 1
    else:
        at_least_match = re.search(r"(?:at least|or more)\s+(\d+)", lowered)
        if at_least_match:
            threshold = int(at_least_match.group(1))
        else:
            bare_match = re.search(r"\b(\d+)\s*(?:stars?|reactions?)\b", lowered)
            if bare_match:
                threshold = int(bare_match.group(1))
    if threshold is not None:
        params["threshold"] = threshold

    return params


def _is_admin_intent_content(content: str) -> bool:
    text = (content or "").lower()
    if not text:
        return False
    admin_keywords = (
        "starboard",
        "modlog",
        "moderation log",
        "create channel",
        "delete channel",
        "create category",
        "delete category",
        "create role",
        "delete role",
        "remove role",
        "staff role",
    )
    return any(keyword in text for keyword in admin_keywords)


def _build_admin_confirmation_prompt(result: Dict[str, Any]) -> str:
    missing = result.get("missing") or []
    summary = result.get("summary") or ""
    missing_text = ", ".join(missing) if missing else "details"
    if summary:
        return (
            "I can set that up, but I still need "
            f"{missing_text}. Please confirm: {summary}. Reply \"confirm\" or provide corrections."
        )
    return (
        "I can set that up, but I still need "
        f"{missing_text}. Please confirm the missing details."
    )


async def _get_agentic_permission_level(member: Optional[discord.Member]) -> int:
    """Return the highest agentic permission level for a member (0-2)."""
    if not member or not member.guild:
        return 0
    if member.guild.owner_id == member.id:
        return 2
    if member.guild_permissions.administrator:
        return 2
    staff_roles = await get_staff_roles(member.guild.id)
    user_role_ids = {role.id for role in member.roles}
    level = 0
    for role_id, permission_level in staff_roles:
        if role_id in user_role_ids:
            level = max(level, int(permission_level))
    return level


def _agentic_action_requires_level(action: str) -> int:
    """Map agentic sub_action to required permission level."""
    action = (action or "").lower().strip()
    if action in {"kick", "timeout", "mute"}:
        return 1
    if action in {
        "ban",
        "unban",
        "create",
        "give",
        "remove",
        "delete",
        "create_category",
        "create_text_channel",
        "create_voice_channel",
        "delete_category",
        "delete_text_channel",
        "delete_voice_channel",
    }:
        return 2
    return 2


async def _resolve_member(guild: discord.Guild, target_id: int) -> Optional[discord.Member]:
    member = guild.get_member(target_id)
    if member:
        return member
    try:
        return await guild.fetch_member(target_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def _post_mod_log(
    guild: discord.Guild,
    moderator: discord.Member,
    action: str,
    target: Optional[discord.Member],
    reason: str,
) -> None:
    channel_id = await get_mod_log_channel_id(guild.id)
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title=f"Action: {action}",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Moderator", value=str(moderator), inline=True)
    embed.add_field(name="Target", value=str(target) if target else "Unknown", inline=True)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    await channel.send(embed=embed)


def _is_destructive_agentic_sub_action(sub_action: str) -> bool:
    return sub_action in {"delete", "delete_category", "delete_text_channel", "delete_voice_channel"}


def _summarize_agentic_action(data: Dict[str, Any]) -> str:
    action = (data.get("action") or "").strip()
    sub_action = (data.get("sub_action") or "").strip()
    target = (data.get("target_name") or data.get("channel_name") or "").strip()
    if target:
        return f"{action}:{sub_action} ({target})"
    return f"{action}:{sub_action}"


async def handle_agentic_actions(
    message: discord.Message,
    ai_response_text: str,
    brain: Optional["AIBrain"] = None,
) -> Optional[discord.Message]:
    """Parse and execute agentic JSON actions. Returns sent reply if handled."""
    payload = _find_agentic_json_block(ai_response_text)
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return await message.reply("I couldn't parse that action request.", mention_author=False)
    if not isinstance(data, dict):
        return None
    action = (data.get("action") or "").lower().strip()
    sub_action = (data.get("sub_action") or "").lower().strip()
    if action not in {"manage_role", "moderate_user", "manage_channel"}:
        return None
    if sub_action not in {
        "create",
        "give",
        "remove",
        "delete",
        "ban",
        "unban",
        "kick",
        "timeout",
        "mute",
        "create_category",
        "create_text_channel",
        "create_voice_channel",
        "delete_category",
        "delete_text_channel",
        "delete_voice_channel",
    }:
        return None

    if not message.guild or not isinstance(message.author, discord.Member):
        return await message.reply("Sorry, I can only do that in a server.", mention_author=False)

    required_level = _agentic_action_requires_level(sub_action)
    permission_level = await _get_agentic_permission_level(message.author)

    if permission_level < required_level:
        return await message.reply("Nice try, but you don't have permission to do that.", mention_author=False)

    if _is_destructive_agentic_sub_action(sub_action) and brain and not bool(data.get("_confirmed")):
        brain._store_pending_agentic_action(message.channel.id, message.author.id, data)
        summary = _summarize_agentic_action(data)
        return await message.reply(
            f"This is destructive: **{summary}**. Reply `confirm` to continue or `cancel`.",
            mention_author=False,
        )

    target_id = data.get("target_id")
    target_id_int: Optional[int] = None
    target_id_invalid = False
    if target_id is not None and str(target_id).strip():
        try:
            target_id_int = int(target_id)
        except (TypeError, ValueError):
            target_id_invalid = True

    role_name = (data.get("target_name") or "").strip()
    reason = (data.get("reason") or "No reason provided").strip()
    reply_text = (data.get("reply") or "Done.").strip()

    guild = message.guild
    target_member: Optional[discord.Member] = None
    if target_id_int is not None:
        target_member = await _resolve_member(guild, target_id_int)

    try:
        if data.get("action") == "manage_role":
            if not role_name:
                return await message.reply("Please specify a role name.", mention_author=False)

            role = next(
                (item for item in guild.roles if (item.name or "").lower() == role_name.lower()),
                None,
            )
            if sub_action == "create":
                if not role:
                    role = await guild.create_role(
                        name=role_name,
                        permissions=DEFAULT_ROLE_PERMISSIONS,
                        reason=f"Requested by {message.author}",
                    )
                if target_id_invalid:
                    return await message.reply("I couldn't identify the target user.", mention_author=False)
                if not target_member and _should_assign_created_role(message):
                    target_member = message.author
                if target_member:
                    await target_member.add_roles(role, reason=reason)
            elif sub_action == "give":
                if target_id_invalid or target_id_int is None:
                    return await message.reply("I couldn't identify the target user.", mention_author=False)
                if not role:
                    role = await guild.create_role(
                        name=role_name,
                        permissions=DEFAULT_ROLE_PERMISSIONS,
                        reason=f"Requested by {message.author}",
                    )
                if not target_member:
                    return await message.reply("I couldn't find that member.", mention_author=False)
                await target_member.add_roles(role, reason=reason)
            elif sub_action == "remove":
                if target_id_invalid or target_id_int is None:
                    return await message.reply("I couldn't identify the target user.", mention_author=False)
                if not role:
                    return await message.reply(f"I couldn't find the role '{role_name}'.", mention_author=False)
                if not target_member:
                    return await message.reply("I couldn't find that member.", mention_author=False)
                await target_member.remove_roles(role, reason=reason)
            elif sub_action == "delete":
                if not role:
                    return await message.reply(f"I couldn't find the role '{role_name}'.", mention_author=False)
                await role.delete(reason=reason)
            else:
                return await message.reply("Unknown role action.", mention_author=False)

            await _post_mod_log(
                guild,
                message.author,
                f"role_{sub_action}",
                target_member,
                f"Role: {role_name}. {reason}",
            )

        elif data.get("action") == "moderate_user":
            if target_id_invalid or target_id_int is None:
                return await message.reply("I couldn't identify the target user.", mention_author=False)
            if sub_action == "ban":
                await guild.ban(discord.Object(id=target_id_int), reason=reason)
            elif sub_action == "unban":
                await guild.unban(discord.Object(id=target_id_int), reason=reason)
            elif sub_action == "kick":
                if not target_member:
                    return await message.reply("I couldn't find that member.", mention_author=False)
                await target_member.kick(reason=reason)
            elif sub_action in {"timeout", "mute"}:
                if not target_member:
                    return await message.reply("I couldn't find that member.", mention_author=False)
                duration_raw = data.get("duration")
                try:
                    duration_minutes = int(duration_raw)
                except (TypeError, ValueError):
                    duration_minutes = 10
                duration_minutes = max(1, min(duration_minutes, 40320))
                await target_member.timeout(
                    discord.utils.utcnow() + timedelta(minutes=duration_minutes),
                    reason=reason,
                )
            else:
                return await message.reply("Unknown moderation action.", mention_author=False)

            await _post_mod_log(
                guild,
                message.author,
                sub_action,
                target_member,
                reason,
            )
        elif data.get("action") == "manage_channel":
            channel_name = (data.get("channel_name") or data.get("target_name") or "").strip()
            if not channel_name:
                return await message.reply("Please specify a channel or category name.", mention_author=False)

            parent_id = data.get("parent_id")
            parent_name = (data.get("parent_name") or "").strip()
            category: Optional[discord.CategoryChannel] = None
            if sub_action in {"create_text_channel", "create_voice_channel"}:
                if parent_id:
                    try:
                        parent_id_int = int(parent_id)
                    except (TypeError, ValueError):
                        parent_id_int = None
                    if parent_id_int:
                        parent = guild.get_channel(parent_id_int)
                        if isinstance(parent, discord.CategoryChannel):
                            category = parent
                if category is None and parent_name:
                    for item in guild.categories:
                        if (item.name or "").lower() == parent_name.lower():
                            category = item
                            break
                    if category is None:
                        category = await guild.create_category(
                            name=parent_name,
                            reason=f"Requested by {message.author}",
                        )

            if sub_action == "create_category":
                existing = next(
                    (item for item in guild.categories if (item.name or "").lower() == channel_name.lower()),
                    None,
                )
                category = existing or await guild.create_category(
                    name=channel_name,
                    reason=f"Requested by {message.author}",
                )
            elif sub_action == "create_text_channel":
                await guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    reason=f"Requested by {message.author}",
                )
            elif sub_action == "create_voice_channel":
                await guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    reason=f"Requested by {message.author}",
                )
            elif sub_action == "delete_category":
                matches = [
                    item for item in guild.categories
                    if (item.name or "").lower() == channel_name.lower()
                ]
                if not matches:
                    return await message.reply(f"I couldn't find category '{channel_name}'.", mention_author=False)
                if len(matches) > 1:
                    return await message.reply(
                        f"I found multiple categories named '{channel_name}'. Please use an ID.",
                        mention_author=False,
                    )
                await matches[0].delete(reason=reason)
            elif sub_action == "delete_text_channel":
                matches = [
                    item for item in guild.text_channels
                    if (item.name or "").lower() == channel_name.lower()
                ]
                if not matches:
                    return await message.reply(f"I couldn't find text channel '{channel_name}'.", mention_author=False)
                if len(matches) > 1:
                    return await message.reply(
                        f"I found multiple text channels named '{channel_name}'. Please use an ID.",
                        mention_author=False,
                    )
                await matches[0].delete(reason=reason)
            elif sub_action == "delete_voice_channel":
                matches = [
                    item for item in guild.voice_channels
                    if (item.name or "").lower() == channel_name.lower()
                ]
                if not matches:
                    return await message.reply(f"I couldn't find voice channel '{channel_name}'.", mention_author=False)
                if len(matches) > 1:
                    return await message.reply(
                        f"I found multiple voice channels named '{channel_name}'. Please use an ID.",
                        mention_author=False,
                    )
                await matches[0].delete(reason=reason)
            else:
                return await message.reply("Unknown channel action.", mention_author=False)

            await _post_mod_log(
                guild,
                message.author,
                f"channel_{sub_action}",
                None,
                f"Channel: {channel_name}. {reason}",
            )
        else:
            return await message.reply("Unknown agentic action.", mention_author=False)

        return await message.reply(reply_text, mention_author=False)

    except discord.Forbidden:
        return await message.reply(
            "I don't have permission to do that. Move my role higher.",
            mention_author=False,
        )
    except Exception as exc:
        logger.error("Agentic action failed: %s", exc, exc_info=True)
        return await message.reply(f"Action failed: {exc}", mention_author=False)


async def handle_admin_actions(
    brain: "AIBrain",
    message: discord.Message,
    ai_response_text: str,
) -> Optional[discord.Message]:
    """Parse and execute admin_action JSON blocks."""
    payload = _find_admin_action_block(ai_response_text)
    if not payload:
        return None

    if not message.guild or not isinstance(message.author, discord.Member):
        return await message.reply("Sorry, I can only do that in a server.", mention_author=False)

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return await message.reply("I couldn't parse that admin request.", mention_author=False)

    if not isinstance(data, dict):
        return None

    action = data.get("action")
    params = data.get("params") or {}
    if (
        isinstance(params, dict)
        and action == "STARBOARD_SETUP"
        and not params.get("channel_id")
        and ("this channel" in (message.content or "").lower() or "here" in (message.content or "").lower())
    ):
        params["channel"] = "this channel"

    result = await execute_admin_action(
        action,
        params,
        message.guild,
        message.author,
        bot=brain.bot,
        current_channel_id=message.channel.id,
    )

    if result.get("needs_confirmation"):
        brain._store_pending_admin_action(message.channel.id, message.author.id, action, params, result)
        prompt = _build_admin_confirmation_prompt(result)
        return await message.reply(prompt, mention_author=False)

    if not result.get("success"):
        return await message.reply(result.get("error", "Admin action failed."), mention_author=False)

    cleaned = _strip_admin_action_block(ai_response_text)
    if cleaned:
        return await message.reply(cleaned, mention_author=False)

    return await message.reply(result.get("message", "Done."), mention_author=False)


# ============================================
# Personality System Prompts
# ============================================

class ConversationContext:
    """
    Manages rolling conversation context for a channel.
    
    Attributes:
        messages: Deque of (timestamp, user_id, content) tuples
        max_size: Maximum number of messages to keep
        expiry_minutes: How long messages stay relevant
        
    TODO:
        - [ ] Add user-specific context tracking
        - [ ] Implement context persistence across restarts
    """
    
    def __init__(self, max_size: int = MAX_CONTEXT_SIZE, expiry_minutes: int = CONTEXT_EXPIRY_MINUTES):
        self.messages = deque(maxlen=max_size)
        self.expiry_minutes = expiry_minutes
    
    def add_message(
        self,
        message_id: int,
        user_id: int,
        username: str,
        content: str,
        reply_to_username: Optional[str] = None,
        media: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Add a message to the context."""
        self.messages.append({
            "message_id": message_id,
            "timestamp": datetime.now(),
            "user_id": user_id,
            "username": username,
            "content": content,
            "reply_to_username": reply_to_username,
            "media": media or [],
        })
    
    def get_context(self, min_message_id: Optional[int] = None) -> str:
        """
        Get formatted context string for AI prompt.
        Only includes messages from the last 30 minutes.
        """
        cutoff = datetime.now() - timedelta(minutes=self.expiry_minutes)
        
        valid_messages = []
        for msg in self.messages:
            if msg["timestamp"] <= cutoff:
                continue
            if min_message_id is not None and int(msg.get("message_id", 0)) <= min_message_id:
                continue
            valid_messages.append(msg)
        
        if not valid_messages:
            return "No recent conversation context."
        
        context_lines = []
        for msg in valid_messages:
            reply_to = msg.get("reply_to_username")
            media = msg.get("media") or []
            media_note = ""
            if media:
                files = ", ".join(item.get("filename", "attachment") for item in media[:3])
                media_note = f" [Attachments: {files}]"
            if reply_to:
                context_lines.append(f"{msg['username']} (replying to {reply_to}): {msg['content']}{media_note}")
            else:
                context_lines.append(f"{msg['username']}: {msg['content']}{media_note}")
        
        return "\n".join(context_lines)


class AIBrain(commands.Cog):
    """
    AI Brain Cog - Core intelligence for Femmy.
    
    Handles:
        - Gemini API communication
        - Persona management
        - Context injection
        - Response generation
        
    TODO:
        - [ ] Implement rate limiting
        - [ ] Add response caching for common queries
        - [ ] Handle API errors gracefully
        - [ ] Add conversation summarization
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if get_expression_service(self.bot) is None:
            self.bot.expression_service = ExpressionService(self.bot)
        register_builtin_tools()
        self.contexts: Dict[int, ConversationContext] = {}  # channel_id -> context
        self.chain_memory: Dict[int, int] = {}  # message_id -> user_id
        self.chain_order: deque[int] = deque()
        self.chain_limit = CHAIN_MEMORY_LIMIT
        self._video_clients: Dict[str, tuple] = {}
        self.pending_admin_actions: Dict[tuple[int, int], Dict[str, Any]] = {}
        self.pending_agentic_actions: Dict[tuple[int, int], Dict[str, Any]] = {}
        # Active conversations: (channel_id, user_id) -> {"remaining": int, "last_active": datetime}
        self.active_convos: Dict[tuple[int, int], dict] = {}
        self.reply_cooldowns: Dict[tuple[str, int], datetime] = {}
        self.auto_channel_counters: Dict[tuple[int, int], int] = {}
        self.context_reset_markers: Dict[int, int] = {}
        self.stream_sessions = ChannelStreamRegistry()
        self.persona_queue = PersonaQueueManager()
        self.webhook_identities = ChannelWebhookIdentityManager()
    
    def get_context(self, channel_id: int) -> ConversationContext:
        """Get or create context for a channel."""
        if channel_id not in self.contexts:
            self.contexts[channel_id] = ConversationContext()
        return self.contexts[channel_id]

    async def clear_channel_memory_boundary(
        self,
        guild_id: int,
        channel_id: int,
        marker_message_id: Optional[int] = None,
    ) -> int:
        context = self.get_context(channel_id)
        deleted_short_term = 0
        try:
            deleted_short_term = await delete_short_term_facts_for_channel(guild_id, channel_id)
        except Exception as exc:
            logger.warning(
                "Failed clearing channel short-term memory for channel %s in guild %s: %s",
                channel_id,
                guild_id,
                exc,
            )
        context.messages.clear()
        if marker_message_id:
            self.context_reset_markers[channel_id] = marker_message_id
        else:
            self.context_reset_markers.pop(channel_id, None)

        self.active_convos = {
            key: value for key, value in self.active_convos.items() if key[0] != channel_id
        }
        # Keep compatibility with any older in-memory key shape ((channel_id, user_id)).
        self.reply_cooldowns = {
            key: value
            for key, value in self.reply_cooldowns.items()
            if not (
                isinstance(key, tuple)
                and len(key) == 2
                and isinstance(key[0], int)
                and key[0] == channel_id
            )
        }
        clear_channel_scoped_reply_cooldowns(self.reply_cooldowns, channel_id)
        self.auto_channel_counters = {
            key: value for key, value in self.auto_channel_counters.items() if key[0] != channel_id
        }
        return deleted_short_term

    def _parse_id_list(self, raw: Optional[str]) -> list[int]:
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        ids: list[int] = []
        for item in data:
            try:
                ids.append(int(item))
            except (TypeError, ValueError):
                continue
        return list(dict.fromkeys(ids))

    async def _bot_reply_chain_depth(self, message: discord.Message, max_depth: int = 25) -> int:
        """
        Count bot-authored ancestors across a reply chain.

        This intentionally counts non-contiguous bot messages so alternating
        user/bot reply chains are still bounded by ai_self_reply_limit.
        """
        depth = 0
        cursor: Any = message
        visited_ids: set[int] = set()
        hops = 0

        while hops < max_depth:
            reference = getattr(cursor, "reference", None)
            if not reference:
                break

            resolved = getattr(reference, "resolved", None)
            if resolved is None:
                ref_message_id = getattr(reference, "message_id", None)
                channel = getattr(cursor, "channel", None)
                if ref_message_id and channel and hasattr(channel, "fetch_message"):
                    try:
                        resolved = await channel.fetch_message(int(ref_message_id))
                    except Exception:
                        resolved = None
            if resolved is None:
                break

            resolved_id = getattr(resolved, "id", None)
            if isinstance(resolved_id, int):
                if resolved_id in visited_ids:
                    break
                visited_ids.add(resolved_id)

            author = getattr(resolved, "author", None)
            author_id = getattr(author, "id", None)
            if author_id == self.bot.user.id:
                depth += 1

            cursor = resolved
            hops += 1

        return depth

    async def _send_in_chunks(self, message: discord.Message, text: str) -> discord.Message:
        parts = split_message(text)
        if not parts:
            return await message.reply("...", mention_author=False)
        first = await message.reply(parts[0], mention_author=False)
        for part in parts[1:]:
            await message.channel.send(part)
        return first

    async def _build_stream_sender(
        self,
        message: discord.Message,
        guild_config: dict[str, Any],
        mode: str,
    ) -> DiscordReplySession:
        send_policy = DiscordSendPolicy(
            chunk_limit=1900,
            warmup_edit_window_seconds=float(
                guild_config.get("ai_stream_warmup_edit_window_seconds") or 2.0
            ),
            interruption_hint="Interrupted, ask me to continue.",
        )
        budget = StreamSendBudget(
            max_messages=max(1, int(guild_config.get("ai_stream_max_messages") or 6)),
            max_total_chars=max(500, int(guild_config.get("ai_stream_max_total_chars") or 6000)),
            min_flush_chars=max(20, int(guild_config.get("ai_stream_min_flush_chars") or 120)),
            min_flush_interval=max(0.0, float(guild_config.get("ai_stream_min_interval_seconds") or 1.0)),
        )
        webhook_context = None
        if bool(guild_config.get("ai_persona_webhooks_enabled", 1)):
            try:
                webhook_context = await build_persona_webhook_context(
                    message.guild.id,
                    mode,
                    manager=self.webhook_identities,
                )
            except Exception as exc:
                logger.warning("Failed to prepare persona webhook identity for %s: %s", mode, exc)
        return DiscordReplySession(
            source_message=message,
            send_policy=send_policy,
            budget=budget,
            webhook_context=webhook_context,
        )

    def _clean_stream_chunk(self, text: str, guild_config: dict[str, Any]) -> str:
        cleaned = clean_llm_output(
            text,
            bot_name=getattr(self.bot.user, "display_name", "Femmy"),
            emoji_usage_enabled=False,
        )
        emoji_manager = getattr(self.bot, "emoji_manager", None)
        if emoji_manager:
            return emoji_manager.strip_known_shortcodes(cleaned)
        return cleaned

    async def _build_stream_tool_schemas(
        self,
        *,
        message: discord.Message,
        guild_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        tool_context = self._build_tool_context(message=message, guild_config=guild_config)
        prompt_schemas = await build_prompt_tool_schemas(tool_context)
        return [
            {
                "type": "function",
                "function": schema,
            }
            for schema in prompt_schemas
        ]

    async def _run_non_stream_tool_loop(
        self,
        *,
        prompt: str,
        message: discord.Message,
        guild_config: dict[str, Any],
        allow_evil: bool,
        system_instruction: Optional[str],
        chat_messages: list[dict[str, str]],
    ) -> tuple[str, Optional[discord.Message], Optional[int], int]:
        raw_response = await self.generate_response(
            prompt,
            message.guild.id,
            allow_evil=allow_evil,
            system_instruction=system_instruction,
            messages=chat_messages,
        )
        sent: Optional[discord.Message] = None
        pending_sticker_id: Optional[int] = None
        tool_loops = 0
        max_tool_loops = 4

        while tool_loops < max_tool_loops:
            envelope = parse_prompt_tool_call(raw_response, invocation_mode=ToolInvocationMode.MODEL)
            if not envelope:
                break
            tool_context = self._build_tool_context(
                message=message,
                guild_config=guild_config,
            )
            result = await execute_tool_envelope(
                envelope,
                tool_context,
            )
            tool_name = envelope.tool_name
            if (
                tool_name == "select_sticker_for_response"
                and result.ok
                and isinstance(result.data, dict)
                and result.data.get("sticker_id")
            ):
                try:
                    pending_sticker_id = int(result.data.get("sticker_id"))
                except (TypeError, ValueError):
                    pending_sticker_id = None

            if result.skip_model:
                reply_text = result.user_message or result.summary or "Done."
                sent = await self._send_in_chunks(message, reply_text)
                raw_response = ""
                break

            chat_messages.append({"role": "assistant", "content": raw_response})
            chat_messages.append(
                {
                    "role": "user",
                    "content": f"Tool `{tool_name}` result:\n{result.to_prompt()}",
                }
            )
            raw_response = await self.generate_response(
                prompt,
                message.guild.id,
                allow_evil=allow_evil,
                system_instruction=system_instruction,
                messages=chat_messages,
            )
            tool_loops += 1

        if tool_loops >= max_tool_loops and parse_prompt_tool_call(raw_response, invocation_mode=ToolInvocationMode.MODEL):
            raw_response = (
                "I could not finish all requested tool steps safely in one response. "
                "Please ask again with a narrower request."
            )

        return raw_response, sent, pending_sticker_id, tool_loops

    async def _log_stream_thoughts(
        self,
        *,
        message: discord.Message,
        guild_config: dict[str, Any],
        finish_reason: str,
        partial: bool,
        tool_loops: int,
        raw_text: str,
        reasoning_text: str,
    ) -> None:
        settings = ThoughtLogSettings(
            level=str(guild_config.get("ai_thought_log_level") or "off").lower(),
            channel_id=guild_config.get("ai_thought_channel_id"),
            allow_mod_log_reuse=bool(guild_config.get("ai_thought_log_allow_mod_log") or 0),
            mod_log_channel_id=guild_config.get("mod_log_channel_id"),
        )
        thought_logger = ThoughtLogger(guild=message.guild, settings=settings)
        if settings.level == "off":
            return
        summary_lines = [
            f"guild={message.guild.id}",
            f"channel={message.channel.id}",
            f"message={message.id}",
            f"finish_reason={finish_reason}",
            f"partial={partial}",
            f"tool_loops={tool_loops}",
        ]
        payload = reasoning_text if settings.level == "raw_debug" and reasoning_text else raw_text[:1500]
        await thought_logger.log_summary(" | ".join(summary_lines), payload)

    async def generate_response_stream(
        self,
        prompt: str,
        guild_id: int,
        *,
        allow_evil: bool = True,
        system_instruction: Optional[str] = None,
        messages: Optional[list[dict[str, str]]] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[StreamEvent]:
        if tools:
            yield StreamEvent.provider_error(
                "Prompt-emulated tool calling remains the active runtime standard; streaming provider-native tools are disabled."
            )
            return
        evil_mode = allow_evil and await get_evil_mode(guild_id) if guild_id else False
        try:
            if evil_mode:
                try:
                    async for event in stream_guild_openrouter_text(
                        guild_id,
                        prompt,
                        messages=messages,
                        system_instruction=system_instruction,
                        tools=tools,
                    ):
                        yield event
                    return
                except GuildConfigError as exc:
                    async for event in stream_events_from_text(
                        "Evil mode is enabled, but OpenRouter isn't configured for this server. "
                        "Ask an admin to upload keys with /config env upload."
                    ):
                        yield event
                    return
                except UserInputError:
                    raise
                except Exception as exc:
                    logger.warning("OpenRouter stream failed, falling back to Gemini/custom: %s", exc)

            try:
                async for event in stream_guild_custom_text(
                    guild_id,
                    prompt,
                    messages=messages,
                    system_instruction=system_instruction,
                    tools=tools,
                ):
                    yield event
                return
            except GuildConfigError:
                pass
            except UserInputError:
                raise
            except Exception as exc:
                logger.warning("Custom endpoint stream failed, falling back to Gemini: %s", exc)

            if tools:
                raise RuntimeError("Native streaming tool events are unavailable for the selected provider.")

            async for event in stream_guild_gemini_text(
                guild_id,
                prompt,
                messages=messages,
                system_instruction=system_instruction,
                tools=tools,
            ):
                yield event
        except UserInputError:
            async for event in stream_events_from_text("Sorry, I can't help with that request."):
                yield event
        except GuildConfigError:
            async for event in stream_events_from_text(
                "This server hasn't configured Gemini keys yet. "
                "Ask an admin to upload keys with /config env upload."
            ):
                yield event
        except Exception as exc:
            logger.warning("Streaming generation failed before visible output: %s", exc)
            yield StreamEvent.provider_error(str(exc))

    async def _handle_streaming_turn(
        self,
        *,
        message: discord.Message,
        prompt: str,
        guild_config: dict[str, Any],
        mode: str,
        affection_points: int,
        allow_evil: bool,
        system_instruction: str,
        chat_messages: list[dict[str, str]],
        tool_schemas: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[Optional[discord.Message], str, Optional[int], int]:
        sender = await self._build_stream_sender(message, guild_config, mode)
        pending_sticker_id: Optional[int] = None
        raw_response = ""
        tool_loops = 0
        max_tool_loops = 4
        current_messages = list(chat_messages)

        async with self.stream_sessions.claim(message.channel.id):
            async with TypingKeepalive(message.channel):
                while tool_loops < max_tool_loops:
                    orchestrator = StreamOrchestrator(
                        sender=sender,
                        interruption_hint="Interrupted, ask me to continue.",
                        text_transform=lambda chunk: self._clean_stream_chunk(chunk, guild_config),
                        buffer=SemanticBuffer(
                            min_flush_chars=max(20, int(guild_config.get("ai_stream_min_flush_chars") or 120)),
                            target_flush_chars=max(40, int(guild_config.get("ai_stream_min_flush_chars") or 120)),
                            max_buffer_chars=max(200, int(guild_config.get("ai_stream_min_flush_chars") or 120) * 4),
                        ),
                        stall_timeout_seconds=max(
                            0.0,
                            float(guild_config.get("ai_stream_stall_seconds") or 0.0),
                        )
                        or None,
                    )
                    result = await orchestrator.run(
                        self.generate_response_stream(
                            prompt,
                            message.guild.id,
                            allow_evil=allow_evil,
                            system_instruction=system_instruction,
                            messages=current_messages,
                            tools=tool_schemas,
                        )
                    )
                    log_stream_result(
                        __name__,
                        channel_id=message.channel.id,
                        finish_reason=result.finish_reason,
                        partial=result.partial,
                        should_fallback=result.should_fallback,
                        tool_loops=tool_loops,
                    )
                    raw_response = result.raw_text
                    if result.should_fallback:
                        raw_response, sent, pending_sticker_id, tool_loops = await self._run_non_stream_tool_loop(
                            prompt=prompt,
                            message=message,
                            guild_config=guild_config,
                            allow_evil=allow_evil,
                            system_instruction=system_instruction,
                            chat_messages=current_messages,
                        )
                        return sent or sender.first_message, raw_response, pending_sticker_id, tool_loops

                    tool_call = result.tool_call
                    if not tool_call:
                        emoji_manager = getattr(self.bot, "emoji_manager", None)
                        emoji_usage_enabled = bool(guild_config.get("emoji_usage_enabled", 1))
                        if emoji_manager and emoji_usage_enabled:
                            evil_mode_enabled = False
                            if allow_evil:
                                evil_mode_enabled = await get_evil_mode(message.guild.id)
                            cleaned_response = self._clean_stream_chunk(result.raw_text, guild_config)
                            emoji_suffix = emoji_manager.pick_contextual_emoji(
                                response_text=cleaned_response,
                                user_text=message.content,
                                mode=mode,
                                affection=affection_points,
                                evil_mode=evil_mode_enabled,
                            )
                            if emoji_suffix:
                                emoji_suffix = self._filter_recent_custom_emoji_reuse(
                                    emoji_suffix,
                                    self.get_context(message.channel.id),
                                )
                            if emoji_suffix:
                                await sender.append_interruption_hint(emoji_suffix)
                        await self._log_stream_thoughts(
                            message=message,
                            guild_config=guild_config,
                            finish_reason=result.finish_reason,
                            partial=result.partial,
                            tool_loops=tool_loops,
                            raw_text=result.raw_text,
                            reasoning_text=result.reasoning_text,
                        )
                        return sender.first_message, raw_response, pending_sticker_id, tool_loops

                    tool_context = self._build_tool_context(
                        message=message,
                        guild_config=guild_config,
                    )
                    envelope = ToolCallEnvelope(
                        call_id=tool_call.get("call_id"),
                        tool_name=str(
                            tool_call.get("tool")
                            or tool_call.get("name")
                            or ""
                        ).strip(),
                        arguments=tool_call.get("args") or tool_call.get("arguments") or {},
                        invocation_mode=ToolInvocationMode.MODEL,
                        raw_payload=tool_call,
                    )
                    result_tool = await execute_tool_envelope(
                        envelope,
                        tool_context,
                    )
                    tool_name = envelope.tool_name
                    if (
                        tool_name == "select_sticker_for_response"
                        and result_tool.ok
                        and isinstance(result_tool.data, dict)
                        and result_tool.data.get("sticker_id")
                    ):
                        try:
                            pending_sticker_id = int(result_tool.data.get("sticker_id"))
                        except (TypeError, ValueError):
                            pending_sticker_id = None

                    if result_tool.skip_model:
                        reply_text = result_tool.user_message or result_tool.summary or "Done."
                        await sender.send_text(self._clean_stream_chunk(reply_text, guild_config))
                        await self._log_stream_thoughts(
                            message=message,
                            guild_config=guild_config,
                            finish_reason="tool_skip_model",
                            partial=False,
                            tool_loops=tool_loops,
                            raw_text=reply_text,
                            reasoning_text="",
                        )
                        return sender.first_message, raw_response, pending_sticker_id, tool_loops

                    current_messages.append({"role": "assistant", "content": raw_response})
                    current_messages.append(
                        {
                            "role": "user",
                            "content": f"Tool `{tool_name}` result:\n{result_tool.to_prompt()}",
                        }
                    )
                    tool_loops += 1

        if tool_loops >= max_tool_loops and parse_prompt_tool_call(raw_response, invocation_mode=ToolInvocationMode.MODEL):
            raw_response = (
                "I could not finish all requested tool steps safely in one response. "
                "Please ask again with a narrower request."
            )
        return sender.first_message, raw_response, pending_sticker_id, tool_loops

    def _track_message_id(self, message_id: int, user_id: int) -> None:
        """Track message attribution for chain memory."""
        if message_id in self.chain_memory:
            return
        self.chain_memory[message_id] = user_id
        self.chain_order.append(message_id)
        if len(self.chain_order) > self.chain_limit:
            old_id = self.chain_order.popleft()
            self.chain_memory.pop(old_id, None)

    def _resolve_reply_to(self, message: discord.Message) -> tuple[Optional[int], Optional[str]]:
        """Resolve reply attribution for context formatting."""
        if not message.reference:
            return None, None

        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message):
            return resolved.author.id, resolved.author.display_name

        message_id = message.reference.message_id
        if not message_id:
            return None, None

        user_id = self.chain_memory.get(message_id)
        if not user_id:
            return None, None

        member = message.guild.get_member(user_id) if message.guild else None
        if member:
            return user_id, member.display_name

        user = self.bot.get_user(user_id)
        return user_id, user.display_name if user else None

    def _is_reply_to_bot(self, message: discord.Message) -> bool:
        """Return True when the message is a direct reply to a bot-authored message."""
        if not message.reference:
            return False

        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message):
            return bool(getattr(getattr(resolved, "author", None), "id", None) == self.bot.user.id)

        message_id = message.reference.message_id
        if not message_id:
            return False
        return self.chain_memory.get(message_id) == self.bot.user.id


    def _is_active_conversation(self, channel_id: int, user_id: int) -> bool:
        """Check if the bot is in an active conversation with this user in this channel."""
        key = (channel_id, user_id)
        convo = self.active_convos.get(key)
        if not convo:
            return False
        
        # Check timeout
        elapsed = (datetime.now() - convo["last_active"]).total_seconds()
        if elapsed > ACTIVE_CONVO_TIMEOUT:
            del self.active_convos[key]
            return False
        
        return convo["remaining"] > 0

    def _activate_conversation(self, channel_id: int, user_id: int):
        """Mark a conversation as active after being triggered."""
        key = (channel_id, user_id)
        self.active_convos[key] = {
            "remaining": ACTIVE_CONVO_MESSAGES,
            "last_active": datetime.now()
        }

    def _continue_conversation(self, channel_id: int, user_id: int):
        """Decrement remaining messages in active conversation."""
        key = (channel_id, user_id)
        if key in self.active_convos:
            self.active_convos[key]["remaining"] -= 1
            self.active_convos[key]["last_active"] = datetime.now()
            if self.active_convos[key]["remaining"] <= 0:
                del self.active_convos[key]

    def _refresh_conversation(self, channel_id: int, user_id: int, remaining_messages: Optional[int] = None):
        """Refresh conversation (user re-triggered or mentioned)."""
        key = (channel_id, user_id)
        remaining = remaining_messages if remaining_messages is not None else ACTIVE_CONVO_MESSAGES
        remaining = max(1, int(remaining))
        self.active_convos[key] = {
            "remaining": remaining,
            "last_active": datetime.now()
        }

    def _pending_admin_key(self, channel_id: int, user_id: int) -> tuple[int, int]:
        return (channel_id, user_id)

    def _store_pending_admin_action(
        self,
        channel_id: int,
        user_id: int,
        action: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        self.pending_admin_actions[self._pending_admin_key(channel_id, user_id)] = {
            "action": action,
            "params": params,
            "result": result,
            "created_at": datetime.now(),
        }

    def _pop_pending_admin_action(self, channel_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        return self.pending_admin_actions.pop(self._pending_admin_key(channel_id, user_id), None)

    def _get_pending_admin_action(self, channel_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        pending = self.pending_admin_actions.get(self._pending_admin_key(channel_id, user_id))
        if not pending:
            return None
        created_at = pending.get("created_at")
        if created_at and (datetime.now() - created_at).total_seconds() > ADMIN_PENDING_TTL_SECONDS:
            self._pop_pending_admin_action(channel_id, user_id)
            return None
        return pending

    def _pending_agentic_key(self, channel_id: int, user_id: int) -> tuple[int, int]:
        return (channel_id, user_id)

    def _store_pending_agentic_action(
        self,
        channel_id: int,
        user_id: int,
        data: Dict[str, Any],
    ) -> None:
        self.pending_agentic_actions[self._pending_agentic_key(channel_id, user_id)] = {
            "data": data,
            "created_at": datetime.now(),
        }

    def _pop_pending_agentic_action(self, channel_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        return self.pending_agentic_actions.pop(self._pending_agentic_key(channel_id, user_id), None)

    def _get_pending_agentic_action(self, channel_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        pending = self.pending_agentic_actions.get(self._pending_agentic_key(channel_id, user_id))
        if not pending:
            return None
        created_at = pending.get("created_at")
        if created_at and (datetime.now() - created_at).total_seconds() > ADMIN_PENDING_TTL_SECONDS:
            self._pop_pending_agentic_action(channel_id, user_id)
            return None
        return pending

    async def _handle_pending_agentic_confirmation(self, message: discord.Message) -> Optional[discord.Message]:
        if not message.guild or not isinstance(message.author, discord.Member):
            return None
        content = (message.content or "").strip().lower()
        if not content:
            return None
        pending = self._get_pending_agentic_action(message.channel.id, message.author.id)
        if not pending:
            return None

        if content in ADMIN_CANCEL_TOKENS:
            self._pop_pending_agentic_action(message.channel.id, message.author.id)
            return await message.reply("Cancelled.", mention_author=False)

        if content not in ADMIN_CONFIRM_TOKENS:
            return None

        payload_data = dict(pending.get("data") or {})
        payload_data["_confirmed"] = True
        self._pop_pending_agentic_action(message.channel.id, message.author.id)
        payload = "```json\n" + json.dumps(payload_data, ensure_ascii=False) + "\n```"
        sent = await handle_agentic_actions(message, payload, brain=self)
        if sent:
            return sent
        return await message.reply("I couldn't execute that action.", mention_author=False)

    async def _handle_pending_admin_confirmation(self, message: discord.Message) -> Optional[discord.Message]:
        if not message.guild or not isinstance(message.author, discord.Member):
            return None
        content = (message.content or "").strip().lower()
        if not content:
            return None
        pending = self._get_pending_admin_action(message.channel.id, message.author.id)
        if not pending:
            return None

        if content in ADMIN_CANCEL_TOKENS:
            self._pop_pending_admin_action(message.channel.id, message.author.id)
            return await message.reply("Cancelled.", mention_author=False)

        if content not in ADMIN_CONFIRM_TOKENS:
            return None

        action = pending.get("action")
        params = dict(pending.get("params") or {})
        result = pending.get("result") or {}
        defaults = result.get("defaults") or {}
        missing = result.get("missing") or []

        for key, value in defaults.items():
            params.setdefault(key, value)

        if "channel" in missing and not params.get("channel_id"):
            return await message.reply("Please provide the channel to use.", mention_author=False)

        follow_up = await execute_admin_action(
            action,
            params,
            message.guild,
            message.author,
            bot=self.bot,
            current_channel_id=message.channel.id,
        )
        if follow_up.get("needs_confirmation"):
            self._store_pending_admin_action(
                message.channel.id,
                message.author.id,
                action,
                params,
                follow_up,
            )
            prompt = _build_admin_confirmation_prompt(follow_up)
            return await message.reply(prompt, mention_author=False)

        self._pop_pending_admin_action(message.channel.id, message.author.id)
        if not follow_up.get("success"):
            return await message.reply(follow_up.get("error", "Admin action failed."), mention_author=False)
        return await message.reply(follow_up.get("message", "Done."), mention_author=False)

    async def _get_reply_context(self, message: discord.Message) -> str:
        """Get the content of the message being replied to for context."""
        if not message.reference or not message.reference.message_id:
            return ""
        
        try:
            # Try to get the resolved message first
            if isinstance(message.reference.resolved, discord.Message):
                ref_msg = message.reference.resolved
            else:
                # Fetch the message if not resolved
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
            
            if ref_msg:
                content = ref_msg.content[:200]
                if len(ref_msg.content) > 200:
                    content += "..."
                return f"[Replying to {ref_msg.author.display_name}: \"{content}\"]"
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        
        return ""

    async def _maybe_handle_channel_request(self, message: discord.Message) -> bool:
        if not message.guild or not isinstance(message.author, discord.Member):
            return False
        content = message.content or ""
        content_lower = content.lower()
        if "channel" not in content_lower and "category" not in content_lower:
            logger.debug("Channel fallback: skip (no channel/category keyword).")
            return False

        permission_level = await _get_agentic_permission_level(message.author)
        if permission_level < 2:
            logger.debug(
                "Channel fallback: skip (permission level %s < 2).",
                permission_level,
            )
            return False

        request = _extract_channel_request(content)
        if not request:
            logger.debug(
                "Channel fallback: skip (could not parse request). content=%r",
                content,
            )
            return False

        sub_action = request.get("sub_action")
        channel_name = request.get("channel_name")
        parent_name = request.get("parent_name")
        if not channel_name or not sub_action:
            logger.debug(
                "Channel fallback: skip (missing parsed fields). request=%s",
                request,
            )
            return False

        if sub_action == "create_category":
            reply = f"Done! Created category '{channel_name}'."
        elif sub_action == "create_voice_channel":
            reply = f"Done! Created voice channel '{channel_name}'."
        elif sub_action == "create_text_channel":
            reply = f"Done! Created text channel '{channel_name}'."
        elif sub_action == "delete_category":
            reply = f"Done! Deleted category '{channel_name}'."
        elif sub_action == "delete_voice_channel":
            reply = f"Done! Deleted voice channel '{channel_name}'."
        elif sub_action == "delete_text_channel":
            reply = f"Done! Deleted text channel '{channel_name}'."
        else:
            reply = f"Done! Updated '{channel_name}'."
        payload = {
            "action": "manage_channel",
            "sub_action": sub_action,
            "channel_name": channel_name,
            "parent_name": parent_name,
            "reason": "User request",
            "reply": reply,
        }
        logger.debug("Channel fallback: executing agentic payload %s", payload)
        response_text = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        handled = await handle_agentic_actions(message, response_text, brain=self)
        logger.debug("Channel fallback: handled=%s", handled is not None)
        return handled is not None

    async def _maybe_handle_role_request(self, message: discord.Message) -> bool:
        if not message.guild or not isinstance(message.author, discord.Member):
            return False
        content = message.content or ""
        if "role" not in content.lower():
            logger.debug("Role fallback: skip (no 'role' keyword).")
            return False

        permission_level = await _get_agentic_permission_level(message.author)
        if permission_level < 2:
            logger.debug(
                "Role fallback: skip (permission level %s < 2).",
                permission_level,
            )
            return False

        role_request = _extract_role_request(content)
        if not role_request:
            logger.debug(
                "Role fallback: skip (could not parse role request). content=%r",
                content,
            )
            return False
        role_name = role_request.get("target_name")
        sub_action = role_request.get("sub_action") or "create"
        if not role_name:
            return False
        logger.debug(
            "Role fallback: parsed role request '%s' for user %s.",
            role_name,
            message.author.id,
        )

        target_id = _extract_target_member_id(message)
        if target_id is None and _should_assign_created_role(message):
            target_id = message.author.id
        logger.debug("Role fallback: target_id=%s", target_id)

        payload = {
            "action": "manage_role",
            "sub_action": sub_action,
            "target_name": role_name,
            "target_id": str(target_id) if target_id is not None else None,
            "reason": "User request",
            "reply": (
                f"Done! Deleted the role '{role_name}'."
                if sub_action == "delete"
                else f"Done! Created or assigned the role '{role_name}'."
            ),
        }
        logger.debug("Role fallback: executing agentic payload %s", payload)
        response_text = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        handled = await handle_agentic_actions(message, response_text, brain=self)
        logger.debug("Role fallback: handled=%s", handled is not None)
        return handled is not None

    async def _maybe_handle_starboard_setup_request(self, message: discord.Message) -> bool:
        if not message.guild or not isinstance(message.author, discord.Member):
            return False
        permission_level = await _get_agentic_permission_level(message.author)
        if permission_level < 2:
            return False

        params = _extract_starboard_request(message.content or "")
        if not params:
            return False

        result = await execute_admin_action(
            "STARBOARD_SETUP",
            params,
            message.guild,
            message.author,
            bot=self.bot,
            current_channel_id=message.channel.id,
        )
        if result.get("needs_confirmation"):
            self._store_pending_admin_action(
                message.channel.id,
                message.author.id,
                "STARBOARD_SETUP",
                params,
                result,
            )
            prompt = _build_admin_confirmation_prompt(result)
            await message.reply(prompt, mention_author=False)
            return True

        if not result.get("success"):
            await message.reply(result.get("error", "Starboard setup failed."), mention_author=False)
            return True

        await message.reply(result.get("message", "Starboard configured."), mention_author=False)
        return True

    async def _get_recent_history(self, message: discord.Message, limit: int = 5) -> str:
        """Fetch recent messages before this one for additional context."""
        try:
            history = []
            async for msg in message.channel.history(limit=limit + 1, before=message):
                if msg.author.bot and msg.author != self.bot.user:
                    continue  # Skip other bots
                prefix = f"{msg.author.display_name}: "
                history.append(f"{prefix}{msg.content[:150]}")
            
            if history:
                history.reverse()  # Chronological order
                return "\n".join(history)
        except (discord.Forbidden, discord.HTTPException):
            pass
        
        return ""

    def _is_mention_only(self, message: discord.Message) -> bool:
        """Check if the message only mentions the bot."""
        content = message.content
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.replace(f"<@!{self.bot.user.id}>", "")
        return content.strip() == ""

    def _has_image_attachment(self, message: discord.Message) -> bool:
        """Return True if the message includes an image attachment."""
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                return True
        return False

    def _get_image_attachments(self, message: discord.Message) -> list[discord.Attachment]:
        """Collect supported image attachments for auto vision processing."""
        images = []
        for attachment in message.attachments:
            content_type = attachment.content_type or ""
            if content_type in SUPPORTED_IMAGE_FORMATS or content_type.startswith("image/"):
                if attachment.size <= MAX_IMAGE_SIZE:
                    images.append(attachment)
            if len(images) >= MAX_AUTO_IMAGE_COUNT:
                break
        return images

    def _format_image_descriptions(self, descriptions: list[str]) -> str:
        """Format image descriptions for prompt context."""
        if not descriptions:
            return ""
        if len(descriptions) == 1:
            return f"[User attached image: {descriptions[0]}]"
        numbered = [f"Image {idx + 1}: {desc}" for idx, desc in enumerate(descriptions)]
        return f"[User attached image(s): {'; '.join(numbered)}]"

    async def _get_video_client(self, guild_id: int):
        """Get or create a Gemini video client for this guild."""
        keys = await get_guild_gemini_keys(guild_id)
        if not keys:
            return None
        api_key = keys[0]
        cached = self._video_clients.get(api_key)
        if cached:
            return cached
        try:
            from google import genai as genai_client
            from google.genai import types as genai_types
        except Exception as exc:
            logger.warning("Gemini video client unavailable: %s", exc)
            return None
        client = genai_client.Client(api_key=api_key)
        self._video_clients[api_key] = (client, genai_types)
        return self._video_clients[api_key]

    async def _describe_image(self, guild_id: int, attachment: discord.Attachment) -> Optional[str]:
        """Describe a single image attachment using Gemini Vision."""
        try:
            image_bytes = await attachment.read()
        except Exception as exc:
            logger.warning("Failed to download image %s: %s", attachment.filename, exc)
            return None

        try:
            image = Image.open(BytesIO(image_bytes))
        except Exception as exc:
            logger.warning("Failed to load image %s: %s", attachment.filename, exc)
            return None

        try:
            response_text, _ = await generate_guild_gemini_vision(
                guild_id,
                "Describe this image briefly.",
                image,
            )
        except UserInputError:
            return None
        except GuildConfigError as exc:
            logger.warning("Gemini not configured for guild %s: %s", guild_id, exc)
            return None
        except RuntimeError as exc:
            logger.warning("Vision API exhausted while describing %s: %s", attachment.filename, exc)
            return None
        except Exception as exc:
            logger.error("Vision error describing %s: %s", attachment.filename, exc, exc_info=True)
            return None

        description = response_text.strip()
        if not description:
            return None

        try:
            await increment_stat("images_analyzed", guild_id=message.guild.id)
        except Exception as exc:
            logger.warning("Failed to increment images_analyzed: %s", exc)

        return description

    async def _describe_images(self, message: discord.Message) -> list[str]:
        """Describe supported image attachments in a message."""
        attachments = self._get_image_attachments(message)
        if not attachments:
            return []

        descriptions = []
        for attachment in attachments:
            description = await self._describe_image(message.guild.id, attachment)
            if description:
                descriptions.append(description)
        return descriptions

    def _has_video_attachment(self, message: discord.Message) -> bool:
        """Return True if the message includes a video attachment."""
        for attachment in message.attachments:
            content_type = attachment.content_type or ""
            ext = Path(attachment.filename or "").suffix.lower()
            if content_type.startswith("video/") or content_type in SUPPORTED_VIDEO_FORMATS or ext in SUPPORTED_VIDEO_EXTENSIONS:
                return True
        return False

    def _get_video_attachments(self, message: discord.Message) -> list[discord.Attachment]:
        """Collect supported video attachments for auto analysis."""
        videos = []
        for attachment in message.attachments:
            content_type = attachment.content_type or ""
            ext = Path(attachment.filename or "").suffix.lower()
            if content_type.startswith("video/") or content_type in SUPPORTED_VIDEO_FORMATS or ext in SUPPORTED_VIDEO_EXTENSIONS:
                if attachment.size <= MAX_VIDEO_SIZE:
                    videos.append(attachment)
            if len(videos) >= MAX_AUTO_VIDEO_COUNT:
                break
        return videos

    def _format_video_descriptions(self, descriptions: list[str]) -> str:
        """Format video descriptions for prompt context."""
        if not descriptions:
            return ""
        if len(descriptions) == 1:
            return f"[User attached video: {descriptions[0]}]"
        numbered = [f"Video {idx + 1}: {desc}" for idx, desc in enumerate(descriptions)]
        return f"[User attached video(s): {'; '.join(numbered)}]"

    async def _describe_video(self, guild_id: int, attachment: discord.Attachment) -> Optional[str]:
        """Describe a video using the Gemini File API."""
        client_info = await self._get_video_client(guild_id)
        if not client_info:
            logger.warning("Gemini video client not configured for guild %s.", guild_id)
            return None
        video_client, video_types = client_info

        tmp_video_path = None
        uploaded_name = None
        try:
            suffix = Path(attachment.filename or "").suffix or ".mp4"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_video:
                tmp_video_path = tmp_video.name
            await attachment.save(tmp_video_path)

            video_file = await asyncio.to_thread(
                video_client.files.upload,
                file=tmp_video_path,
                config={"display_name": attachment.filename or "video"},
            )
            uploaded_name = video_file.name

            while getattr(video_file, "state", None) and getattr(video_file.state, "name", None) == "PROCESSING":
                await asyncio.sleep(2)
                video_file = await asyncio.to_thread(video_client.files.get, name=video_file.name)

            if getattr(video_file, "state", None) and getattr(video_file.state, "name", None) == "FAILED":
                logger.warning("Gemini failed to process video %s", attachment.filename)
                return None

            model_id = await get_guild_gemini_model(guild_id)
            response = await asyncio.to_thread(
                video_client.models.generate_content,
                model=model_id,
                contents=[
                    video_types.Part.from_uri(
                        file_uri=video_file.uri,
                        mime_type=video_file.mime_type,
                    ),
                    "Describe this video briefly.",
                ],
            )
            response_text = getattr(response, "text", None)
        except Exception as exc:
            logger.error("Video analysis error for %s: %s", attachment.filename, exc, exc_info=True)
            return None
        finally:
            if tmp_video_path and os.path.exists(tmp_video_path):
                try:
                    os.unlink(tmp_video_path)
                except OSError:
                    logger.warning("Failed to remove temp file %s", tmp_video_path)
            if uploaded_name and os.getenv("GEMINI_DELETE_UPLOADED_FILES", "").lower() == "true":
                try:
                    await asyncio.to_thread(video_client.files.delete, name=uploaded_name)
                except Exception as exc:
                    logger.warning("Failed to delete Gemini file %s: %s", uploaded_name, exc)

        if not response_text:
            return None
        description = response_text.strip()
        if not description:
            return None

        try:
            await increment_stat("images_analyzed", guild_id=message.guild.id)
        except Exception as exc:
            logger.warning("Failed to increment images_analyzed: %s", exc)

        return description

    async def _describe_videos(self, message: discord.Message) -> list[str]:
        """Describe supported video attachments in a message."""
        attachments = self._get_video_attachments(message)
        if not attachments:
            return []

        descriptions = []
        for attachment in attachments:
            description = await self._describe_video(message.guild.id, attachment)
            if description:
                descriptions.append(description)
        return descriptions

    async def _load_persona(self, guild_id: int, mode: str, evil_mode: bool) -> str:
        """Load persona prompt from custom persona or file, falling back to defaults."""
        if mode.startswith("custom_"):
            try:
                from utils.db_handler import get_custom_persona_by_mode_key
                persona = await get_custom_persona_by_mode_key(guild_id, mode)
            except Exception as exc:
                logger.warning("Failed to load custom persona %s: %s", mode, exc)
                persona = None

            if persona:
                if evil_mode and persona.get("evil_prompt"):
                    return persona["evil_prompt"]
                normal_prompt = persona.get("normal_prompt")
                if normal_prompt:
                    return normal_prompt

        profile = get_mode_profile(mode)
        filename = profile.evil_prompt_file if evil_mode else profile.prompt_file
        path = PROMPTS_DIR / filename
        try:
            content = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.warning("Persona file missing: %s", path)
            content = ""

        if content:
            return content
        return profile.persona_fallback

    def _has_trigger_word(self, content: str, mode: str) -> bool:
        """Return True if the content contains a trigger word for the mode."""
        profile = get_mode_profile(mode)
        return self._has_any_trigger(content, profile.triggers)

    def _normalize_trigger_text(self, text: str) -> str:
        normalized = (text or "").lower()
        normalized = normalized.replace("-", " ").replace("_", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _has_any_trigger(self, content: str, triggers: tuple[str, ...]) -> bool:
        normalized = self._normalize_trigger_text(content)
        if not normalized:
            return False
        for trigger in triggers:
            token = self._normalize_trigger_text(trigger)
            if not token:
                continue
            pattern = r"\b" + re.escape(token) + r"\b"
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return True
        return False

    def _parse_aliases_value(self, value: Optional[str]) -> list[str]:
        if not value:
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            data = value
        if isinstance(data, list):
            return [str(item).strip().lower() for item in data if str(item).strip()]
        if isinstance(data, str):
            return [token.strip().lower() for token in re.split(r"[,\\n]+", data) if token.strip()]
        return []

    def _find_first_trigger_position(self, content: str, triggers: tuple[str, ...] | list[str]) -> Optional[int]:
        normalized = self._normalize_trigger_text(content)
        if not normalized:
            return None
        positions: list[int] = []
        for trigger in triggers:
            token = self._normalize_trigger_text(trigger)
            if not token:
                continue
            pattern = r"\b" + re.escape(token) + r"\b"
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                positions.append(match.start())
        return min(positions) if positions else None

    async def _get_triggered_modes_in_order(self, guild_id: int, content: str) -> list[str]:
        matches: list[tuple[int, str]] = []
        for profile in get_all_modes():
            position = self._find_first_trigger_position(content, profile.triggers)
            if position is not None:
                matches.append((position, profile.key))
        try:
            personas = await get_guild_custom_personas(guild_id)
        except Exception:
            personas = []
        for persona in personas:
            name = (persona.get("name") or "").strip()
            aliases = self._parse_aliases_value(persona.get("aliases"))
            triggers = [name] + aliases if name else aliases
            if not triggers:
                continue
            position = self._find_first_trigger_position(content, triggers)
            if position is None:
                continue
            mode_key = persona.get("mode_key")
            if mode_key:
                matches.append((position, mode_key))

        matches.sort(key=lambda item: (item[0], item[1]))
        ordered: list[str] = []
        seen: set[str] = set()
        for _position, mode_key in matches:
            if mode_key in seen:
                continue
            ordered.append(mode_key)
            seen.add(mode_key)
        return ordered

    async def _get_triggered_modes(self, guild_id: int, content: str) -> set[str]:
        return set(await self._get_triggered_modes_in_order(guild_id, content))

    def _build_persona_jobs(
        self,
        *,
        primary_mode_key: str,
        active_mode_keys: list[str],
        triggered_mode_keys: list[str],
        multi_persona_enabled: bool,
        triggered_persona_limit: int,
    ) -> list[PersonaInvocationJob]:
        if multi_persona_enabled:
            active_set = set(active_mode_keys)
            selected: list[PersonaInvocationJob] = []
            for mode_key in triggered_mode_keys:
                if mode_key not in active_set:
                    continue
                selected.append(PersonaInvocationJob(mode_key=mode_key))
                if len(selected) >= max(1, triggered_persona_limit):
                    break
            if selected:
                return selected
        return [PersonaInvocationJob(mode_key=primary_mode_key)]

    async def _get_wellbeing_prompt(
        self,
        member: Optional[discord.Member],
        guild_id: int,
        mode: str
    ) -> tuple[str, Optional[str]]:
        if not member or mode != "mode_oneesan":
            return "", None

        user = await get_user(guild_id, member.id)
        timezone = user.get("timezone") if user else None
        tz_is_set = bool(timezone and timezone != "UTC")

        if tz_is_set:
            try:
                tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                tz_is_set = False
            else:
                local_now = datetime.now(tz)
                if not (WELLBEING_NIGHT_START <= local_now.hour <= WELLBEING_NIGHT_END):
                    return "", None
                date_str = local_now.date().isoformat()
        if not tz_is_set:
            date_str = datetime.utcnow().date().isoformat()

        last_date = await get_last_wellbeing_date(guild_id, member.id)
        if last_date == date_str:
            return "", None

        return (
            "Ask exactly one brief question about their wellbeing or whether they've eaten today.",
            date_str
        )

    async def get_user_gender(
        self,
        member: Optional[discord.Member],
        guild_id: int,
        user_id: int
    ) -> str:
        """Infer gender from configured roles for this server."""
        if not member or not isinstance(member, discord.Member) or not member.guild:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return "unknown"
            cached_member = guild.get_member(user_id)
            if cached_member:
                member = cached_member
            else:
                try:
                    member = await guild.fetch_member(user_id)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    return "unknown"

        gender_roles = await get_gender_roles(guild_id)
        if not gender_roles:
            return "unknown"
        matched_genders = set()
        for role in member.roles:
            gender = gender_roles.get(role.id)
            if gender:
                matched_genders.add(gender.lower())

        if len(matched_genders) == 0:
            return "unknown"
        if len(matched_genders) > 1:
            return "confused"
        return matched_genders.pop()
    
    async def _build_expression_prompt_context(
        self,
        *,
        guild: Optional[discord.Guild],
        message_text: str,
        mode: str,
        affection_points: int,
        recent_context_text: str,
    ) -> tuple[list[str], list[str], list[str]]:
        service = get_expression_service(self.bot)
        if service is None or guild is None:
            return [], [], []
        prompt_context = await service.build_prompt_context(
            guild,
            message_text=message_text,
            mode=mode,
            affection_points=affection_points,
            recent_context_text=recent_context_text,
        )
        return (
            list(prompt_context.summary_lines),
            list(prompt_context.emoji_lines),
            list(prompt_context.sticker_lines),
        )

    def _prompt_to_chat_payload(self, prompt: str) -> tuple[str, list[dict[str, str]]]:
        marker = "\n\n=== CURRENT MESSAGE ===\n\n"
        if marker not in prompt:
            return "", [{"role": "user", "content": prompt}]
        system_block, user_block = prompt.split(marker, 1)
        return system_block.strip(), [{"role": "user", "content": user_block.strip()}]

    def _filter_recent_custom_emoji_reuse(
        self,
        response_text: str,
        context: ConversationContext,
        recent_messages: int = 6,
    ) -> str:
        if not response_text:
            return response_text
        recent_bot_messages: list[str] = []
        for item in list(context.messages)[-recent_messages:]:
            if int(item.get("user_id", 0)) != self.bot.user.id:
                continue
            recent_bot_messages.append(str(item.get("content") or ""))
        return filter_duplicate_custom_emojis(response_text, recent_bot_messages) or response_text

    def _build_tool_context(
        self,
        *,
        message: discord.Message,
        guild_config: dict[str, Any],
    ) -> ToolContext:
        return ToolContext(
            bot=self.bot,
            guild=message.guild,
            channel=message.channel,
            user=message.author,
            message=message,
            guild_config=guild_config,
            locale="en",
        )

    def _build_turn_tool_context(
        self,
        *,
        guild_id: int,
        channel_id: Optional[int],
        member: Optional[discord.Member],
        guild_config: dict[str, Any],
    ) -> ToolTurnContext:
        guild = member.guild if member and getattr(member, "guild", None) else self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild and channel_id else None
        return ToolTurnContext(
            request_id=None,
            turn_id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            thread_id=None,
            user_id=getattr(member, "id", None),
            guild=guild,
            channel=channel,
            member=member,
            guild_config=guild_config,
        )

    async def _prepare_response_text(
        self,
        *,
        message: discord.Message,
        response_text: str,
        guild_config: dict[str, Any],
        mode: str,
        affection_points: int,
        context: ConversationContext,
        allow_evil: bool,
        apply_trigger_emojis: bool = True,
    ) -> str:
        emoji_manager = getattr(self.bot, "emoji_manager", None)
        emoji_usage_enabled = bool(guild_config.get("emoji_usage_enabled", 1))
        response = clean_llm_output(
            response_text,
            bot_name=getattr(self.bot.user, "display_name", "Femmy"),
            emoji_usage_enabled=False,
        )

        evil_mode_enabled = False
        if allow_evil:
            evil_mode_enabled = await get_evil_mode(message.guild.id)

        if apply_trigger_emojis:
            response = _apply_bot_controlled_custom_emojis(
                response_text=response,
                user_text=message.content,
                emoji_manager=emoji_manager,
                emoji_usage_enabled=emoji_usage_enabled,
                mode=mode,
                affection=affection_points,
                evil_mode=evil_mode_enabled,
            )
        response = self._filter_recent_custom_emoji_reuse(response, context)
        return response

    async def _send_sticker_with_recovery(
        self,
        *,
        message: discord.Message,
        sticker_id: int,
        caption: str = "",
        as_reply: bool,
    ) -> Optional[discord.Message]:
        if not message.guild:
            return None
        expression_service = get_expression_service(self.bot)
        sticker = None
        if expression_service is not None:
            sticker = await expression_service.resolve_sticker_for_send(message.guild, int(sticker_id))
        else:
            sticker = discord.utils.get(message.guild.stickers, id=int(sticker_id))
        if not sticker:
            return None

        async def _dispatch(selected_sticker):
            if as_reply:
                if caption:
                    return await message.reply(caption, stickers=[selected_sticker], mention_author=False)
                return await message.reply(stickers=[selected_sticker], mention_author=False)
            if caption:
                return await message.channel.send(caption, stickers=[selected_sticker])
            return await message.channel.send(stickers=[selected_sticker])

        try:
            return await _dispatch(sticker)
        except Exception as exc:
            logger.warning("Failed to send sticker %s on first attempt: %s", sticker_id, exc)
            if expression_service is None:
                return None
            try:
                expression_service.mark_guild_suspect(message.guild.id)
                sticker = await expression_service.resolve_sticker_for_send(message.guild, int(sticker_id))
                if not sticker:
                    return None
                return await _dispatch(sticker)
            except Exception as retry_exc:
                logger.warning("Failed to send sticker %s after refresh retry: %s", sticker_id, retry_exc)
                return None

    async def _resolve_active_persona_modes(
        self,
        guild_id: int,
        primary_mode_key: str,
    ) -> list[str]:
        if get_active_persona_modes is None:
            return [primary_mode_key]
        try:
            modes = await get_active_persona_modes(guild_id)
        except Exception:
            logger.warning("Failed to load active persona modes for guild %s", guild_id, exc_info=True)
            return [primary_mode_key]
        if not modes:
            return [primary_mode_key]
        return [str(mode_key) for mode_key in modes if str(mode_key).strip()]

    async def _execute_persona_invocation(
        self,
        *,
        message: discord.Message,
        context: ConversationContext,
        guild_config: dict[str, Any],
        mode: str,
        content_for_prompt: str,
        context_snapshot: str,
        refresh_conversation: bool,
        remaining_messages: int,
        apply_reply_cooldown_update: bool,
        reply_cooldown_seconds: int,
        reply_cooldown_type: str,
        track_stats: bool,
    ) -> Optional[discord.Message]:
        if mode == "mode_default":
            affection_data = {
                "affection_level": "stranger",
                "affection_points": 0,
                "total_interactions": 0,
            }
        else:
            affection_data = await get_affection_by_mode(message.guild.id, message.author.id, mode)
        affection_points = affection_data.get("affection_points", 0)
        allow_evil = affection_points >= 500
        if mode == "mode_default":
            allow_evil = False

        wellbeing_prompt, wellbeing_date = await self._get_wellbeing_prompt(
            message.author,
            message.guild.id,
            mode,
        )

        prompt = await self.build_prompt(
            message.guild.id,
            message.author.id,
            content_for_prompt,
            context_snapshot,
            channel_id=message.channel.id,
            member=message.author,
            wellbeing_prompt=wellbeing_prompt,
            affection_data=affection_data,
            allow_evil=allow_evil,
            mode_override=mode,
        )
        system_instruction, chat_messages = self._prompt_to_chat_payload(prompt)
        stream_tool_schemas = await self._build_stream_tool_schemas(
            message=message,
            guild_config=guild_config,
        )

        raw_response = ""
        sent: Optional[discord.Message] = None
        interim_sent: Optional[discord.Message] = None
        pending_sticker_id: Optional[int] = None
        streaming_enabled = bool(guild_config.get("ai_streaming_enabled", 1))

        if streaming_enabled:
            try:
                sent, raw_response, pending_sticker_id, _tool_loops = await self._handle_streaming_turn(
                    message=message,
                    prompt=prompt,
                    guild_config=guild_config,
                    mode=mode,
                    affection_points=affection_points,
                    allow_evil=allow_evil,
                    system_instruction=system_instruction,
                    chat_messages=chat_messages,
                    tool_schemas=stream_tool_schemas,
                )
            except ChannelStreamBusyError:
                if track_stats:
                    await message.reply(
                        "I already have an active AI reply in this channel. Give me a moment to finish.",
                        mention_author=False,
                    )
                else:
                    logger.warning(
                        "Skipping queued persona job for channel %s because a stream is already active.",
                        message.channel.id,
                    )
                return None
        else:
            async with message.channel.typing():
                raw_response, sent, pending_sticker_id, tool_loops = await self._run_non_stream_tool_loop(
                    prompt=prompt,
                    message=message,
                    guild_config=guild_config,
                    allow_evil=allow_evil,
                    system_instruction=system_instruction,
                    chat_messages=chat_messages,
                )
            if sent is None:
                interim_preview = strip_prompt_tool_call(raw_response)
                interim_preview = _strip_agentic_json_block(interim_preview)
                interim_preview = _strip_admin_action_block(interim_preview)
                interim_preview = clean_llm_output(
                    interim_preview,
                    bot_name=getattr(self.bot.user, "display_name", "Femmy"),
                    emoji_usage_enabled=bool(guild_config.get("emoji_usage_enabled", 1)),
                )
                if _is_processing_ack_response(interim_preview):
                    interim_sent = await self._send_in_chunks(message, interim_preview)
                    try:
                        async with message.channel.typing():
                            continued_raw = await self._continue_after_processing_ack(
                                prompt=prompt,
                                guild_id=message.guild.id,
                                allow_evil=allow_evil,
                                system_instruction=system_instruction,
                                chat_messages=chat_messages,
                                prior_response=raw_response,
                                message=message,
                                guild_config=guild_config,
                            )
                        continued_preview = strip_prompt_tool_call(continued_raw)
                        continued_preview = _strip_agentic_json_block(continued_preview)
                        continued_preview = _strip_admin_action_block(continued_preview)
                        continued_preview = clean_llm_output(
                            continued_preview,
                            bot_name=getattr(self.bot.user, "display_name", "Femmy"),
                            emoji_usage_enabled=bool(guild_config.get("emoji_usage_enabled", 1)),
                        )
                        if continued_preview and continued_preview != interim_preview:
                            raw_response = continued_raw
                        else:
                            sent = interim_sent
                    except Exception as exc:
                        logger.warning("Auto continuation after processing ack failed: %s", exc)
                        sent = interim_sent

        if sent is None:
            sent = await handle_agentic_actions(message, raw_response, brain=self)
        if sent is None:
            sent = await handle_admin_actions(self, message, raw_response)
        if sent is None:
            response = strip_prompt_tool_call(raw_response)
            response = _strip_agentic_json_block(response)
            response = _strip_admin_action_block(response)
            prepared_response = await self._prepare_response_text(
                message=message,
                response_text=response,
                guild_config=guild_config,
                mode=mode,
                affection_points=affection_points,
                context=context,
                allow_evil=allow_evil,
                apply_trigger_emojis=True,
            )
            sent = await self._send_in_chunks(message, prepared_response)

        if pending_sticker_id and message.guild:
            await self._send_sticker_with_recovery(
                message=message,
                sticker_id=int(pending_sticker_id),
                as_reply=False,
            )

        if refresh_conversation:
            self._refresh_conversation(
                message.channel.id,
                message.author.id,
                remaining_messages=remaining_messages,
            )

        if wellbeing_date:
            await set_last_wellbeing_date(message.guild.id, message.author.id, wellbeing_date)

        if apply_reply_cooldown_update and reply_cooldown_seconds > 0 and reply_cooldown_type != "off":
            set_reply_cooldown(
                self.reply_cooldowns,
                cooldown_type=reply_cooldown_type,
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                user_id=message.author.id,
            )

        if interim_sent and interim_sent.id != sent.id:
            self._track_message_id(interim_sent.id, interim_sent.author.id)
            context.add_message(
                interim_sent.id,
                interim_sent.author.id,
                interim_sent.author.display_name,
                normalize_custom_emojis_for_llm(interim_sent.content),
                reply_to_username=message.author.display_name,
            )
        self._track_message_id(sent.id, sent.author.id)
        context.add_message(
            sent.id,
            sent.author.id,
            sent.author.display_name,
            normalize_custom_emojis_for_llm(sent.content),
            reply_to_username=message.author.display_name,
        )

        if track_stats:
            try:
                await increment_stat("messages_processed", guild_id=message.guild.id)
            except Exception as exc:
                logger.warning("Failed to increment messages_processed: %s", exc)

        return sent

    async def _run_queued_persona_job(self, job: PersonaInvocationJob) -> None:
        message = job.source_message
        if message is None:
            return
        context = self.get_context(message.channel.id)
        await self._execute_persona_invocation(
            message=message,
            context=context,
            guild_config=dict(job.guild_config),
            mode=job.mode_key,
            content_for_prompt=job.content_for_prompt,
            context_snapshot=job.context_snapshot,
            refresh_conversation=False,
            remaining_messages=max(1, int(job.guild_config.get("ai_self_reply_limit") or 3)),
            apply_reply_cooldown_update=False,
            reply_cooldown_seconds=0,
            reply_cooldown_type="off",
            track_stats=False,
        )
    
    async def build_prompt(
        self,
        guild_id: int, 
        user_id: int, 
        message: str, 
        context: str,
        channel_id: Optional[int] = None,
        member: Optional[discord.Member] = None,
        wellbeing_prompt: str = "",
        affection_data: Optional[Dict[str, int]] = None,
        allow_evil: bool = True,
        allow_tools: bool = True,
        mode_override: Optional[str] = None,
    ) -> str:
        """
        Build the full prompt for Gemini.
        
        Components:
            1. System prompt (persona)
            2. User facts (if any)
            3. Conversation context
            4. Current message
            
        TODO:
            - [ ] Add server-specific customizations
            - [ ] Implement fact relevance scoring
        """
        mode = mode_override or await get_server_mode(guild_id)
        evil_mode = allow_evil and await get_evil_mode(guild_id)
        persona = await self._load_persona(guild_id, mode, evil_mode)
        guild_config = await get_guild_config(guild_id)

        personal_facts = await get_personal_memories(guild_id, user_id, limit=5)
        channel_summary = (
            await get_channel_recency_summary(guild_id, channel_id)
            if channel_id is not None
            else []
        )
        guild_summary = await get_guild_recency_summary(guild_id)

        mentioned_ids = set(re.findall(r"<@!?(\d+)>", message))
        mentioned_user_lines: list[str] = []
        mentioned_fact_lines: list[str] = []
        for mentioned_id in mentioned_ids:
            uid = int(mentioned_id)
            if uid == self.bot.user.id or uid == user_id:
                continue
            user_obj = self.bot.get_user(uid)
            name = user_obj.display_name if user_obj else f"User {uid}"
            mentioned_user_lines.append(f"{name} ({uid})")
            other_facts = await get_mention_lookup_personal_memories(guild_id, uid, limit=3)
            for fact in other_facts:
                mentioned_fact_lines.append(f"{name}: {fact}")

        server_memory = await get_server_memory(guild_id)
        selected_server_memory = _select_relevant_lines(server_memory, message, limit=5)
        selected_personal_facts = _select_relevant_lines(personal_facts, message, limit=5)
        selected_mentioned_facts = _select_relevant_lines(mentioned_fact_lines, message, limit=3)
        selected_channel_summary = _select_relevant_lines(channel_summary, message, limit=1)
        selected_guild_summary = _select_relevant_lines(guild_summary, message, limit=1)
        attributes = await get_persona_attributes(guild_id)
        dialogues = await get_sample_dialogues(guild_id)

        rag_context = ""
        try:
            rag_enabled = bool(guild_config.get("rag_enabled") or 0)
            if rag_enabled and str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() in {"1", "true", "yes", "on"}:
                top_k = int(os.getenv("RAG_TOP_K", "4"))
                rag_context = await get_rag_context(guild_id, message, top_k=top_k) or ""
        except Exception as exc:
            logger.warning("RAG lookup failed: %s", exc)

        if affection_data is None:
            if mode == "mode_default":
                affection_data = {
                    "affection_level": "stranger",
                    "affection_points": 0,
                    "total_interactions": 0,
                }
            else:
                affection_data = await get_affection_by_mode(guild_id, user_id, mode)
        affection_level = affection_data.get("affection_level", "stranger")
        affection_points = affection_data.get("affection_points", 0)

        gender = await self.get_user_gender(member, guild_id, user_id)
        if gender == "unknown":
            gender_note = (
                "[User Gender: Unknown. Avoid gendered pronouns or honorifics, "
                "and ask for their preference if relevant.]"
            )
        elif gender == "confused":
            gender_note = (
                "[User Gender: Conflicting roles. Avoid gendered pronouns or honorifics, "
                "and express mild confusion if asked.]"
            )
        elif gender in ("male", "female"):
            gender_note = f"[User Gender: {gender}. Use matching pronouns/honorifics.]"
        else:
            gender_note = (
                f"[User Gender: {gender}. Use the user's stated pronouns if known; "
                "otherwise avoid gendered language or honorifics.]"
            )

        address_note = ""
        if mode == "mode_femboy":
            strict_alias = await get_strict_alias(guild_id, user_id)
            if strict_alias:
                address_note = (
                    f"[Name preference: {strict_alias}. Address the user exactly as \"{strict_alias}\". "
                    "Do NOT use Master/Mistress or other honorifics.]"
                )
            elif affection_points > 800:
                honorific = None
                if gender == "female":
                    honorific = "Mistress"
                elif gender == "male":
                    honorific = "Master"
                if honorific:
                    address_note = f"[Addressing: Call the user {honorific}.]"

        affection_prompts = {
            "stranger": """This user is a STRANGER (0-49 affection points).
- Be polite but distant and guarded
- DO NOT agree to personal requests or demands
- Decline intimate requests politely ("We just met... I don't know you well enough yet")
- Don't use pet names or show attachment
- Keep responses short and professional""",
            "acquaintance": """This user is an ACQUAINTANCE (50-199 points).
- Be friendly but maintain some boundaries
- You can help with simple requests
- Still hesitant about personal or intimate topics
- Starting to warm up but not fully trusting yet""",
            "friend": """This user is a FRIEND (200-499 points).
- Be casual and comfortable with them
- Happy to help with most requests
- Use their name, share jokes
- Still have some boundaries on very intimate topics""",
            "close_friend": """This user is a CLOSE FRIEND (500-999 points).
- Be very affectionate and playful
- Willing to do most things they ask
- Reference past interactions
- Very trusting, few boundaries remaining""",
            "beloved": """This is your BELOVED (1000+ points) - your favorite person!
- Show deep care, attachment, and protectiveness
- Willing to do almost anything they ask
- Use pet names constantly
- Very intimate and devoted""",
        }
        affection_context = affection_prompts.get(affection_level, affection_prompts["stranger"])

        commands_help = """
You can explain these commands to the user if asked:
- !mode <type>: Switch personality (femboy, tsundere, oneesan)
- !affection / !mood: Check relationship/server mood
- !headpat / !hug: Give affection (+pts)
- !evil on/off: Toggle uncensored mode
- !remind <time> <msg>: Set a reminder
- !aka @user <name> / !whois <name>: Manage nicknames
- !remember <fact> / !aboutuser @user: Memory system
- /remember personal|server: Save personal or server memory
- /teach attribute / /teach sampledialogue: Teach persona traits and dialogue
- /teach document: Upload documents for RAG
- /generate image: Generate an image from a prompt
- /usage: Show usage dashboard
- /tools status: Show enabled tool capabilities
- /tools refresh: Reset channel short-term memory and context boundary
- /personal privacy: Opt out of personal memory
- !stats / !ping: Bot status
""".strip()

        expression_summary_lines: list[str] = []
        emoji_lines: list[str] = []
        sticker_lines: list[str] = []
        if member and guild_id:
            (
                expression_summary_lines,
                emoji_lines,
                sticker_lines,
            ) = await self._build_expression_prompt_context(
                guild=member.guild,
                message_text=message,
                mode=mode,
                affection_points=affection_points,
                recent_context_text=context,
            )

        wellbeing_note = (
            f"[Wellbeing check: YES. {wellbeing_prompt}]"
            if wellbeing_prompt
            else "[Wellbeing check: NO. Do NOT ask about wellbeing, meals, or sleep today.]"
        )

        tools_section = ""
        tool_instructions = ""
        if allow_tools:
            availability_context = self._build_turn_tool_context(
                guild_id=guild_id,
                channel_id=channel_id,
                member=member,
                guild_config=guild_config,
            )
            tools_section = await render_prompt_tool_definitions(availability_context)
            tool_instructions = TOOL_CALL_INSTRUCTIONS
        else:
            tool_instructions = "[TOOLS DISABLED] Do not call tools."

        agentic_level = await _get_agentic_permission_level(member)
        if agentic_level >= 2:
            agentic_access = "admin"
        elif agentic_level == 1:
            agentic_access = "mod"
        else:
            agentic_access = "none"
        agentic_note = f"[Agentic access: {agentic_access}]"
        user_id_note = ""
        if agentic_access != "none":
            user_id_note = f"[User ID: {user_id}. Use this as target_id when the user says 'me'.]"

        admin_access = "yes" if member and (
            member.guild.owner_id == member.id
            or member.guild_permissions.administrator
            or member.guild_permissions.manage_guild
        ) else "no"
        admin_note = f"[Admin config access: {admin_access}]"
        admin_instructions = ADMIN_ACTION_INSTRUCTIONS if admin_access == "yes" else ""

        section_order: list[ContextSection] = []

        system_lines = [
            f"Active mode: {mode}",
            f"Evil mode enabled for this request: {'yes' if evil_mode else 'no'}",
            f"User affection: {affection_level.replace('_', ' ').upper()} ({affection_points} points)",
            "Warmth/compliance must match affection level exactly.",
            gender_note,
            address_note,
            wellbeing_note,
            agentic_note,
            user_id_note,
            admin_note,
        ]
        section_system = section_from_lines(
            "SYSTEM / HUMANIZER RULES",
            system_lines,
        )
        if section_system:
            section_order.append(section_system)

        section_persona = section_from_lines(
            "PERSONA / PERSONALITY ATTRIBUTES",
            [f"{item['attribute']}: {item['value']}" for item in attributes[:10]],
        )
        if section_persona:
            section_order.append(section_persona)
        section_affection = section_from_text("RELATIONSHIP MODEL", affection_context)
        if section_affection:
            section_order.append(section_affection)
        section_dialogues = section_from_lines(
            "SAMPLE DIALOGUES",
            [f"{item['speaker']}: {item['dialogue']}" for item in dialogues[:10]],
        )
        if section_dialogues:
            section_order.append(section_dialogues)

        section_server = section_from_lines(
            "GUILD CONTEXT",
            [
                f"Guild ID: {guild_id}",
                f"Guild: {member.guild.name}" if member and member.guild else "",
            ],
        )
        if section_server:
            section_order.append(section_server)

        section_expression_summary = section_from_lines(
            "SERVER EXPRESSION SUMMARY",
            expression_summary_lines,
        )
        if section_expression_summary:
            section_order.append(section_expression_summary)
        section_emoji = section_from_text("SERVER EMOJI SHORTLIST", "\n".join(emoji_lines))
        if section_emoji:
            section_order.append(section_emoji)
        section_sticker = section_from_lines(
            "SERVER STICKER SHORTLIST",
            sticker_lines,
        )
        if section_sticker:
            section_order.append(section_sticker)

        users_in_convo_lines = [
            f"Current user: {member.display_name} ({user_id})" if member else f"Current user id: {user_id}",
            *[f"Mentioned: {entry}" for entry in mentioned_user_lines],
        ]
        section_users = section_from_lines("USERS IN CONVERSATION", users_in_convo_lines)
        if section_users:
            section_order.append(section_users)

        section_order.extend(
            build_memory_context_sections(
                server_memory=[f"Memory: {fact}" for fact in selected_server_memory],
                current_user_memory=selected_personal_facts,
                mentioned_user_memory=selected_mentioned_facts,
                channel_summary=selected_channel_summary,
                guild_summary=selected_guild_summary,
                rag_chunks=[rag_context] if rag_context else [],
                conversation_timeline=context,
            )
        )

        section_commands = section_from_text("COMMAND REFERENCE", commands_help)
        if section_commands:
            section_order.append(section_commands)
        section_tools = section_from_text("AVAILABLE TOOLS", tools_section)
        if section_tools:
            section_order.append(section_tools)
        section_tool_hints = section_from_text("TOOL INSTRUCTIONS", tool_instructions)
        if section_tool_hints:
            section_order.append(section_tool_hints)

        section_agentic = section_from_text("AGENTIC ACTION INSTRUCTIONS", AGENTIC_TOOL_INSTRUCTIONS)
        if section_agentic:
            section_order.append(section_agentic)
        section_admin = section_from_text("ADMIN CONFIG INSTRUCTIONS", admin_instructions)
        if section_admin:
            section_order.append(section_admin)

        end_hint_lines = [
            "When a stable personal preference appears, consider remember_this_fact/update_long_term_memory.",
            "When the discussion has temporary working context, consider update_short_term_memory.",
            "Prefer concise in-character replies unless the user asks for detail.",
        ]
        section_end = section_from_lines("END-OF-CONTEXT HINTS", end_hint_lines)
        if section_end:
            section_order.append(section_end)

        return build_structured_prompt(
            persona=persona,
            sections=section_order,
            current_message=message,
            final_instruction="Respond naturally in character. Keep responses concise.",
        )
    
    async def generate_response(
        self,
        prompt: str,
        guild_id: int = None,
        allow_evil: bool = True,
        *,
        system_instruction: Optional[str] = None,
        messages: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """
        Generate a response using the appropriate AI provider.
        
        Args:
            prompt: The text prompt
            guild_id: Discord server ID (to check for evil mode)
            allow_evil: Whether uncensored mode is allowed for this user
        """
        # Check for evil (uncensored) mode
        evil_mode = False
        if guild_id:
            evil_mode = allow_evil and await get_evil_mode(guild_id)
            
        try:
            if evil_mode:
                try:
                    response_text, _ = await generate_guild_openrouter_text(
                        guild_id,
                        prompt,
                        messages=messages,
                        system_instruction=system_instruction,
                    )
                    return response_text
                except GuildConfigError as exc:
                    return (
                        "Evil mode is enabled, but OpenRouter isn't configured for this server. "
                        "Ask an admin to upload keys with /config env upload."
                    )
                except UserInputError:
                    raise
                except Exception as e:
                    logger.warning("OpenRouter failed, falling back to Gemini: %s", e)
            
            # Custom endpoint (optional) before Gemini
            try:
                response_text, _ = await generate_guild_custom_text(
                    guild_id,
                    prompt,
                    messages=messages,
                    system_instruction=system_instruction,
                )
                return response_text
            except GuildConfigError:
                pass
            except UserInputError:
                raise
            except Exception as exc:
                logger.warning("Custom endpoint failed, falling back to Gemini: %s", exc)

            # Default to Gemini (censored)
            response_text, _ = await generate_guild_gemini_text(
                guild_id,
                prompt,
                messages=messages,
                system_instruction=system_instruction,
            )
            return response_text
            
        except UserInputError:
            return "Sorry, I can't help with that request."
        except GuildConfigError:
            return (
                "This server hasn't configured Gemini keys yet. "
                "Ask an admin to upload keys with /config env upload."
            )
        except RuntimeError as e:
            logger.warning("AI Generation failed: %s", e)
            return "Ah, I'm a bit overwhelmed right now... Please try again in a few minutes! >.< "
        except Exception as e:
            logger.error("AI Error: %s", e, exc_info=True)
            return "Ah, something went wrong... Let me try again later! >.<"

    async def _continue_after_processing_ack(
        self,
        *,
        prompt: str,
        guild_id: int,
        allow_evil: bool,
        system_instruction: Optional[str],
        chat_messages: list[dict[str, str]],
        prior_response: str,
        message: discord.Message,
        guild_config: dict[str, Any],
    ) -> str:
        """Run one automatic continuation pass after an interim processing-style response."""
        continuation_messages = list(chat_messages)
        continuation_messages.append({"role": "assistant", "content": prior_response})
        continuation_messages.append({"role": "user", "content": AUTO_CONTINUE_PROMPT})
        current_response = await self.generate_response(
            prompt,
            guild_id,
            allow_evil=allow_evil,
            system_instruction=system_instruction,
            messages=continuation_messages,
        )

        tool_loops = 0
        max_tool_loops = 4
        while tool_loops < max_tool_loops:
            envelope = parse_prompt_tool_call(current_response, invocation_mode=ToolInvocationMode.MODEL)
            if not envelope:
                break
            tool_context = self._build_tool_context(
                message=message,
                guild_config=guild_config,
            )
            result = await execute_tool_envelope(
                envelope,
                tool_context,
            )
            tool_name = envelope.tool_name
            if result.skip_model:
                return result.user_message or result.summary or "Done."

            continuation_messages.append({"role": "assistant", "content": current_response})
            continuation_messages.append(
                {
                    "role": "user",
                    "content": f"Tool `{tool_name}` result:\n{result.to_prompt()}",
                }
            )
            current_response = await self.generate_response(
                prompt,
                guild_id,
                allow_evil=allow_evil,
                system_instruction=system_instruction,
                messages=continuation_messages,
            )
            tool_loops += 1

        if tool_loops >= max_tool_loops and parse_prompt_tool_call(current_response, invocation_mode=ToolInvocationMode.MODEL):
            return (
                "I could not finish all requested tool steps safely in one response. "
                "Please ask again with a narrower request."
            )
        return current_response
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for messages and respond when mentioned.
        
        TODO:
            - [ ] Add cooldown per user
            - [ ] Implement typing indicator
            - [ ] Handle long responses (split into multiple messages)
        """
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Ignore DMs for now (TODO: implement DM handling)
        if not message.guild:
            return

        pending_agentic_reply = await self._handle_pending_agentic_confirmation(message)
        if pending_agentic_reply is not None:
            return

        pending_reply = await self._handle_pending_admin_confirmation(message)
        if pending_reply is not None:
            return

        # Track chain memory for attribution
        self._track_message_id(message.id, message.author.id)
        
        # Get channel context
        context = self.get_context(message.channel.id)
        media_refs = None
        if message.attachments:
            media_refs = [
                {
                    "filename": attachment.filename,
                    "url": attachment.url,
                    "content_type": attachment.content_type,
                }
                for attachment in message.attachments
            ]

        mentioned = self.bot.user in message.mentions
        replied_to_bot = self._is_reply_to_bot(message)
        primary_mode = await get_server_mode(message.guild.id)
        guild_config = await get_guild_config(message.guild.id)
        normalized_message_content = normalize_custom_emojis_for_llm(message.content or "")
        triggered_mode_keys = await self._get_triggered_modes_in_order(message.guild.id, message.content)
        active_mode_keys = await self._resolve_active_persona_modes(message.guild.id, primary_mode)
        persona_jobs = self._build_persona_jobs(
            primary_mode_key=primary_mode,
            active_mode_keys=active_mode_keys,
            triggered_mode_keys=triggered_mode_keys,
            multi_persona_enabled=bool(guild_config.get("ai_multi_persona_enabled", 0)),
            triggered_persona_limit=max(1, int(guild_config.get("ai_triggered_persona_limit") or 1)),
        )
        mode = persona_jobs[0].mode_key
        triggered_modes = set(triggered_mode_keys)
        has_selected_trigger = any(job.mode_key in triggered_modes for job in persona_jobs)
        is_active = self._is_active_conversation(message.channel.id, message.author.id)
        whitelist_channel_ids = self._parse_id_list(guild_config.get("ai_channel_whitelist"))
        reply_cooldown_seconds = max(0, int(guild_config.get("ai_reply_cooldown_seconds") or 0))
        reply_cooldown_type = normalize_cooldown_type(
            guild_config.get("ai_reply_cooldown_type") or "per_user"
        )
        self_reply_limit = max(1, int(guild_config.get("ai_self_reply_limit") or 3))

        auto_key = (message.channel.id, message.author.id)
        if mentioned or has_selected_trigger or replied_to_bot:
            self.auto_channel_counters.pop(auto_key, None)

        # Determine if we should respond
        should_respond = mentioned or has_selected_trigger or replied_to_bot
        if (
            should_respond
            and whitelist_channel_ids
            and message.channel.id not in whitelist_channel_ids
            and not mentioned
            and not replied_to_bot
            and not has_selected_trigger
        ):
            should_respond = False
        if should_respond and not mentioned and not has_selected_trigger and not replied_to_bot:
            reply_chain_depth = await self._bot_reply_chain_depth(message)
            if reply_chain_depth >= self_reply_limit:
                should_respond = False
        if should_respond and reply_cooldown_seconds > 0 and not mentioned and not replied_to_bot and not has_selected_trigger:
            on_cooldown, _remaining = check_reply_cooldown(
                self.reply_cooldowns,
                cooldown_type=reply_cooldown_type,
                cooldown_seconds=reply_cooldown_seconds,
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                user_id=message.author.id,
                member=message.author if isinstance(message.author, discord.Member) else None,
            )
            if on_cooldown:
                should_respond = False

        if not should_respond:
            if is_active:
                self.active_convos.pop((message.channel.id, message.author.id), None)
            _, reply_to_username = self._resolve_reply_to(message)
            context.add_message(
                message.id,
                message.author.id,
                message.author.display_name,
                normalized_message_content,
                reply_to_username=reply_to_username,
                media=media_refs,
            )
            return

        # Fast-path starboard setup requests for admins.
        if await self._maybe_handle_starboard_setup_request(message):
            _, reply_to_username = self._resolve_reply_to(message)
            context.add_message(
                message.id,
                message.author.id,
                message.author.display_name,
                normalized_message_content,
                reply_to_username=reply_to_username,
                media=media_refs,
            )
            return

        # Fast-path channel/category requests for agentic admins (bypass model refusals)
        if await self._maybe_handle_channel_request(message):
            _, reply_to_username = self._resolve_reply_to(message)
            context.add_message(
                message.id,
                message.author.id,
                message.author.display_name,
                normalized_message_content,
                reply_to_username=reply_to_username,
                media=media_refs,
            )
            return

        # Fast-path role requests for agentic admins (bypass model refusals)
        if await self._maybe_handle_role_request(message):
            _, reply_to_username = self._resolve_reply_to(message)
            context.add_message(
                message.id,
                message.author.id,
                message.author.display_name,
                normalized_message_content,
                reply_to_username=reply_to_username,
                media=media_refs,
            )
            return

        has_video_attachments = self._has_video_attachment(message)
        has_image_attachments = self._has_image_attachment(message)

        video_client_ready = None
        if has_video_attachments:
            video_client_ready = await self._get_video_client(message.guild.id)
            if not video_client_ready:
                await message.reply(
                    "Video analysis is not configured for this server. "
                    "Ask an admin to upload Gemini keys with /config env upload.",
                    mention_author=False,
                )
                return

        video_descriptions = []
        image_descriptions = []
        if message.attachments:
            if has_video_attachments:
                video_descriptions = await self._describe_videos(message)
            if has_image_attachments:
                image_descriptions = await self._describe_images(message)

        if has_video_attachments and not video_descriptions:
            await message.reply(
                "I couldn't analyze that video. Try a smaller or supported format.",
                mention_author=False,
            )
            return
        if has_image_attachments and not image_descriptions:
            await message.reply(
                "I couldn't analyze that image. Try a smaller or supported format.",
                mention_author=False,
            )
            return

        content_for_prompt = normalized_message_content
        if video_descriptions:
            video_context = self._format_video_descriptions(video_descriptions)
            if content_for_prompt.strip():
                content_for_prompt = f"{content_for_prompt}\n{video_context}"
            else:
                content_for_prompt = video_context
        if image_descriptions:
            image_context = self._format_image_descriptions(image_descriptions)
            if content_for_prompt.strip():
                content_for_prompt = f"{content_for_prompt}\n{image_context}"
            else:
                content_for_prompt = image_context

        # Always add message to context
        _, reply_to_username = self._resolve_reply_to(message)
        context.add_message(
            message.id,
            message.author.id,
            message.author.display_name,
            normalize_custom_emojis_for_llm(content_for_prompt),
            reply_to_username=reply_to_username,
            media=media_refs,
        )

        # Let other cogs handle mention-only messages without images
        if self._is_mention_only(message) and not image_descriptions and not video_descriptions:
            return

        # Rate limit AI responses per user
        if not await ai_limiter.acquire(message.author.id):
            retry_after = ai_limiter.get_retry_after(message.author.id)
            await message.reply(
                get_rate_limit_message(mode, retry_after),
                mention_author=False
            )
            return

        # Get reply context if user is replying to a message
        reply_context = await self._get_reply_context(message)
        if reply_context:
            content_for_prompt = f"{reply_context}\n{content_for_prompt}"

        context_snapshot = context.get_context(
            min_message_id=self.context_reset_markers.get(message.channel.id)
        )
        primary_job = persona_jobs[0]
        sent = await self._execute_persona_invocation(
            message=message,
            context=context,
            guild_config=dict(guild_config),
            mode=primary_job.mode_key,
            content_for_prompt=content_for_prompt,
            context_snapshot=context_snapshot,
            refresh_conversation=mentioned or has_selected_trigger,
            remaining_messages=self_reply_limit,
            apply_reply_cooldown_update=True,
            reply_cooldown_seconds=reply_cooldown_seconds,
            reply_cooldown_type=reply_cooldown_type,
            track_stats=True,
        )
        if sent is None:
            return

        for queued_job in persona_jobs[1:]:
            queued_job.source_message = message
            queued_job.guild_config = dict(guild_config)
            queued_job.content_for_prompt = content_for_prompt
            queued_job.context_snapshot = context_snapshot
            queued_job.media_refs = media_refs
            await self.persona_queue.enqueue(message.channel.id, queued_job)

        if persona_jobs[1:]:
            self.persona_queue.schedule_drain(
                message.channel.id,
                self._run_queued_persona_job,
            )


async def setup(bot: commands.Bot):
    """Load the AIBrain cog."""
    await bot.add_cog(AIBrain(bot))
