import asyncio

from utils.tenor_resolver import resolve_tenor_url


def test_resolve_tenor_url_from_gif_json():
    html = """
    <html><body>
      <script id="gif-json">
      {"media_formats":{"gif":{"url":"https://media.tenor.com/abc.gif"}}}
      </script>
    </body></html>
    """

    async def _fetch(_url: str):
        return html

    resolved = asyncio.run(
        resolve_tenor_url("https://tenor.com/view/example-gif-123", fetch_html=_fetch)
    )
    assert resolved == "https://media.tenor.com/abc.gif"


def test_resolve_tenor_url_regex_fallback():
    html = """
    https://media.tenor.com/example-file.gif
    https://media.tenor.com/other-file.mp4
    """

    async def _fetch(_url: str):
        return html

    resolved = asyncio.run(
        resolve_tenor_url("https://tenor.com/view/example-file-gif-123", fetch_html=_fetch)
    )
    assert resolved == "https://media.tenor.com/example-file.gif"


def test_resolve_tenor_url_passthrough_for_non_view_urls():
    url = "https://example.com/file.gif"
    resolved = asyncio.run(resolve_tenor_url(url))
    assert resolved == url
