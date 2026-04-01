from __future__ import annotations

from io import BytesIO
from typing import Any, Optional

import discord
from PIL import Image

from utils.guild_ai import generate_guild_gemini_vision, GuildConfigError
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult


async def _resolve_member(context: ToolContext, target_id: Optional[int]) -> Optional[discord.Member]:
    if target_id:
        member = context.guild.get_member(int(target_id))
        if member:
            return member
        try:
            return await context.guild.fetch_member(int(target_id))
        except Exception:
            return None
    return context.user


async def _handle_peek_profile_picture(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    target_id = args.get("user_id")
    member = await _resolve_member(context, target_id)
    if not member:
        return ToolResult(ok=False, summary="User not found.")

    try:
        avatar_bytes = await member.display_avatar.read()
    except Exception:
        return ToolResult(ok=False, summary="Failed to read avatar.")

    prompt = (
        "Describe this profile picture. "
        "Focus on visible details like colors, style, and mood. "
        "Avoid guessing personal identity."
    )
    try:
        image = Image.open(BytesIO(avatar_bytes))
        response, _ = await generate_guild_gemini_vision(context.guild.id, prompt, image)
    except GuildConfigError:
        return ToolResult(ok=False, summary="Profile analysis not configured.")
    except Exception:
        return ToolResult(ok=False, summary="Failed to analyze avatar.")

    return ToolResult(
        ok=True,
        summary="Profile picture analyzed.",
        data={"user_id": member.id, "analysis": response},
    )


tool_peek_profile_picture = ToolDefinition(
    name="peek_profile_picture",
    description="Analyze a user's profile picture.",
    args_schema={"user_id": "target user id (optional)"},
    handler=_handle_peek_profile_picture,
)
