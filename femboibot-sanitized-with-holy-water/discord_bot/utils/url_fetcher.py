from __future__ import annotations

import asyncio
from typing import Optional

import aiohttp
import trafilatura

from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 15
MAX_BYTES = 2_000_000


async def fetch_url_text(url: str, timeout: int = DEFAULT_TIMEOUT, max_bytes: int = MAX_BYTES) -> Optional[str]:
    if not url:
        return None

    async def _fetch() -> Optional[str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status >= 400:
                    return None
                data = await response.content.read(max_bytes)
                if not data:
                    return None
                html = data.decode(errors="ignore")
                extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
                if extracted:
                    return extracted.strip()
                return html.strip()

    try:
        return await asyncio.wait_for(_fetch(), timeout=timeout + 2)
    except Exception as exc:
        logger.warning("Failed to fetch url %s: %s", url, exc)
        return None
