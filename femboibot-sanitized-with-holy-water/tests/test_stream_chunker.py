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

from utils.streaming.chunker import split_stream_text


def test_split_stream_text_respects_limit_for_plain_text():
    text = "a" * 140

    parts = split_stream_text(text, limit=50)

    assert "".join(parts) == text
    assert all(len(part) <= 50 for part in parts)


def test_split_stream_text_balances_code_fences():
    text = "```python\n" + ("print('x')\n" * 20)

    parts = split_stream_text(text, limit=80)

    assert all(len(part) <= 80 for part in parts)
    assert all(part.count("```") % 2 == 0 for part in parts)
