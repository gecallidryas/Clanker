import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub

if "pytz" not in sys.modules:
    pytz_stub = types.ModuleType("pytz")
    pytz_stub.UnknownTimeZoneError = Exception
    pytz_stub.timezone = lambda _name: None
    sys.modules["pytz"] = pytz_stub

if "aiosqlite" not in sys.modules:
    aiosqlite_stub = types.ModuleType("aiosqlite")

    class _Connection:
        pass

    async def _connect(*args, **kwargs):
        raise RuntimeError("aiosqlite stub should not be used in this test")

    aiosqlite_stub.Connection = _Connection
    aiosqlite_stub.Row = object
    aiosqlite_stub.connect = _connect
    sys.modules["aiosqlite"] = aiosqlite_stub

from cogs.ai_brain import _is_processing_ack_response  # noqa: E402


def test_processing_ack_detects_interim_request_message():
    text = "I am processing the request for news regarding maneaters in Buffalo, New York."
    assert _is_processing_ack_response(text) is True


def test_processing_ack_ignores_substantive_result_messages():
    text = (
        "I found 5 results about maneaters in Buffalo. "
        "Top source says the incident happened near Delaware Park."
    )
    assert _is_processing_ack_response(text) is False


def test_processing_ack_ignores_messages_with_links():
    text = "I'm processing this now: https://example.com/article"
    assert _is_processing_ack_response(text) is False
