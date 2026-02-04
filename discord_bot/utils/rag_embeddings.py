from __future__ import annotations

import os
from typing import List, Optional

from openai import AsyncOpenAI

from utils.guild_ai import get_guild_openrouter_keys
from utils.logger import get_logger

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_client_cache: dict[tuple[int, str, str], AsyncOpenAI] = {}


def _build_client(guild_id: int, api_key: str, base_url: str) -> AsyncOpenAI:
    cache_key = (guild_id, api_key, base_url)
    cached = _client_cache.get(cache_key)
    if cached:
        return cached
    headers = None
    if base_url.startswith("https://openrouter.ai/"):
        headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_APP_URL", "https://github.com/gecallidryas/femboi"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Femmy Discord Bot"),
        }
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=headers, timeout=45, max_retries=0)
    _client_cache[cache_key] = client
    return client


async def _resolve_embedding_key(guild_id: int) -> Optional[str]:
    env_key = os.getenv("RAG_EMBEDDING_API_KEY")
    if env_key:
        return env_key
    keys = await get_guild_openrouter_keys(guild_id)
    return keys[0] if keys else None


async def embed_texts(guild_id: int, texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    api_key = await _resolve_embedding_key(guild_id)
    if not api_key:
        raise RuntimeError("No embedding API key configured.")
    base_url = os.getenv("RAG_OPENAI_BASE_URL") or OPENROUTER_BASE_URL
    model = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
    client = _build_client(guild_id, api_key, base_url)
    response = await client.embeddings.create(model=model, input=texts)
    if not response or not getattr(response, "data", None):
        raise RuntimeError("Embedding request returned no data.")
    return [item.embedding for item in response.data]
