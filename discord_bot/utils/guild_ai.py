"""
Guild-specific AI configuration and dispatch.
"""

from __future__ import annotations

import asyncio
import os
from typing import Dict, List, Optional, Tuple

from utils.logger import get_logger
from utils.db_handler import get_guild_config
from utils.encryption import get_encryption
from utils.api_manager import (
    UserInputError,
    OpenRouterManager,
    normalize_openrouter_model,
    normalize_gemini_model,
    generate_gemini_with_key,
    generate_gemini_with_key_and_image,
    _is_rate_limit_error,
    _parse_timeout,
)

logger = get_logger(__name__)

GEMINI_DEFAULT_MODEL = "gemini-2.5-flash-lite"
OPENROUTER_DEFAULT_MODEL = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"

RECOMMENDED_GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

RECOMMENDED_OPENROUTER_MODELS = [
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nousresearch/deephermes-3-mistral-24b-preview",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek/deepseek-chat",
]

_guild_key_index: Dict[tuple[int, str], int] = {}
_guild_key_lock = asyncio.Lock()

_openrouter_cache: Dict[tuple[int, str], Tuple[Tuple[str, str, Tuple[str, ...]], OpenRouterManager]] = {}

GEMINI_GENERAL_FIELDS = [
    "gemini_api_key",
    "gemini_api_key_2",
    "gemini_api_key_3",
    "gemini_api_key_4",
    "gemini_api_key_5",
]

GEMINI_TRANSLATE_FIELDS = [
    "gemini_translate_key",
    "gemini_translate_key_2",
    "gemini_translate_key_3",
    "gemini_translate_key_4",
    "gemini_translate_key_5",
]

GEMINI_SUMMARIZE_FIELDS = [
    "gemini_summarize_key",
    "gemini_summarize_key_2",
    "gemini_summarize_key_3",
    "gemini_summarize_key_4",
    "gemini_summarize_key_5",
]

GEMINI_PROFILE_FIELDS = [
    "gemini_profile_key",
]

OPENROUTER_KEY_FIELDS = [
    "openrouter_api_key",
    "openrouter_api_key_2",
    "openrouter_api_key_3",
    "openrouter_api_key_4",
    "openrouter_api_key_5",
]


class GuildConfigError(RuntimeError):
    """Raised when a guild has not configured required AI keys."""


async def _get_keys_from_config(guild_id: int, fields: List[str]) -> List[str]:
    config = await get_guild_config(guild_id)
    encryption = get_encryption()
    keys: List[str] = []
    for field in fields:
        encrypted = config.get(field)
        if not encrypted:
            continue
        try:
            keys.append(encryption.decrypt(encrypted))
        except Exception as exc:
            logger.warning("Failed to decrypt %s for guild %s: %s", field, guild_id, exc)
    return keys


async def get_guild_gemini_keys(guild_id: int) -> List[str]:
    return await _get_keys_from_config(guild_id, GEMINI_GENERAL_FIELDS)


async def get_guild_translate_keys(guild_id: int) -> List[str]:
    return await _get_keys_from_config(guild_id, GEMINI_TRANSLATE_FIELDS)


async def get_guild_summarize_keys(guild_id: int) -> List[str]:
    return await _get_keys_from_config(guild_id, GEMINI_SUMMARIZE_FIELDS)


async def get_guild_profile_key(guild_id: int) -> Optional[str]:
    keys = await _get_keys_from_config(guild_id, GEMINI_PROFILE_FIELDS)
    return keys[0] if keys else None


async def get_guild_gemini_model(guild_id: int) -> str:
    config = await get_guild_config(guild_id)
    model = config.get("gemini_model") or GEMINI_DEFAULT_MODEL
    normalized = normalize_gemini_model(model)
    return normalized or model


async def get_guild_translate_model(guild_id: int) -> str:
    config = await get_guild_config(guild_id)
    model = config.get("gemini_translate_model") or config.get("gemini_model") or GEMINI_DEFAULT_MODEL
    normalized = normalize_gemini_model(model)
    return normalized or model


async def get_guild_summarize_model(guild_id: int) -> str:
    config = await get_guild_config(guild_id)
    model = config.get("gemini_summarize_model") or config.get("gemini_model") or GEMINI_DEFAULT_MODEL
    normalized = normalize_gemini_model(model)
    return normalized or model


async def get_guild_openrouter_keys(guild_id: int) -> List[str]:
    return await _get_keys_from_config(guild_id, OPENROUTER_KEY_FIELDS)


async def get_guild_openrouter_config(guild_id: int) -> Tuple[str, List[str]]:
    config = await get_guild_config(guild_id)
    raw_model = config.get("openrouter_model") or OPENROUTER_DEFAULT_MODEL
    model_id = normalize_openrouter_model(raw_model) or raw_model

    fallbacks_raw = config.get("openrouter_fallback_models") or ""
    fallbacks: List[str] = []
    for item in [val.strip() for val in fallbacks_raw.split(",") if val.strip()]:
        model = normalize_openrouter_model(item)
        if model:
            fallbacks.append(model)
        else:
            logger.warning("Ignoring unknown OpenRouter model '%s' for guild %s", item, guild_id)
    return model_id, fallbacks


async def _next_key_index(guild_id: int, task: str, key_count: int) -> int:
    async with _guild_key_lock:
        current = _guild_key_index.get((guild_id, task), 0)
        current %= max(key_count, 1)
        _guild_key_index[(guild_id, task)] = (current + 1) % max(key_count, 1)
        return current


async def _generate_with_keys(
    guild_id: int,
    task: str,
    keys: List[str],
    model: str,
    prompt: str,
) -> tuple[str, str]:
    if not keys:
        raise GuildConfigError(f"{task} keys not configured for this server.")
    request_timeout = _parse_timeout(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"), 30.0)
    start = await _next_key_index(guild_id, task, len(keys))
    last_error: Optional[Exception] = None
    for offset in range(len(keys)):
        key = keys[(start + offset) % len(keys)]
        try:
            return await generate_gemini_with_key(key, model, prompt, request_timeout)
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(str(exc).lower()):
                continue
            continue
    raise RuntimeError(f"All guild {task} keys failed. Last error: {last_error}")


async def generate_guild_gemini_text(guild_id: int, prompt: str) -> tuple[str, str]:
    keys = await get_guild_gemini_keys(guild_id)
    model = await get_guild_gemini_model(guild_id)
    return await _generate_with_keys(guild_id, "general", keys, model, prompt)


async def generate_guild_gemini_translate_text(guild_id: int, prompt: str) -> tuple[str, str]:
    keys = await get_guild_translate_keys(guild_id)
    model = await get_guild_translate_model(guild_id)
    return await _generate_with_keys(guild_id, "translate", keys, model, prompt)


async def generate_guild_gemini_summary_text(guild_id: int, prompt: str) -> tuple[str, str]:
    keys = await get_guild_summarize_keys(guild_id)
    model = await get_guild_summarize_model(guild_id)
    return await _generate_with_keys(guild_id, "summarize", keys, model, prompt)


async def generate_guild_gemini_profile_text(guild_id: int, prompt: str) -> tuple[str, str]:
    key = await get_guild_profile_key(guild_id)
    if not key:
        raise GuildConfigError("Profile key not configured for this server.")
    model = await get_guild_gemini_model(guild_id)
    request_timeout = _parse_timeout(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"), 30.0)
    return await generate_gemini_with_key(key, model, prompt, request_timeout)


async def generate_guild_gemini_vision(guild_id: int, prompt: str, image) -> tuple[str, str]:
    keys = await get_guild_gemini_keys(guild_id)
    if not keys:
        raise GuildConfigError("Gemini API keys not configured for this server.")

    model = await get_guild_gemini_model(guild_id)
    request_timeout = _parse_timeout(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"), 30.0)

    start = await _next_key_index(guild_id, "general", len(keys))
    last_error: Optional[Exception] = None

    for offset in range(len(keys)):
        key = keys[(start + offset) % len(keys)]
        try:
            return await generate_gemini_with_key_and_image(key, model, prompt, image, request_timeout)
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(str(exc).lower()):
                continue
            continue

    raise RuntimeError(f"All guild Gemini keys failed. Last error: {last_error}")


def _get_openrouter_manager(guild_id: int, api_key: str, model: str, fallbacks: List[str]) -> OpenRouterManager:
    signature = (api_key, model, tuple(fallbacks))
    cache_key = (guild_id, api_key)
    cached = _openrouter_cache.get(cache_key)
    if cached and cached[0] == signature:
        return cached[1]
    manager = OpenRouterManager(api_key=api_key, model=model, fallback_models=fallbacks)
    _openrouter_cache[cache_key] = (signature, manager)
    return manager


async def generate_guild_openrouter_text(guild_id: int, prompt: str) -> tuple[str, str]:
    keys = await get_guild_openrouter_keys(guild_id)
    if not keys:
        raise GuildConfigError("OpenRouter API keys not configured for this server.")
    model, fallbacks = await get_guild_openrouter_config(guild_id)
    start = await _next_key_index(guild_id, "openrouter", len(keys))
    last_error: Optional[Exception] = None
    for offset in range(len(keys)):
        api_key = keys[(start + offset) % len(keys)]
        manager = _get_openrouter_manager(guild_id, api_key, model, fallbacks)
        try:
            return await manager.generate(prompt)
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"All OpenRouter keys failed. Last error: {last_error}")
