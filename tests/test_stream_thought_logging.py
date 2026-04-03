import asyncio
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

from utils.streaming.thought_logger import ThoughtLogger
from utils.streaming.types import ThoughtLogSettings


class FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.messages = []
        self.mention = f"<#{channel_id}>"

    async def send(self, content: str, **kwargs):
        self.messages.append(content)


class FakeGuild:
    def __init__(self, channels):
        self._channels = {channel.id: channel for channel in channels}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


def test_thought_logger_prefers_dedicated_channel():
    async def _run():
        thought_channel = FakeChannel(10)
        mod_channel = FakeChannel(20)
        guild = FakeGuild([thought_channel, mod_channel])
        logger = ThoughtLogger(
            guild=guild,
            settings=ThoughtLogSettings(level="summary", channel_id=10, allow_mod_log_reuse=False, mod_log_channel_id=20),
        )

        await logger.log_summary("provider=gemini", "summary text")

        assert thought_channel.messages
        assert not mod_channel.messages

    asyncio.run(_run())


def test_thought_logger_reuses_mod_log_only_when_explicitly_allowed():
    async def _run():
        mod_channel = FakeChannel(20)
        guild = FakeGuild([mod_channel])
        logger = ThoughtLogger(
            guild=guild,
            settings=ThoughtLogSettings(level="summary", channel_id=None, allow_mod_log_reuse=True, mod_log_channel_id=20),
        )

        await logger.log_summary("provider=gemini", "summary text")

        assert mod_channel.messages

    asyncio.run(_run())
