import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.image_downloader import download_and_validate_image, MAX_AVATAR_BYTES


class FakeContent:
    def __init__(self, chunks):
        self._chunks = chunks

    async def iter_chunked(self, size):
        for chunk in self._chunks:
            yield chunk


class FakeResponse:
    def __init__(self, status=200, headers=None, data=b""):
        self.status = status
        self.headers = headers or {}
        self.content = FakeContent([data])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, head_response, get_response):
        self._head_response = head_response
        self._get_response = get_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def head(self, url, allow_redirects=True, timeout=10):
        return self._head_response

    def get(self, url, timeout=30):
        return self._get_response


class ImageDownloaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_invalid_scheme(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "avatar.webp"
            success, message = await download_and_validate_image(
                "ftp://example.com/avatar.png",
                path,
                MAX_AVATAR_BYTES,
            )
        self.assertFalse(success)
        self.assertIn("Invalid URL scheme", message)

    async def test_rejects_large_content_length(self):
        head = FakeResponse(status=200, headers={
            "Content-Type": "image/png",
            "Content-Length": str(MAX_AVATAR_BYTES + 1),
        })
        get_resp = FakeResponse(status=200, headers={}, data=b"")

        with mock.patch("utils.image_downloader.aiohttp.ClientSession", return_value=FakeSession(head, get_resp)):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "avatar.webp"
                success, message = await download_and_validate_image(
                    "https://example.com/avatar.png",
                    path,
                    MAX_AVATAR_BYTES,
                )

        self.assertFalse(success)
        self.assertIn("Image too large", message)

    async def test_downloads_and_saves_image(self):
        head = FakeResponse(status=200, headers={"Content-Type": "image/png"})
        get_resp = FakeResponse(status=200, headers={}, data=b"fakebytes")

        class DummyImage:
            mode = "RGBA"

            def load(self):
                return None

            def save(self, output, format="WEBP", quality=80, method=6):
                output.write(b"webp")

        with mock.patch("utils.image_downloader.aiohttp.ClientSession", return_value=FakeSession(head, get_resp)):
            with mock.patch("utils.image_downloader.Image.open", return_value=DummyImage()):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "avatar.webp"
                    success, message = await download_and_validate_image(
                        "https://example.com/avatar.png",
                        path,
                        MAX_AVATAR_BYTES,
                    )
                    self.assertTrue(success)
                    self.assertEqual(message, "ok")
                    self.assertTrue(path.exists())

    async def test_rejects_invalid_image_bytes(self):
        head = FakeResponse(status=200, headers={"Content-Type": "image/png"})
        get_resp = FakeResponse(status=200, headers={}, data=b"fakebytes")

        with mock.patch("utils.image_downloader.aiohttp.ClientSession", return_value=FakeSession(head, get_resp)):
            with mock.patch("utils.image_downloader.Image.open", side_effect=Exception("bad")):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "avatar.webp"
                    success, message = await download_and_validate_image(
                        "https://example.com/avatar.png",
                        path,
                        MAX_AVATAR_BYTES,
                    )

        self.assertFalse(success)
        self.assertIn("valid image", message)
