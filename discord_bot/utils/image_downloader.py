"""Safe image download and validation for custom personas."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

import aiohttp
from PIL import Image

MAX_AVATAR_BYTES = 500 * 1024
MAX_BANNER_BYTES = 500 * 1024
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
ALLOWED_SCHEMES = {"http", "https"}


def _is_allowed_url(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme in ALLOWED_SCHEMES


async def download_and_validate_image(
    url: str,
    save_path: Path,
    max_size: int,
) -> Tuple[bool, str]:
    """
    Download image from URL, validate it is an actual image, then save.
    - Enforce scheme (http/https only)
    - Enforce size limit
    - Check Content-Type when available
    - Validate image bytes with Pillow
    """
    if not _is_allowed_url(url):
        return False, "Invalid URL scheme"

    try:
        async with aiohttp.ClientSession() as session:
            # HEAD request (best-effort)
            try:
                async with session.head(url, allow_redirects=True, timeout=10) as resp:
                    if resp.status >= 400:
                        return False, f"URL returned status {resp.status}"
                    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                    if content_type and content_type not in ALLOWED_MIME_TYPES:
                        return False, f"Invalid content type: {content_type}"
                    content_length = resp.headers.get("Content-Length")
                    if content_length and int(content_length) > max_size:
                        return False, "Image too large"
            except Exception:
                # Some hosts block HEAD; continue to GET
                pass

            async with session.get(url, timeout=30) as resp:
                if resp.status >= 400:
                    return False, f"Download failed: status {resp.status}"

                data = bytearray()
                async for chunk in resp.content.iter_chunked(8192):
                    data.extend(chunk)
                    if len(data) > max_size:
                        return False, "Image exceeds size limit"

        try:
            image = Image.open(BytesIO(data))
            image.load()
        except Exception:
            return False, "File is not a valid image"

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        output = BytesIO()
        image.save(output, format="WEBP", quality=80, method=6)
        converted = output.getvalue()
        if len(converted) > max_size:
            return False, "Image too large after conversion"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(converted)
        return True, "ok"

    except aiohttp.ClientError as exc:
        return False, f"Network error: {exc}"
    except Exception as exc:
        return False, f"Error: {exc}"
