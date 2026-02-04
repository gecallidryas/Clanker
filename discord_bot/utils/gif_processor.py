from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Optional

import aiohttp
from PIL import Image

from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

logger = get_logger(__name__)


def _gif_enabled() -> bool:
    return str(os.getenv("GIF_ANALYSIS_ENABLED", "")).lower() in {"1", "true", "yes", "on"}


async def _download_bytes(url: str) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as resp:
                if resp.status >= 400:
                    return None
                return await resp.read()
    except Exception as exc:
        logger.warning("GIF download failed: %s", exc)
        return None


def _extract_gif_info(data: bytes) -> dict[str, Any]:
    with Image.open(BytesIO(data)) as img:
        frames = getattr(img, "n_frames", 1)
        durations = []
        for frame in range(min(frames, 10)):
            img.seek(frame)
            durations.append(img.info.get("duration", 0))
        return {"frames": frames, "sample_durations_ms": durations}


async def _handle_process_gif(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    if not _gif_enabled():
        return ToolResult(ok=False, summary="GIF processing is disabled on this bot.")
    url = (args.get("url") or "").strip()
    if not url:
        return ToolResult(ok=False, summary="Missing gif url.")
    data = await _download_bytes(url)
    if not data:
        return ToolResult(ok=False, summary="Failed to download gif.")
    try:
        info = _extract_gif_info(data)
    except Exception as exc:
        logger.warning("GIF parse failed: %s", exc)
        return ToolResult(ok=False, summary="Failed to parse gif.")
    summary = f"GIF has {info.get('frames')} frame(s)."
    return ToolResult(ok=True, summary=summary, data=info)


tool_process_gif = ToolDefinition(
    name="process_gif",
    description="Extract basic info about a GIF (dev only).",
    args_schema={"url": "gif url"},
    handler=_handle_process_gif,
)
