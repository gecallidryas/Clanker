from __future__ import annotations

import asyncio
import base64
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


def _get_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        return default
    if value < minimum or value > maximum:
        return default
    return value


def _load_gif_processor_config() -> dict[str, int]:
    return {
        "max_width": _get_int_env("GIF_KEYFRAME_MAX_WIDTH", 800, 128, 4096),
        "jpeg_quality": _get_int_env("GIF_KEYFRAME_JPEG_QUALITY", 80, 20, 100),
        "max_keyframes": _get_int_env("GIF_KEYFRAME_MAX_FRAMES", 10, 1, 50),
        "frame_interval": _get_int_env("GIF_KEYFRAME_INTERVAL", 10, 1, 100),
        "timeout_ms": _get_int_env("GIF_KEYFRAME_TIMEOUT_MS", 30_000, 1000, 120_000),
    }


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


def _calculate_keyframe_indices(total_frames: int, interval: int, max_frames: int) -> list[int]:
    total = max(1, int(total_frames))
    stride = max(1, int(interval))
    cap = max(1, int(max_frames))

    if cap == 1:
        return [0]
    if total <= 1:
        return [0]
    indices = {0, total - 1}
    current = stride
    while current < total - 1:
        indices.add(current)
        current += stride
    ordered = sorted(indices)
    if len(ordered) <= cap:
        return ordered

    # Keep first/last and sample the middle while respecting max_frames exactly.
    if cap == 2:
        return [ordered[0], ordered[-1]]

    middle = ordered[1:-1]
    slots = cap - 2
    if len(middle) <= slots:
        return [ordered[0], *middle, ordered[-1]]

    picked_middle: list[int] = []
    if slots == 1:
        picked_middle = [middle[len(middle) // 2]]
    else:
        step = (len(middle) - 1) / float(slots - 1)
        for slot in range(slots):
            picked_middle.append(middle[int(round(slot * step))])

    unique_middle: list[int] = []
    seen_middle: set[int] = set()
    for value in picked_middle:
        if value in seen_middle:
            continue
        seen_middle.add(value)
        unique_middle.append(value)

    if len(unique_middle) < slots:
        for value in middle:
            if value in seen_middle:
                continue
            seen_middle.add(value)
            unique_middle.append(value)
            if len(unique_middle) >= slots:
                break

    return [ordered[0], *unique_middle[:slots], ordered[-1]]


async def extract_gif_keyframes(
    gif_source: str | bytes,
    *,
    max_width: Optional[int] = None,
    jpeg_quality: Optional[int] = None,
    max_keyframes: Optional[int] = None,
    frame_interval: Optional[int] = None,
    timeout_ms: Optional[int] = None,
) -> list[dict[str, Any]]:
    config = _load_gif_processor_config()
    if max_width is not None:
        config["max_width"] = max_width
    if jpeg_quality is not None:
        config["jpeg_quality"] = jpeg_quality
    if max_keyframes is not None:
        config["max_keyframes"] = max_keyframes
    if frame_interval is not None:
        config["frame_interval"] = frame_interval
    if timeout_ms is not None:
        config["timeout_ms"] = timeout_ms

    async def _run() -> list[dict[str, Any]]:
        data = gif_source if isinstance(gif_source, bytes) else await _download_bytes(gif_source)
        if not data:
            raise RuntimeError("Failed to download gif.")

        frames: list[dict[str, Any]] = []
        with Image.open(BytesIO(data)) as img:
            total_frames = max(1, int(getattr(img, "n_frames", 1)))
            indices = _calculate_keyframe_indices(
                total_frames,
                max(1, int(config["frame_interval"])),
                max(1, int(config["max_keyframes"])),
            )
            for frame_number, frame_index in enumerate(indices):
                img.seek(frame_index)
                frame = img.convert("RGB")
                if frame.width > config["max_width"]:
                    ratio = config["max_width"] / float(frame.width)
                    frame = frame.resize(
                        (config["max_width"], max(1, int(frame.height * ratio))),
                        Image.Resampling.LANCZOS,
                    )

                out = BytesIO()
                frame.save(
                    out,
                    format="JPEG",
                    quality=max(20, min(100, int(config["jpeg_quality"]))),
                    optimize=True,
                    progressive=True,
                )
                frames.append(
                    {
                        "data": base64.b64encode(out.getvalue()).decode("ascii"),
                        "mime_type": "image/jpeg",
                        "frame_number": frame_number,
                        "total_frames": total_frames,
                        "original_frame_index": frame_index,
                    }
                )
        return frames

    timeout_seconds = max(1.0, config["timeout_ms"] / 1000.0)
    return await asyncio.wait_for(_run(), timeout=timeout_seconds)


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
        keyframes = await extract_gif_keyframes(data)
    except Exception as exc:
        logger.warning("GIF parse failed: %s", exc)
        return ToolResult(ok=False, summary="Failed to parse gif.")
    summary = (
        f"GIF has {info.get('frames')} frame(s). "
        f"Extracted {len(keyframes)} keyframe(s) for model-friendly analysis."
    )
    return ToolResult(
        ok=True,
        summary=summary,
        data={
            **info,
            "keyframes": keyframes,
        },
    )


tool_process_gif = ToolDefinition(
    name="process_gif",
    description="Extract basic info about a GIF (dev only).",
    args_schema={"url": "gif url"},
    handler=_handle_process_gif,
)
