from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp
from duckduckgo_search import DDGS
from utils.api_manager import _parse_timeout
from utils.guild_ai import get_guild_gemini_keys, get_guild_gemini_model

from utils.db_handler import get_guild_config
from utils.encryption import get_encryption
from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult
from utils.url_fetcher import fetch_url_text

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - exercised in lightweight test environments
    genai = None
    genai_types = None

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


def clear_search_cache(provider: Optional[str] = None, query: Optional[str] = None) -> None:
    if provider is None and query is None:
        _cache.clear()
        return

    keys_to_remove: list[tuple[str, str]] = []
    for cache_provider, cache_query in list(_cache):
        if provider is not None and cache_provider != provider:
            continue
        if query is not None and cache_query != query:
            continue
        keys_to_remove.append((cache_provider, cache_query))

    for cache_key in keys_to_remove:
        _cache.pop(cache_key, None)


async def _get_gemini_search_config(guild_id: int) -> Optional[tuple[list[str], str]]:
    keys = await get_guild_gemini_keys(guild_id)
    if not keys:
        return None
    model = await get_guild_gemini_model(guild_id)
    return keys, model


def _normalize_snippet(text: str, limit: int = 280) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _has_usable_gemini_chunk(grounding_metadata: Any) -> bool:
    for chunk in getattr(grounding_metadata, "grounding_chunks", None) or []:
        web_chunk = getattr(chunk, "web", None)
        url = (getattr(web_chunk, "uri", None) or "").strip()
        if url:
            return True
    return False


def _get_gemini_grounding_metadata(response: Any) -> Any:
    for candidate in getattr(response, "candidates", None) or []:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        if grounding_metadata is not None and _has_usable_gemini_chunk(grounding_metadata):
            return grounding_metadata
    return None


def _get_chunk_title(web_chunk: Any, url: str) -> tuple[str, int]:
    title = str(getattr(web_chunk, "title", None) or "").strip()
    if title:
        return title, 3

    domain = str(getattr(web_chunk, "domain", None) or "").strip()
    if domain:
        return domain, 2

    parsed = urlparse(url)
    host = (parsed.hostname or parsed.netloc or "").strip()
    if host.startswith("www."):
        host = host[4:]
    if host:
        return host, 1

    return "Untitled source", 0


def _extract_gemini_results(response: Any, max_results: int) -> list[dict[str, str]]:
    grounding_metadata = _get_gemini_grounding_metadata(response)
    if grounding_metadata is None:
        return []

    snippet_map: dict[int, list[str]] = {}
    for support in getattr(grounding_metadata, "grounding_supports", None) or []:
        segment = getattr(support, "segment", None)
        snippet = _normalize_snippet(getattr(segment, "text", None) or "")
        if not snippet:
            continue
        for chunk_index in getattr(support, "grounding_chunk_indices", None) or []:
            try:
                index = int(chunk_index)
            except (TypeError, ValueError):
                continue
            bucket = snippet_map.setdefault(index, [])
            if snippet not in bucket:
                bucket.append(snippet)

    results_by_url: dict[str, dict[str, Any]] = {}
    for index, chunk in enumerate(getattr(grounding_metadata, "grounding_chunks", None) or []):
        web_chunk = getattr(chunk, "web", None)
        url = (getattr(web_chunk, "uri", None) or "").strip()
        if not url:
            continue
        title, priority = _get_chunk_title(web_chunk, url)
        snippets = snippet_map.get(index, [])
        entry = results_by_url.get(url)
        if entry is None:
            results_by_url[url] = {
                "title": title,
                "priority": priority,
                "url": url,
                "snippets": list(snippets),
            }
            continue

        if priority > entry["priority"]:
            entry["title"] = title
            entry["priority"] = priority
        for snippet in snippets:
            if snippet not in entry["snippets"]:
                entry["snippets"].append(snippet)

    results: list[dict[str, str]] = []
    for entry in results_by_url.values():
        results.append(
            {
                "title": entry["title"],
                "url": entry["url"],
                "snippet": " ".join(entry["snippets"]).strip(),
            }
        )
        if len(results) >= max_results:
            break
    return results


def _run_gemini_search_sync(
    api_key: str,
    model: str,
    query: str,
    max_results: int,
) -> list[dict[str, str]]:
    if genai is None or genai_types is None:
        raise RuntimeError("google-genai is not installed")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=query,
        config=genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
        ),
    )
    return _extract_gemini_results(response, max_results=max_results)


async def gemini_search(
    query: str,
    api_keys: list[str],
    model: str,
    max_results: int = 5,
) -> Optional[list[dict[str, str]]]:
    cached = _cache_get("gemini", query)
    if cached is not None:
        return cached

    request_timeout = _parse_timeout(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS"), 30.0)
    last_error: Optional[Exception] = None
    for api_key in api_keys:
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    _run_gemini_search_sync,
                    api_key,
                    model,
                    query,
                    max_results,
                ),
                timeout=request_timeout,
            )
            _cache_set("gemini", query, results)
            return results
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini search failed: %s", exc)
    if last_error is not None:
        logger.warning("Gemini search exhausted all configured keys: %s", last_error)
    return None


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
        title = item.get("title") or "Untitled source"
        url = item.get("url") or ""
        snippet = _normalize_snippet(item.get("snippet") or "")
        lines.append(f"{idx}. [{title}]({url})" if url else f"{idx}. {title}")
        if snippet:
            lines.append(snippet)
        if idx < len(results):
            lines.append("")
    return "\n".join(lines)


async def _handle_web_search(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult(ok=False, summary="Missing query.")

    max_results = int(args.get("max_results") or 5)
    max_results = max(1, min(max_results, 8))
    guild_id = getattr(getattr(context, "guild", None), "id", None)
    if guild_id is None:
        return ToolResult(ok=False, summary="Web search is only available in servers.")

    gemini_config = await _get_gemini_search_config(guild_id)
    if gemini_config:
        api_keys, model = gemini_config
        gemini_results = await gemini_search(query, api_keys, model, max_results=max_results)
        if gemini_results:
            results = gemini_results
            provider = "gemini"
        else:
            brave_key = await _get_brave_key(guild_id)
            if brave_key:
                results = await brave_search(query, brave_key, max_results=max_results)
                provider = "brave"
            else:
                results = await duckduckgo_search(query, max_results=max_results)
                provider = "duckduckgo"
    else:
        brave_key = await _get_brave_key(guild_id)
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
