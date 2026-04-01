from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Optional

import aiohttp
from duckduckgo_search import DDGS

from utils.db_handler import get_guild_config
from utils.encryption import get_encryption
from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult
from utils.url_fetcher import fetch_url_text

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 300
_cache: dict[tuple[str, str], tuple[float, list[dict[str, str]]]] = {}


def _cache_get(provider: str, query: str) -> Optional[list[dict[str, str]]]:
    key = (provider, query)
    entry = _cache.get(key)
    if not entry:
        return None
    ts, results = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return results


def _cache_set(provider: str, query: str, results: list[dict[str, str]]) -> None:
    _cache[(provider, query)] = (time.time(), results)


async def duckduckgo_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    cached = _cache_get("ddg", query)
    if cached is not None:
        return cached

    def _run() -> list[dict[str, str]]:
        with DDGS() as ddgs:
            rows = []
            for item in ddgs.text(query, max_results=max_results):
                rows.append(
                    {
                        "title": item.get("title") or "",
                        "url": item.get("href") or item.get("url") or "",
                        "snippet": item.get("body") or item.get("snippet") or "",
                    }
                )
            return rows

    try:
        results = await asyncio.to_thread(_run)
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        results = []

    _cache_set("ddg", query, results)
    return results


async def brave_search(query: str, api_key: str, max_results: int = 5) -> list[dict[str, str]]:
    cached = _cache_get("brave", query)
    if cached is not None:
        return cached

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"X-Subscription-Token": api_key}
    params = {"q": query, "count": max_results}
    results: list[dict[str, str]] = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=15) as resp:
                if resp.status >= 400:
                    logger.warning("Brave search failed: status=%s", resp.status)
                    return []
                data = await resp.json()
        for item in (data.get("web") or {}).get("results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "snippet": item.get("description") or "",
                }
            )
    except Exception as exc:
        logger.warning("Brave search failed: %s", exc)
        results = []

    _cache_set("brave", query, results)
    return results


async def _get_brave_key(guild_id: int) -> Optional[str]:
    env_key = os.getenv("BRAVE_API_KEY")
    if env_key:
        return env_key
    config = await get_guild_config(guild_id)
    encrypted = config.get("brave_api_key")
    if not encrypted:
        return None
    try:
        return get_encryption().decrypt(encrypted)
    except Exception:
        return None


def _format_results(results: list[dict[str, str]]) -> str:
    if not results:
        return "No results found."
    lines = []
    for idx, item in enumerate(results, start=1):
        title = item.get("title") or "Untitled"
        url = item.get("url") or ""
        snippet = item.get("snippet") or ""
        lines.append(f"{idx}. {title} - {url} ({snippet})")
    return "\n".join(lines)


async def _handle_web_search(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult(ok=False, summary="Missing query.")

    max_results = int(args.get("max_results") or 5)
    max_results = max(1, min(max_results, 8))
    brave_key = await _get_brave_key(context.guild.id)

    if brave_key:
        results = await brave_search(query, brave_key, max_results=max_results)
        provider = "brave"
    else:
        results = await duckduckgo_search(query, max_results=max_results)
        provider = "duckduckgo"

    summary = f"Web search ({provider}) results for '{query}'."
    return ToolResult(
        ok=True,
        summary=summary,
        data={"provider": provider, "query": query, "results": results, "formatted": _format_results(results)},
    )


async def _handle_fetch_url(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    url = (args.get("url") or "").strip()
    if not url:
        return ToolResult(ok=False, summary="Missing url.")
    text = await fetch_url_text(url)
    if not text:
        return ToolResult(ok=False, summary="Failed to fetch url.")
    trimmed = text[:4000]
    return ToolResult(
        ok=True,
        summary=f"Fetched content from {url}.",
        data={"url": url, "content": trimmed},
    )


tool_web_search = ToolDefinition(
    name="web_search",
    description="Search the web for recent or general information.",
    args_schema={"query": "search query text", "max_results": "1-8 (optional)"},
    handler=_handle_web_search,
)

tool_fetch_url = ToolDefinition(
    name="fetch_url",
    description="Fetch and extract text from a URL.",
    args_schema={"url": "https://example.com/article"},
    handler=_handle_fetch_url,
)
