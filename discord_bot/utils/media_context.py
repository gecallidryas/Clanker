from __future__ import annotations

from typing import Any, Optional

import discord

from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

SUPPORTED_IMAGE_FORMATS = {"image/png", "image/jpeg", "image/gif", "image/webp"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mpeg", ".mpg", ".ogv", ".mkv"}


def _is_supported_image(attachment: discord.Attachment) -> bool:
    return attachment.content_type in SUPPORTED_IMAGE_FORMATS


def _is_supported_video(attachment: discord.Attachment) -> bool:
    if attachment.content_type and attachment.content_type.startswith("video/"):
        return True
    name = (attachment.filename or "").lower()
    return any(name.endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS)


async def collect_recent_media(
    channel: discord.TextChannel,
    before_message_id: Optional[int] = None,
    limit_messages: int = 40,
    max_items: int = 6,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    before = discord.Object(id=before_message_id) if before_message_id else None

    async for message in channel.history(limit=limit_messages, before=before):
        for attachment in message.attachments:
            if not (_is_supported_image(attachment) or _is_supported_video(attachment)):
                continue
            results.append(
                {
                    "message_id": message.id,
                    "author": message.author.display_name,
                    "filename": attachment.filename,
                    "url": attachment.url,
                    "content_type": attachment.content_type,
                }
            )
            if len(results) >= max_items:
                return results
    return results


async def _handle_increase_media_context(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    channel_id = args.get("channel_id")
    before_message_id = args.get("before_message_id") or (context.message.id if context.message else None)
    limit_messages = int(args.get("limit_messages") or 40)
    max_items = int(args.get("max_items") or 6)

    channel = context.channel
    if channel_id:
        channel = context.guild.get_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        return ToolResult(ok=False, summary="Channel not found.")

    media = await collect_recent_media(
        channel,
        before_message_id=before_message_id,
        limit_messages=max(5, min(limit_messages, 200)),
        max_items=max(1, min(max_items, 20)),
    )
    summary = f"Found {len(media)} recent media attachment(s)."
    return ToolResult(ok=True, summary=summary, data={"media": media})


tool_increase_media_context = ToolDefinition(
    name="increase_media_context",
    description="Fetch recent media attachments from chat history.",
    args_schema={
        "channel_id": "optional channel id",
        "before_message_id": "optional message id to look before",
        "limit_messages": "max messages to scan (optional)",
        "max_items": "max attachments to return (optional)",
    },
    handler=_handle_increase_media_context,
)
