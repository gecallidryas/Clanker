from __future__ import annotations

from utils.streaming.chunker import split_stream_text

DISCORD_MESSAGE_LIMIT = 2000
DEFAULT_CHUNK_LIMIT = 1900


def split_message(text: str, limit: int = DEFAULT_CHUNK_LIMIT) -> list[str]:
    """Split text into Discord-sized chunks, preserving code blocks when possible."""
    return split_stream_text(text, limit=limit)
