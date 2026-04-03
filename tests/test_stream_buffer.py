import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

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

from utils.streaming.buffer import SemanticBuffer


def test_semantic_buffer_flushes_at_sentence_boundary():
    buffer = SemanticBuffer(min_flush_chars=8, target_flush_chars=12, max_buffer_chars=48)
    buffer.add_text("Hello there. Another sentence")

    flushed = buffer.pop_flushable()

    assert flushed == "Hello there."
    assert buffer.pending_text == " Another sentence"


def test_semantic_buffer_holds_incomplete_markdown_link():
    buffer = SemanticBuffer(min_flush_chars=8, target_flush_chars=12, max_buffer_chars=48)
    buffer.add_text("See [the docs](https://example.com")

    assert buffer.pop_flushable() is None
    assert buffer.pending_text == "See [the docs](https://example.com"


def test_semantic_buffer_force_flush_closes_code_fence():
    buffer = SemanticBuffer(min_flush_chars=8, target_flush_chars=12, max_buffer_chars=48)
    buffer.add_text("```py\nprint('hi')")

    flushed = buffer.pop_flushable(force=True)

    assert flushed == "```py\nprint('hi')\n```"
    assert buffer.pending_text == ""
