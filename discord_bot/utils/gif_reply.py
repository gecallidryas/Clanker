from __future__ import annotations

import os
import re
from typing import Any, Optional

import aiohttp
import discord

from utils.db_handler import get_guild_config
from utils.encryption import get_encryption
from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

logger = get_logger(__name__)

TENOR_SEARCH_URL = "https://tenor.googleapis.com/v2/search"
DEFAULT_CLIENT_KEY = "femboibot"
DEFAULT_LIMIT = 1

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "to", "of", "in", "on", "for",
    "with", "at", "by", "from", "up", "down", "out", "over", "under", "as", "is", "are", "was",
    "were", "be", "been", "being", "it", "this", "that", "these", "those", "i", "you", "we",
    "they", "he", "she", "them", "us", "my", "your", "our", "their", "me", "him", "her",
}

EMOTION_CUES = {
    "lol", "lmao", "haha", "funny", "hilarious", "rofl", "omg", "wow", "yay", "nice",
    "congrats", "congratulations", "sad", "sorry", "angry", "mad", "upset", "frustrated",
    "excited", "happy", "glad", "love", "aww", "cute", "tired", "bored", "confused",
}

REACTION_KEYWORDS = {
    "laugh", "laughing", "lol", "lmao", "haha", "funny",
    "sad", "cry", "crying", "angry", "mad", "upset",
    "surprised", "wow", "excited", "happy", "yay",
    "facepalm", "shrug", "confused", "celebrate", "congrats",
    "cheer", "clap", "applause", "thumbs up", "thumbsup",
    "hug", "pat", "headpat", "aww", "cute",
}


async def _get_tenor_keys(guild_id: int) -> tuple[Optional[str], Optional[str]]:
    api_key = os.getenv("TENOR_API_KEY")
    client_key = os.getenv("TENOR_CLIENT_KEY")
    if api_key:
        return api_key, client_key

    config = await get_guild_config(guild_id)
    encrypted_api = config.get("tenor_api_key")
    encrypted_client = config.get("tenor_client_key")
    encryption = get_encryption()

    if encrypted_api:
        try:
            api_key = encryption.decrypt(encrypted_api)
        except Exception:
            api_key = None

    if encrypted_client:
        try:
            client_key = encryption.decrypt(encrypted_client)
        except Exception:
            client_key = None

    return api_key, client_key


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    tokens = [t for t in cleaned.split() if t and t not in STOPWORDS]
    return tokens


def _is_relevant_to_text(query: str, context_text: str) -> bool:
    query = (query or "").strip()
    if not query:
        return False
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return False
    context_tokens = set(_tokenize(context_text))
    if context_tokens & query_tokens:
        return True
    if query.lower() in REACTION_KEYWORDS and (context_tokens & EMOTION_CUES):
        return True
    return False


def _is_relevant_query(context: ToolContext, query: str, caption: str) -> bool:
    message_text = ""
    if context and context.message:
        message_text = context.message.content or ""
        if context.message.reference and isinstance(context.message.reference.resolved, discord.Message):
            message_text = f"{message_text}\n{context.message.reference.resolved.content or ''}"
    combined = f"{message_text}\n{caption or ''}".strip()
    return _is_relevant_to_text(query, combined)


def _pick_media_url(result: dict[str, Any]) -> Optional[str]:
    media = result.get("media_formats") or {}
    for key in ("gif", "mediumgif", "tinygif", "mp4", "nanomp4"):
        entry = media.get(key) or {}
        url = entry.get("url")
        if url:
            return str(url)
    return None


async def _search_tenor(query: str, api_key: str, client_key: Optional[str], limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    params = {
        "q": query,
        "key": api_key,
        "limit": max(1, min(limit, 8)),
        "media_filter": "gif",
    }
    if client_key:
        params["client_key"] = client_key
    results: list[dict[str, Any]] = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TENOR_SEARCH_URL, params=params, timeout=15) as resp:
                if resp.status >= 400:
                    logger.warning("Tenor search failed: %s", resp.status)
                    return []
                data = await resp.json()
        for item in data.get("results", [])[: params["limit"]]:
            url = _pick_media_url(item)
            if not url:
                continue
            results.append({"url": url, "title": item.get("content_description") or ""})
    except Exception as exc:
        logger.warning("Tenor search failed: %s", exc)
        return []
    return results


async def _handle_send_gif(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = (args.get("query") or "").strip()
    caption = (args.get("caption") or "").strip()
    if not query:
        return ToolResult(ok=False, summary="Missing gif query.")
    if not _is_relevant_query(context, query, caption):
        return ToolResult(ok=False, summary="GIF query not relevant to the current message.")

    api_key, client_key = await _get_tenor_keys(context.guild.id)
    if not api_key:
        return ToolResult(ok=False, summary="Tenor API key not configured.")

    results = await _search_tenor(query, api_key, client_key or DEFAULT_CLIENT_KEY, limit=1)
    if not results:
        return ToolResult(ok=False, summary="No gif results found.")

    gif_url = results[0]["url"]
    message = gif_url if not caption else f"{caption}\n{gif_url}"
    return ToolResult(
        ok=True,
        summary="GIF ready.",
        data={"url": gif_url, "provider": "tenor"},
        user_message=message,
        skip_model=True,
    )


tool_send_gif = ToolDefinition(
    name="send_gif",
    description="Search Tenor and send a GIF. Query must be directly relevant to the user's message.",
    args_schema={"query": "search keywords", "caption": "optional message"},
    handler=_handle_send_gif,
)
