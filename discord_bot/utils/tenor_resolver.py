from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Optional
from urllib.parse import unquote

import aiohttp

from utils.logger import get_logger

logger = get_logger(__name__)


FetchHtmlFn = Callable[[str], Awaitable[Optional[str]]]


async def _default_fetch_html(url: str) -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as response:
                if response.status >= 400:
                    logger.warning("Tenor resolver fetch failed: %s", response.status)
                    return None
                return await response.text()
    except Exception as exc:
        logger.warning("Tenor resolver fetch failed: %s", exc)
        return None


def _extract_from_gif_json(html: str) -> Optional[str]:
    match = re.search(
        r"<script[^>]*id=['\"]gif-json['\"][^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    try:
        payload = json.loads((match.group(1) or "").strip())
    except Exception:
        return None
    gif_url = payload.get("media_formats", {}).get("gif", {}).get("url")
    if isinstance(gif_url, str) and gif_url:
        return gif_url
    return None


def _extract_via_regex(html: str, url_slug: str) -> Optional[str]:
    candidates = re.findall(
        r"https?://media\.tenor\.com/[^\s\"'<>]+\.(?:gif|mp4|webm|png)",
        html,
        flags=re.IGNORECASE,
    )
    if not candidates:
        return None

    decoded_slug = unquote(url_slug or "").lower()
    matching: list[str] = []
    for url in candidates:
        filename = (url.rsplit("/", 1)[-1] or "").lower()
        stem = re.sub(r"\.(gif|mp4|webm|png)$", "", filename, flags=re.IGNORECASE)
        if stem and stem in decoded_slug:
            matching.append(url)

    if not matching:
        matching = candidates
    gif = next((url for url in matching if url.lower().endswith(".gif")), None)
    return gif or matching[0]


async def resolve_tenor_url(
    tenor_view_url: str,
    fetch_html: Optional[FetchHtmlFn] = None,
) -> Optional[str]:
    if not tenor_view_url:
        return None
    if "tenor.com/view/" not in tenor_view_url:
        return tenor_view_url

    slug_match = re.search(r"/view/([A-Za-z0-9%-]+)-gif-\d+", tenor_view_url)
    url_slug = slug_match.group(1) if slug_match else ""

    fetcher = fetch_html or _default_fetch_html
    html = await fetcher(tenor_view_url)
    if not html:
        return None

    from_json = _extract_from_gif_json(html)
    if from_json:
        return from_json
    return _extract_via_regex(html, url_slug)

