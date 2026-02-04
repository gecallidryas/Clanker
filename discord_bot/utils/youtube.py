from __future__ import annotations

import asyncio
import re
from typing import Any, Optional

from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

logger = get_logger(__name__)


YOUTUBE_ID_PATTERNS = [
    re.compile(r"v=([\\w-]{11})"),
    re.compile(r"youtu\\.be/([\\w-]{11})"),
    re.compile(r"youtube\\.com/shorts/([\\w-]{11})"),
]


def extract_video_id(url: str) -> Optional[str]:
    if not url:
        return None
    for pattern in YOUTUBE_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def _fetch_metadata(url: str) -> dict[str, Any]:
    yt = YouTube(url)
    return {
        "title": yt.title,
        "author": yt.author,
        "length": yt.length,
        "description": yt.description,
        "publish_date": yt.publish_date.isoformat() if yt.publish_date else None,
    }


def _fetch_transcript(video_id: str) -> str:
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    lines = []
    for item in transcript:
        text = item.get("text", "").replace("\n", " ").strip()
        if text:
            lines.append(text)
    return " ".join(lines)


async def _handle_process_youtube(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    url = (args.get("youtube_url") or args.get("url") or "").strip()
    if not url:
        return ToolResult(ok=False, summary="Missing YouTube url.")

    video_id = extract_video_id(url)
    if not video_id:
        return ToolResult(ok=False, summary="Invalid YouTube url.")

    metadata: dict[str, Any] = {}
    transcript_text = None

    try:
        metadata = await asyncio.to_thread(_fetch_metadata, url)
    except Exception as exc:
        logger.warning("YouTube metadata fetch failed: %s", exc)

    try:
        transcript_text = await asyncio.to_thread(_fetch_transcript, video_id)
    except Exception as exc:
        logger.warning("YouTube transcript fetch failed: %s", exc)

    summary = f"Processed YouTube video {video_id}."
    return ToolResult(
        ok=True,
        summary=summary,
        data={"video_id": video_id, "metadata": metadata, "transcript": transcript_text},
    )


tool_process_youtube = ToolDefinition(
    name="process_youtube_video",
    description="Fetch YouTube metadata and transcript if available.",
    args_schema={"youtube_url": "YouTube URL"},
    handler=_handle_process_youtube,
)
