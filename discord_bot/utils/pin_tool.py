from __future__ import annotations

from typing import Any

import discord

from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult


async def _handle_pin_message(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    message_id = args.get("message_id")
    channel_id = args.get("channel_id")
    if not message_id:
        return ToolResult(ok=False, summary="Missing message_id.")

    channel = context.channel
    if channel_id:
        channel = context.guild.get_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        return ToolResult(ok=False, summary="Channel not found.")

    try:
        message = await channel.fetch_message(int(message_id))
    except Exception:
        return ToolResult(ok=False, summary="Message not found.")

    if isinstance(context.user, discord.Member):
        if not context.user.guild_permissions.manage_messages and not context.user.guild_permissions.administrator:
            return ToolResult(ok=False, summary="User lacks permission to pin messages.")

    bot_member = context.guild.me or context.guild.get_member(context.bot.user.id if context.bot.user else 0)
    if not bot_member or not channel.permissions_for(bot_member).manage_messages:
        return ToolResult(ok=False, summary="Bot lacks permission to pin messages.")

    try:
        await message.pin(reason=f"Requested by {context.user}")
    except discord.Forbidden:
        return ToolResult(ok=False, summary="Bot lacks permission to pin messages.")
    except discord.HTTPException:
        return ToolResult(ok=False, summary="Failed to pin message.")

    return ToolResult(ok=True, summary="Pinned the message.")


tool_pin_message = ToolDefinition(
    name="pin_message",
    description="Pin a message in the current channel.",
    args_schema={"message_id": "target message id", "channel_id": "optional channel id"},
    handler=_handle_pin_message,
    required_permission="mod",
)
