"""
Guild-specific AI configuration and dispatch.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - exercised in lightweight test environments
    AsyncOpenAI = None

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
    stream_events_from_text,
    stream_openai_chat_completions,
    stream_gemini_with_key,
    _is_rate_limit_error,
    _parse_timeout,
)
from utils.streaming.types import ProviderFeatures, StreamEvent

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
OPENROUTER_NO_FALLBACK_SENTINELS = {"none", "no", "off", "disable", "disabled"}

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


async def get_guild_gemini_key_type(guild_id: int) -> str:
    config = await get_guild_config(guild_id)
    key_type = (config.get("gemini_key_type") or "paid").strip().lower()
    return key_type if key_type in {"free", "paid"} else "paid"


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


def _default_openrouter_fallbacks(primary_model_id: str) -> List[str]:
    fallbacks: List[str] = []
    for item in RECOMMENDED_OPENROUTER_MODELS:
        model = normalize_openrouter_model(item)
        if not model or model == primary_model_id or model in fallbacks:
            continue
        fallbacks.append(model)
    return fallbacks


def normalize_openrouter_fallback_setting(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.lower() in OPENROUTER_NO_FALLBACK_SENTINELS:
        return "none"
    return normalized


async def get_guild_openrouter_config(guild_id: int) -> Tuple[str, List[str]]:
    config = await get_guild_config(guild_id)
    raw_model = config.get("openrouter_model") or OPENROUTER_DEFAULT_MODEL
    model_id = normalize_openrouter_model(raw_model) or raw_model

    fallbacks_raw = normalize_openrouter_fallback_setting(config.get("openrouter_fallback_models"))
    if fallbacks_raw == "none":
        return model_id, []
    fallbacks: List[str] = []
    for item in [val.strip() for val in (fallbacks_raw or "").split(",") if val.strip()]:
        model = normalize_openrouter_model(item)
        if model:
            fallbacks.append(model)
        else:
            logger.warning("Ignoring unknown OpenRouter model '%s' for guild %s", item, guild_id)
    if not fallbacks:
        fallbacks = _default_openrouter_fallbacks(model_id)
    return model_id, fallbacks


def _parse_capabilities(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    items = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return list(dict.fromkeys(items))


def get_custom_endpoint_features(capabilities: List[str]) -> ProviderFeatures:
    capability_set = {str(item).strip().lower() for item in capabilities if str(item).strip()}
    openai_compatible = bool(
        capability_set.intersection({"openai_compat", "openai-compatible", "openai_chat"})
    )
    supports_streaming = openai_compatible and bool(
        capability_set.intersection({"streaming", "openai_streaming"})
    )
    supports_tools = openai_compatible and bool(
        capability_set.intersection({"tools", "tool_calls", "openai_tools"})
    )
    supports_vision = "vision" in capability_set
    supports_video = "video" in capability_set
    text_only = not any((supports_tools, supports_vision, supports_video))
    return ProviderFeatures(
        openai_compatible=openai_compatible,
        supports_streaming=supports_streaming,
        supports_tools=supports_tools,
        supports_vision=supports_vision,
        supports_video=supports_video,
        text_only=text_only,
    )


async def get_guild_custom_endpoint_config(
    guild_id: int,
) -> Tuple[Optional[str], Optional[str], Optional[str], List[str], bool]:
    """Return (url, api_key, model, capabilities, enabled)."""
    config = await get_guild_config(guild_id)
    url = (config.get("custom_endpoint_url") or "").strip() or None
    model = (config.get("custom_model_name") or "").strip() or None
    enabled = bool(config.get("custom_endpoint_enabled") or 0)
    capabilities = _parse_capabilities(config.get("custom_model_capabilities"))

    api_key_encrypted = config.get("custom_endpoint_api_key")
    api_key = None
    if api_key_encrypted:
        try:
            api_key = get_encryption().decrypt(api_key_encrypted)
        except Exception:
            api_key = None
    return url, api_key, model, capabilities, enabled


async def _next_key_index(guild_id: int, task: str, key_count: int) -> int:
    async with _guild_key_lock:
        current = _guild_key_index.get((guild_id, task), 0)
        current %= max(key_count, 1)
        _guild_key_index[(guild_id, task)] = (current + 1) % max(key_count, 1)
        return current


async def _get_key_index(guild_id: int, task: str, key_count: int) -> int:
    async with _guild_key_lock:
        current = _guild_key_index.get((guild_id, task), 0)
        return current % max(key_count, 1)


async def _set_key_index(guild_id: int, task: str, index: int, key_count: int) -> None:
    async with _guild_key_lock:
        _guild_key_index[(guild_id, task)] = index % max(key_count, 1)


async def _generate_with_keys(
    guild_id: int,
    task: str,
    keys: List[str],
    model: str,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
) -> tuple[str, str]:
    if not keys:
        raise GuildConfigError(f"{task} keys not configured for this server.")
    request_timeout = _parse_timeout(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"), 30.0)
    key_type = await get_guild_gemini_key_type(guild_id)
    if key_type == "free":
        start = await _next_key_index(guild_id, task, len(keys))
    else:
        start = await _get_key_index(guild_id, task, len(keys))
    last_error: Optional[Exception] = None
    for offset in range(len(keys)):
        key_index = (start + offset) % len(keys)
        key = keys[key_index]
        try:
            effective_prompt = prompt
            if messages:
                blocks: list[str] = []
                if system_instruction:
                    blocks.append(system_instruction.strip())
                for item in messages:
                    role = str(item.get("role") or "user").strip().lower()
                    content = str(item.get("content") or "").strip()
                    if not content:
                        continue
                    blocks.append(f"{role.upper()}: {content}")
                if blocks:
                    effective_prompt = "\n\n".join(blocks)
            response = await generate_gemini_with_key(key, model, effective_prompt, request_timeout)
            if key_type != "free":
                await _set_key_index(guild_id, task, key_index, len(keys))
            return response
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(str(exc).lower()):
                continue
            continue
    raise RuntimeError(f"All guild {task} keys failed. Last error: {last_error}")


async def generate_guild_gemini_text(
    guild_id: int,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
) -> tuple[str, str]:
    keys = await get_guild_gemini_keys(guild_id)
    model = await get_guild_gemini_model(guild_id)
    return await _generate_with_keys(
        guild_id,
        "general",
        keys,
        model,
        prompt,
        messages=messages,
        system_instruction=system_instruction,
    )


async def stream_guild_gemini_text(
    guild_id: int,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
    tools: Optional[list[dict[str, Any]]] = None,
) -> AsyncIterator[StreamEvent]:
    if tools:
        raise RuntimeError("Gemini streaming tool events are not supported.")
    keys = await get_guild_gemini_keys(guild_id)
    model = await get_guild_gemini_model(guild_id)
    if not keys:
        raise GuildConfigError("general keys not configured for this server.")
    request_timeout = _parse_timeout(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"), 30.0)
    key_type = await get_guild_gemini_key_type(guild_id)
    if key_type == "free":
        start = await _next_key_index(guild_id, "general", len(keys))
    else:
        start = await _get_key_index(guild_id, "general", len(keys))
    last_error: Optional[Exception] = None
    for offset in range(len(keys)):
        key_index = (start + offset) % len(keys)
        key = keys[key_index]
        try:
            async for event in stream_gemini_with_key(
                key,
                model,
                prompt,
                request_timeout=request_timeout,
                messages=messages,
                system_instruction=system_instruction,
            ):
                yield event
            if key_type != "free":
                await _set_key_index(guild_id, "general", key_index, len(keys))
            return
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(str(exc).lower()):
                continue
            continue
    if last_error:
        raise RuntimeError(f"All guild general keys failed. Last error: {last_error}")
    raise RuntimeError("All guild general keys failed.")


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

    key_type = await get_guild_gemini_key_type(guild_id)
    if key_type == "free":
        start = await _next_key_index(guild_id, "general", len(keys))
    else:
        start = await _get_key_index(guild_id, "general", len(keys))
    last_error: Optional[Exception] = None

    for offset in range(len(keys)):
        key_index = (start + offset) % len(keys)
        key = keys[key_index]
        try:
            response = await generate_gemini_with_key_and_image(key, model, prompt, image, request_timeout)
            if key_type != "free":
                await _set_key_index(guild_id, "general", key_index, len(keys))
            return response
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


async def generate_guild_openrouter_text(
    guild_id: int,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
) -> tuple[str, str]:
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
            return await manager.generate(
                prompt,
                messages=messages,
                system_instruction=system_instruction,
            )
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"All OpenRouter keys failed. Last error: {last_error}")


async def stream_guild_openrouter_text(
    guild_id: int,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
    tools: Optional[list[dict[str, Any]]] = None,
) -> AsyncIterator[StreamEvent]:
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
            async for event in manager.stream_generate(
                prompt,
                messages=messages,
                system_instruction=system_instruction,
                tools=tools,
            ):
                yield event
            return
        except UserInputError:
            raise
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"All OpenRouter keys failed. Last error: {last_error}")


_custom_client_cache: Dict[tuple[int, str, str], AsyncOpenAI] = {}


def _get_custom_client(guild_id: int, api_key: Optional[str], base_url: str) -> AsyncOpenAI:
    if AsyncOpenAI is None:
        raise RuntimeError("openai is not installed")
    cache_key = (guild_id, api_key or "", base_url)
    cached = _custom_client_cache.get(cache_key)
    if cached:
        return cached
    client = AsyncOpenAI(
        api_key=api_key or "EMPTY",
        base_url=base_url,
        timeout=_parse_timeout(os.getenv("CUSTOM_ENDPOINT_TIMEOUT_SECONDS"), 45.0),
        max_retries=0,
    )
    _custom_client_cache[cache_key] = client
    return client


async def generate_guild_custom_text(
    guild_id: int,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
) -> tuple[str, str]:
    url, api_key, model, _, enabled = await get_guild_custom_endpoint_config(guild_id)
    if not enabled or not url or not model:
        raise GuildConfigError("Custom endpoint not configured for this server.")
    client = _get_custom_client(guild_id, api_key, url)
    payload_messages: List[dict] = []
    if messages:
        if system_instruction:
            payload_messages.append({"role": "system", "content": system_instruction})
        payload_messages.extend(messages)
    else:
        payload_messages = [{"role": "user", "content": prompt}]
    response = await client.chat.completions.create(
        model=model,
        messages=payload_messages,
    )
    if not response or not getattr(response, "choices", None):
        raise RuntimeError("Custom endpoint returned no choices.")
    message = response.choices[0].message
    content = getattr(message, "content", None)
    if not content:
        raise RuntimeError("Custom endpoint returned empty content.")
    return content, model


async def stream_guild_custom_text(
    guild_id: int,
    prompt: str,
    messages: Optional[List[dict]] = None,
    system_instruction: Optional[str] = None,
    tools: Optional[list[dict[str, Any]]] = None,
) -> AsyncIterator[StreamEvent]:
    url, api_key, model, capabilities, enabled = await get_guild_custom_endpoint_config(guild_id)
    if not enabled or not url or not model:
        raise GuildConfigError("Custom endpoint not configured for this server.")

    features = get_custom_endpoint_features(capabilities)
    if tools and not features.supports_tools:
        raise RuntimeError("Custom endpoint streaming tool events are not supported.")
    if not features.supports_streaming:
        text, _ = await generate_guild_custom_text(
            guild_id,
            prompt,
            messages=messages,
            system_instruction=system_instruction,
        )
        async for event in stream_events_from_text(text):
            yield event
        return

    client = _get_custom_client(guild_id, api_key, url)
    payload_messages: List[dict[str, Any]] = []
    if messages:
        if system_instruction:
            payload_messages.append({"role": "system", "content": system_instruction})
        payload_messages.extend(messages)
    else:
        payload_messages = [{"role": "user", "content": prompt}]

    async for event in stream_openai_chat_completions(
        client,
        model=model,
        messages=payload_messages,
        timeout=_parse_timeout(os.getenv("CUSTOM_ENDPOINT_TIMEOUT_SECONDS"), 45.0),
        tools=tools if features.supports_tools else None,
    ):
        yield event
