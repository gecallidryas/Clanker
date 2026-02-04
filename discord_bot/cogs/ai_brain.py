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
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional
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
    get_facts,
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
)
from utils.api_manager import UserInputError
from utils.app_emojis import (
    clean_emoji_name,
    filter_emojis_by_prefix,
    format_custom_emoji,
    get_application_emojis,
    get_guild_emojis,
    replace_custom_emojis,
    FEMMY_EMOJI_PREFIX,
    YUMI_EMOJI_PREFIX,
)
from utils.guild_ai import (
    generate_guild_gemini_text,
    generate_guild_gemini_vision,
    generate_guild_openrouter_text,
    generate_guild_custom_text,
    get_guild_gemini_keys,
    get_guild_gemini_model,
    GuildConfigError,
)
from utils.admin_actions import execute_admin_action
from modes import get_mode_profile, get_all_modes
from utils.rate_limiter import ai_limiter, get_rate_limit_message
from utils.logger import get_logger
from utils.tool_registry import (
    register_builtin_tools,
    execute_tool,
    get_available_tools,
    render_tool_definitions,
)
from utils.tool_parser import extract_tool_call, strip_tool_call
from utils.tool_context import ToolContext
from utils.rag_store import get_rag_context
from utils.text_splitter import split_message

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


AGENTIC_JSON_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
ADMIN_ACTION_PATTERN = re.compile(r"```admin_action\s*(\{.*?\})\s*```", re.DOTALL)
ADMIN_CONFIRM_TOKENS = {"confirm", "yes", "y", "ok", "okay"}
ADMIN_CANCEL_TOKENS = {"cancel", "stop", "never mind", "nevermind"}
ADMIN_PENDING_TTL_SECONDS = 180

AGENTIC_TOOL_INSTRUCTIONS = """
[AGENTIC TOOL USE]
You can manage roles and moderate users only when the user has agentic permission.
If the user has permission and asks for a role or moderation action, respond ONLY with a JSON code block in this schema:

```json
{
  "action": "manage_role" | "moderate_user",
  "sub_action": "create" | "give" | "remove" | "ban" | "kick" | "timeout" | "mute",
  "target_name": "Role name (if applicable)",
  "target_id": "USER_ID_NUMERIC",
  "duration": "Timeout duration in minutes (if timeout/mute)",
  "reason": "Reason for action",
  "reply": "Conversational confirmation for the user"
}
```

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


def _find_agentic_json_block(response_text: str) -> Optional[str]:
    match = AGENTIC_JSON_PATTERN.search(response_text or "")
    return match.group(1) if match else None


def _find_admin_action_block(response_text: str) -> Optional[str]:
    match = ADMIN_ACTION_PATTERN.search(response_text or "")
    return match.group(1) if match else None


def _strip_admin_action_block(response_text: str) -> str:
    if not response_text:
        return ""
    return ADMIN_ACTION_PATTERN.sub("", response_text).strip()


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
    if action in {"ban", "create", "give", "remove"}:
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


async def handle_agentic_actions(
    message: discord.Message,
    ai_response_text: str,
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
    if action not in {"manage_role", "moderate_user"}:
        return None
    if sub_action not in {"create", "give", "remove", "ban", "kick", "timeout", "mute"}:
        return None

    if not message.guild or not isinstance(message.author, discord.Member):
        return await message.reply("Sorry, I can only do that in a server.", mention_author=False)

    required_level = _agentic_action_requires_level(sub_action)
    permission_level = await _get_agentic_permission_level(message.author)

    if permission_level < required_level:
        return await message.reply("Nice try, but you don't have permission to do that.", mention_author=False)

    target_id = data.get("target_id")
    try:
        target_id_int = int(target_id)
    except (TypeError, ValueError):
        return await message.reply("I couldn't identify the target user.", mention_author=False)

    role_name = (data.get("target_name") or "").strip()
    reason = (data.get("reason") or "No reason provided").strip()
    reply_text = (data.get("reply") or "Done.").strip()

    guild = message.guild
    target_member = await _resolve_member(guild, target_id_int)

    try:
        if data.get("action") == "manage_role":
            if not role_name:
                return await message.reply("Please specify a role name.", mention_author=False)

            role = discord.utils.get(guild.roles, name=role_name)
            if sub_action in {"create", "give"}:
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
                if not role:
                    return await message.reply(f"I couldn't find the role '{role_name}'.", mention_author=False)
                if not target_member:
                    return await message.reply("I couldn't find that member.", mention_author=False)
                await target_member.remove_roles(role, reason=reason)
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
            if sub_action == "ban":
                await guild.ban(discord.Object(id=target_id_int), reason=reason)
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

    result = await execute_admin_action(action, params, message.guild, message.author, bot=brain.bot)

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
    
    def get_context(self) -> str:
        """
        Get formatted context string for AI prompt.
        Only includes messages from the last 30 minutes.
        """
        cutoff = datetime.now() - timedelta(minutes=self.expiry_minutes)
        
        valid_messages = [
            msg for msg in self.messages
            if msg["timestamp"] > cutoff
        ]
        
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
        register_builtin_tools()
        self.contexts: Dict[int, ConversationContext] = {}  # channel_id -> context
        self.chain_memory: Dict[int, int] = {}  # message_id -> user_id
        self.chain_order: deque[int] = deque()
        self.chain_limit = CHAIN_MEMORY_LIMIT
        self._video_clients: Dict[str, tuple] = {}
        self.pending_admin_actions: Dict[tuple[int, int], Dict[str, Any]] = {}
        # Active conversations: (channel_id, user_id) -> {"remaining": int, "last_active": datetime}
        self.active_convos: Dict[tuple[int, int], dict] = {}
    
    def get_context(self, channel_id: int) -> ConversationContext:
        """Get or create context for a channel."""
        if channel_id not in self.contexts:
            self.contexts[channel_id] = ConversationContext()
        return self.contexts[channel_id]

    async def _send_in_chunks(self, message: discord.Message, text: str) -> discord.Message:
        parts = split_message(text)
        if not parts:
            return await message.reply("...", mention_author=False)
        first = await message.reply(parts[0], mention_author=False)
        for part in parts[1:]:
            await message.channel.send(part)
        return first

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

    def _refresh_conversation(self, channel_id: int, user_id: int):
        """Refresh conversation (user re-triggered or mentioned)."""
        key = (channel_id, user_id)
        self.active_convos[key] = {
            "remaining": ACTIVE_CONVO_MESSAGES,
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

        follow_up = await execute_admin_action(action, params, message.guild, message.author, bot=self.bot)
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

    def _get_triggered_modes(self, content: str) -> set[str]:
        triggered: set[str] = set()
        for profile in get_all_modes():
            if self._has_any_trigger(content, profile.triggers):
                triggered.add(profile.key)
        return triggered

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
    
    async def _get_app_emojis(self, mode: str, guild: Optional[discord.Guild], limit: int = 50) -> str:
        """Get a formatted list of guild emojis for AI use."""
        emojis = await get_guild_emojis(self.bot, guild)
        if not emojis:
            return ""

        if mode == "mode_femboy":
            emojis = filter_emojis_by_prefix(emojis, FEMMY_EMOJI_PREFIX)
        elif mode == "mode_oneesan":
            emojis = filter_emojis_by_prefix(emojis, YUMI_EMOJI_PREFIX)

        if not emojis:
            return ""

        lines = []
        for emoji in emojis[:limit]:
            token = format_custom_emoji(emoji)
            if not token:
                continue
            display_name = clean_emoji_name(getattr(emoji, "name", ""))
            lines.append(f"{token} ({display_name})")

        return "\n".join(lines)
    
    async def build_prompt(
        self,
        guild_id: int, 
        user_id: int, 
        message: str, 
        context: str,
        member: Optional[discord.Member] = None,
        wellbeing_prompt: str = "",
        affection_data: Optional[Dict[str, int]] = None,
        allow_evil: bool = True,
        allow_tools: bool = True,
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
        # Get current persona mode
        mode = await get_server_mode(guild_id)
        evil_mode = allow_evil and await get_evil_mode(guild_id)
        persona = await self._load_persona(guild_id, mode, evil_mode)
        guild_config = await get_guild_config(guild_id)
        
        # Get user facts (Current speaker)
        personal_facts = await get_facts(guild_id, user_id, ["personal"])
        short_term_facts = await get_facts(guild_id, user_id, ["short_term"])
        long_term_facts = await get_facts(guild_id, user_id, ["long_term"])

        facts_list = [f"- (User {user_id}) {fact}" for fact in personal_facts[:10]]
        if short_term_facts:
            facts_list.extend([f"- (Short-term) {fact}" for fact in short_term_facts[:5]])
        if long_term_facts:
            facts_list.extend([f"- (Long-term) {fact}" for fact in long_term_facts[:5]])

        # Check for mentions in the message and fetch their facts
        mentioned_ids = set(re.findall(r"<@!?(\d+)>", message))
        for mentioned_id in mentioned_ids:
            uid = int(mentioned_id)
            # Skip if it's the bot itself or the current speaker (already fetched)
            if uid == self.bot.user.id or uid == user_id:
                continue
            
            other_facts = await get_facts(guild_id, uid, ["personal"])
            if other_facts:
                # Try to resolve username for better context
                user = self.bot.get_user(uid)
                name = user.display_name if user else f"User {uid}"
                facts_list.extend([f"- ({name}) {fact}" for fact in other_facts[:5]])

        facts_section = ""
        if facts_list:
            facts_section = f"\n\nThings you know about the users:\n" + "\n".join(facts_list)

        server_memory_section = ""
        server_memory = await get_server_memory(guild_id)
        if server_memory:
            server_memory_section = "\n\nServer memory:\n" + "\n".join(
                f"- {fact}" for fact in server_memory[:10]
            )

        attributes_section = ""
        attributes = await get_persona_attributes(guild_id)
        if attributes:
            lines = [f"- {item['attribute']}: {item['value']}" for item in attributes[:10]]
            attributes_section = "\n\nPersona attributes:\n" + "\n".join(lines)

        dialogue_section = ""
        dialogues = await get_sample_dialogues(guild_id)
        if dialogues:
            lines = [f"- {item['speaker']}: {item['dialogue']}" for item in dialogues[:10]]
            dialogue_section = "\n\nSample dialogues:\n" + "\n".join(lines)

        rag_section = ""
        try:
            rag_enabled = bool(guild_config.get("rag_enabled") or 0)
            if rag_enabled and str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() in {"1", "true", "yes", "on"}:
                top_k = int(os.getenv("RAG_TOP_K", "4"))
                rag_context = await get_rag_context(guild_id, message, top_k=top_k)
                if rag_context:
                    rag_section = "\n\nDocument memory:\n" + rag_context
        except Exception as exc:
            logger.warning("RAG lookup failed: %s", exc)
        
        # Get affection level for behavior adjustment
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

        # Determine user gender from configured roles
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
        
        # Addressing preferences for Femmy
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

        # Affection prompts that gate compliance and warmth
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
- Very intimate and devoted"""
        }
        affection_context = affection_prompts.get(affection_level, affection_prompts["stranger"])

        # Command context for RAG-like help
        commands_help = """
=== AVAILABLE COMMANDS ===
You can explain these commands to the user if asked:
- !mode <type>: Switch personality (femboy, tsundere, oneesan)
- !affection / !mood: Check relationship/server mood
- !headpat / !hug: Give affection (+pts)
- !evil on/off: Toggle uncensored mode
- !remind <time> <msg>: Set a reminder
- !aka @user <name> / !whois <name>: Manage nicknames
- !remember <fact> / !aboutuser @user: Memory system
- /teach memory personal|server: Teach personal or server memory
- /teach attribute / /teach sampledialogue: Teach persona traits and dialogue
- /teach document: Upload documents for RAG
- /generate image: Generate an image from a prompt
- /usage: Show usage dashboard
- /tools status: Show enabled tool capabilities
- /personal privacy: Opt out of personal memory
- !stats / !ping: Bot status
"""

        # Get guild emojis
        emoji_section = ""
        if member and guild_id:
            emojis = await self._get_app_emojis(mode, member.guild)
            if emojis:
                emoji_section = (
                    "\n\n=== SERVER EMOJIS ===\n"
                    "You can use these server emojis naturally in your responses:\n"
                    f"{emojis}\n"
                )

        custom_emoji_section = ""
        emoji_manager = getattr(self.bot, "emoji_manager", None)
        if emoji_manager:
            custom_emojis = emoji_manager.build_prompt_section(
                mode=mode,
                affection=affection_points,
                evil_mode=evil_mode,
            )
            if custom_emojis:
                custom_emoji_section = f"\n\n{custom_emojis}"

        wellbeing_note = (
            f"[Wellbeing check: YES. {wellbeing_prompt}]"
            if wellbeing_prompt
            else "[Wellbeing check: NO. Do NOT ask about wellbeing, meals, or sleep today.]"
        )
        emoji_policy_note = (
            "[Emoji policy: If you use custom emojis, use ONLY the CUSTOM EMOJIS list and "
            "the SERVER EMOJIS list. Unicode emojis are allowed.]"
        )

        tools_section = ""
        tool_instructions = ""
        if allow_tools:
            available_tools = get_available_tools(guild_config)
            if available_tools:
                tools_section = "\n\n=== AVAILABLE TOOLS ===\n" + render_tool_definitions(available_tools)
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

        admin_access = "yes" if member and (
            member.guild_permissions.administrator or member.guild_permissions.manage_guild
        ) else "no"
        admin_note = f"[Admin config access: {admin_access}]"
        admin_instructions = ADMIN_ACTION_INSTRUCTIONS if admin_access == "yes" else ""

        # Build full prompt
        prompt = f"""
{persona}

=== RELATIONSHIP STATUS ===
User's affection level: {affection_level.replace('_', ' ').upper()} ({affection_points} points)
{affection_context}

IMPORTANT: Your warmth, compliance, and willingness to help MUST match the affection level above.
Low affection = reserved, won't agree to demands. High affection = eager to please.

{gender_note}
{address_note}
{wellbeing_note}
{agentic_note}
{admin_note}
{emoji_policy_note}

        {commands_help}{custom_emoji_section}{emoji_section}{tools_section}
        {tool_instructions}
        {AGENTIC_TOOL_INSTRUCTIONS}
        {admin_instructions}
        {facts_section}{server_memory_section}{attributes_section}{dialogue_section}{rag_section}

Recent conversation:
{context}

Current message from user:
{message}

Respond naturally in character. Keep responses concise.
"""
        return prompt
    
    async def generate_response(self, prompt: str, guild_id: int = None, allow_evil: bool = True) -> str:
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
                    response_text, _ = await generate_guild_openrouter_text(guild_id, prompt)
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
                response_text, _ = await generate_guild_custom_text(guild_id, prompt)
                return response_text
            except GuildConfigError:
                pass
            except UserInputError:
                raise
            except Exception as exc:
                logger.warning("Custom endpoint failed, falling back to Gemini: %s", exc)

            # Default to Gemini (censored)
            response_text, _ = await generate_guild_gemini_text(guild_id, prompt)
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
        mode = await get_server_mode(message.guild.id)

        triggered_modes = self._get_triggered_modes(message.content)
        has_current_trigger = mode in triggered_modes
        has_other_trigger = bool(triggered_modes - {mode})

        # Determine if we should respond
        should_respond = (mentioned or has_current_trigger) and not (has_other_trigger and not has_current_trigger)

        if not should_respond:
            _, reply_to_username = self._resolve_reply_to(message)
            context.add_message(
                message.id,
                message.author.id,
                message.author.display_name,
                message.content,
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

        content_for_prompt = message.content
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
            content_for_prompt,
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

        # Get reply context if user is replying to a message
        reply_context = await self._get_reply_context(message)
        if reply_context:
            content_for_prompt = f"{reply_context}\n{content_for_prompt}"

        # Show typing indicator
        async with message.channel.typing():
            # Build and send prompt
            context_snapshot = context.get_context()
            prompt = await self.build_prompt(
                message.guild.id,
                message.author.id,
                content_for_prompt,
                context_snapshot,
                member=message.author,
                wellbeing_prompt=wellbeing_prompt,
                affection_data=affection_data,
                allow_evil=allow_evil
            )
            
            response = await self.generate_response(
                prompt,
                message.guild.id,
                allow_evil=allow_evil
            )

        raw_response = response
        tool_call = extract_tool_call(raw_response)
        sent = None
        if tool_call:
            guild_config = await get_guild_config(message.guild.id)
            tool_context = ToolContext(
                bot=self.bot,
                guild=message.guild,
                channel=message.channel,
                user=message.author,
                message=message,
                guild_config=guild_config,
                locale="en",
            )
            result = await execute_tool(
                str(tool_call.get("tool") or "").strip(),
                tool_call.get("args") or {},
                tool_context,
            )

            if result.skip_model:
                reply_text = result.user_message or result.summary or "Done."
                sent = await self._send_in_chunks(message, reply_text)
                raw_response = ""
            else:
                tool_message = f"{content_for_prompt}\n\n{result.to_prompt()}"
                tool_prompt = await self.build_prompt(
                    message.guild.id,
                    message.author.id,
                    tool_message,
                    context_snapshot,
                    member=message.author,
                    wellbeing_prompt=wellbeing_prompt,
                    affection_data=affection_data,
                    allow_evil=allow_evil,
                    allow_tools=False,
                )
                response = await self.generate_response(
                    tool_prompt,
                    message.guild.id,
                    allow_evil=allow_evil,
                )
                raw_response = response
        if sent is None:
            sent = await handle_agentic_actions(message, raw_response)
        if sent is None:
            sent = await handle_admin_actions(self, message, raw_response)
        if sent is None:
            response = strip_tool_call(raw_response)
            evil_mode_enabled = allow_evil and await get_evil_mode(message.guild.id)

            emoji_manager = getattr(self.bot, "emoji_manager", None)
            if emoji_manager:
                response = emoji_manager.apply_trigger_emojis(
                    response_text=response,
                    user_text=message.content,
                    mode=mode,
                    affection=affection_points,
                    evil_mode=evil_mode_enabled,
                )

            if message.guild:
                try:
                    guild_emojis = await get_guild_emojis(self.bot, message.guild)
                    app_emojis = await get_application_emojis(self.bot)
                    response = replace_custom_emojis(response, guild_emojis, app_emojis)
                except Exception as exc:
                    logger.warning("Failed to normalize emojis: %s", exc)

            sent = await self._send_in_chunks(message, response)

        # Manage conversation state
        if mentioned or has_trigger:
            # Fresh trigger - activate/refresh conversation
            self._refresh_conversation(message.channel.id, message.author.id)
        elif is_active:
            # Continuing active conversation - decrement remaining
            self._continue_conversation(message.channel.id, message.author.id)

        if wellbeing_date:
            await set_last_wellbeing_date(message.guild.id, message.author.id, wellbeing_date)

        # Track bot response for chain memory and context
        self._track_message_id(sent.id, sent.author.id)
        context.add_message(
            sent.id,
            sent.author.id,
            sent.author.display_name,
            sent.content,
            reply_to_username=message.author.display_name
        )

        try:
            await increment_stat("messages_processed", guild_id=message.guild.id)
        except Exception as e:
            logger.warning("Failed to increment messages_processed: %s", e)


async def setup(bot: commands.Bot):
    """Load the AIBrain cog."""
    await bot.add_cog(AIBrain(bot))
