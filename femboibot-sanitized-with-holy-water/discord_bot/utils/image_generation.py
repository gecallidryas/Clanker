from __future__ import annotations

import asyncio
import os
from io import BytesIO
from typing import Any, Optional

import aiohttp
import discord
from openai import AsyncOpenAI

from utils.db_handler import get_guild_config
from utils.encryption import get_encryption
from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_IMAGE_SIZE = "1024x1024"
MAX_IMAGE_BYTES = 8 * 1024 * 1024


async def _download_image(url: str) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status >= 400:
                    return None
                data = await resp.read()
                return data
    except Exception as exc:
        logger.warning("Failed to download image: %s", exc)
        return None


async def _replicate_request(api_key: str, model_version: str, prompt: str) -> Optional[str]:
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    payload = {
        "version": model_version,
        "input": {"prompt": prompt},
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.replicate.com/v1/predictions",
            json=payload,
            headers=headers,
            timeout=30,
        ) as resp:
            if resp.status >= 400:
                logger.warning("Replicate create failed: %s", resp.status)
                return None
            data = await resp.json()
            prediction_id = data.get("id")
            if not prediction_id:
                return None

        # Poll for completion
        for _ in range(30):
            await asyncio.sleep(2)
            async with session.get(
                f"https://api.replicate.com/v1/predictions/{prediction_id}",
                headers=headers,
                timeout=30,
            ) as status_resp:
                if status_resp.status >= 400:
                    return None
                status_data = await status_resp.json()
                status = status_data.get("status")
                if status == "succeeded":
                    outputs = status_data.get("output") or []
                    if isinstance(outputs, list) and outputs:
                        return str(outputs[0])
                    if isinstance(outputs, str):
                        return outputs
                    return None
                if status in {"failed", "canceled"}:
                    return None
    return None


async def _generate_with_replicate(prompt: str, api_key: str, model_version: str) -> Optional[bytes]:
    url = await _replicate_request(api_key, model_version, prompt)
    if not url:
        return None
    return await _download_image(url)


async def _generate_with_openrouter(prompt: str, api_key: str, model: str, size: str) -> Optional[bytes]:
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=45,
        max_retries=0,
        default_headers={
            "HTTP-Referer": os.getenv("OPENROUTER_APP_URL", "https://github.com/gecallidryas/femboi"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Femmy Discord Bot"),
        },
    )
    try:
        response = await client.images.generate(model=model, prompt=prompt, size=size)
    except Exception as exc:
        logger.warning("OpenRouter image generation failed: %s", exc)
        return None
    url = None
    if response and getattr(response, "data", None):
        item = response.data[0]
        url = getattr(item, "url", None) or item.get("url") if isinstance(item, dict) else None
    if not url:
        return None
    return await _download_image(url)


async def _resolve_image_provider(guild_id: int) -> tuple[str, Optional[str], Optional[str]]:
    config = await get_guild_config(guild_id)
    provider = (config.get("image_provider") or "").strip().lower()
    model = (config.get("image_model") or "").strip()
    encryption = get_encryption()
    replicate_key = None

    encrypted_replicate = config.get("replicate_api_key")
    if encrypted_replicate:
        try:
            replicate_key = encryption.decrypt(encrypted_replicate)
        except Exception:
            replicate_key = None
    if not replicate_key:
        replicate_key = os.getenv("REPLICATE_API_KEY")

    if not provider:
        if replicate_key:
            provider = "replicate"
        else:
            provider = "openrouter"

    return provider, replicate_key, model


async def _handle_generate_image(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return ToolResult(ok=False, summary="Missing prompt.")

    size = (args.get("size") or DEFAULT_IMAGE_SIZE).strip()
    provider, replicate_key, model = await _resolve_image_provider(context.guild.id)

    image_bytes: Optional[bytes] = None
    if provider == "replicate":
        if not replicate_key:
            return ToolResult(ok=False, summary="Replicate key not configured.")
        if not model:
            return ToolResult(ok=False, summary="Replicate model version not configured.")
        image_bytes = await _generate_with_replicate(prompt, replicate_key, model)
    else:
        # Use OpenRouter key for image generation
        config = await get_guild_config(context.guild.id)
        encrypted_openrouter = config.get("openrouter_api_key")
        openrouter_key = None
        if encrypted_openrouter:
            try:
                openrouter_key = get_encryption().decrypt(encrypted_openrouter)
            except Exception:
                openrouter_key = None
        if not openrouter_key:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            return ToolResult(ok=False, summary="OpenRouter key not configured.")
        if not model:
            model = "openai/gpt-image-1"
        image_bytes = await _generate_with_openrouter(prompt, openrouter_key, model, size)

    if not image_bytes:
        return ToolResult(ok=False, summary="Image generation failed.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return ToolResult(ok=False, summary="Generated image too large to send.")

    file = discord.File(BytesIO(image_bytes), filename="generated.png")
    await context.channel.send(file=file)
    return ToolResult(ok=True, summary="Generated and sent image.", data={"provider": provider, "size": size})


tool_generate_image = ToolDefinition(
    name="generate_image",
    description="Generate an image from a text prompt.",
    args_schema={"prompt": "image description", "size": "e.g., 1024x1024 (optional)"},
    handler=_handle_generate_image,
)
