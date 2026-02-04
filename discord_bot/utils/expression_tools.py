from __future__ import annotations

from typing import Any, Optional

import discord

from utils.expression_picker import pick_emoji, pick_sticker
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult


async def _handle_select_sticker(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = (args.get("query") or "").strip()
    sticker = pick_sticker(context.guild, query if query else None)
    if not sticker:
        return ToolResult(ok=False, summary="No stickers available.")
    await context.channel.send(stickers=[sticker])
    return ToolResult(ok=True, summary=f"Sent sticker {sticker.name}.", data={"sticker": sticker.name})


async def _handle_react_with_emoji(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    message_id = args.get("message_id")
    channel_id = args.get("channel_id")
    emoji_query = (args.get("emoji") or "").strip()

    if not message_id:
        return ToolResult(ok=False, summary="Missing message_id.")

    channel: Optional[discord.abc.Messageable] = context.channel
    if channel_id:
        channel = context.guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return ToolResult(ok=False, summary="Channel not found.")

    try:
        message = await channel.fetch_message(int(message_id))
    except Exception:
        return ToolResult(ok=False, summary="Message not found.")

    emoji = None
    if emoji_query:
        emoji = discord.utils.get(context.guild.emojis, name=emoji_query)
    if not emoji:
        emoji = pick_emoji(context.guild, emoji_query if emoji_query else None)
    if not emoji:
        return ToolResult(ok=False, summary="No emoji available.")

    try:
        await message.add_reaction(emoji)
    except discord.Forbidden:
        return ToolResult(ok=False, summary="Missing permission to add reactions.")
    except discord.HTTPException:
        return ToolResult(ok=False, summary="Failed to add reaction.")

    return ToolResult(ok=True, summary=f"Reacted with {emoji}.", data={"emoji": str(emoji)})


tool_select_sticker_for_response = ToolDefinition(
    name="select_sticker_for_response",
    description="Send a sticker from the server that matches the response.",
    args_schema={"query": "optional keyword for sticker name"},
    handler=_handle_select_sticker,
)

tool_react_with_emoji = ToolDefinition(
    name="react_with_emoji",
    description="React to a message with a server emoji.",
    args_schema={"message_id": "target message id", "channel_id": "optional channel id", "emoji": "optional emoji name"},
    handler=_handle_react_with_emoji,
)
