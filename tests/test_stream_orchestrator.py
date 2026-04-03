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

from utils.streaming.orchestrator import StreamOrchestrator
from utils.streaming.types import StreamEvent


class FakeSender:
    def __init__(self):
        self.sent = []
        self.hints = []
        self.sent_event = asyncio.Event()

    async def send_text(self, text: str) -> None:
        self.sent.append(text)
        self.sent_event.set()

    async def append_interruption_hint(self, text: str) -> None:
        self.hints.append(text)


async def _collect(events):
    for item in events:
        yield item


def test_orchestrator_appends_hint_after_partial_error():
    async def _run():
        sender = FakeSender()
        orchestrator = StreamOrchestrator(sender=sender, interruption_hint="Interrupted, ask me to continue.")
        events = [
            StreamEvent.text_delta("Hello there. "),
            StreamEvent.provider_error("network broke"),
        ]

        result = await orchestrator.run(_collect(events))

        assert sender.sent == ["Hello there."]
        assert sender.hints == ["Interrupted, ask me to continue."]
        assert result.partial is True
        assert result.should_fallback is False
        assert result.finish_reason == "error"

    asyncio.run(_run())


def test_orchestrator_requests_fallback_when_no_visible_text_was_sent():
    async def _run():
        sender = FakeSender()
        orchestrator = StreamOrchestrator(sender=sender, interruption_hint="Interrupted, ask me to continue.")
        events = [
            StreamEvent.provider_error("network broke"),
        ]

        result = await orchestrator.run(_collect(events))

        assert sender.sent == []
        assert sender.hints == []
        assert result.partial is False
        assert result.should_fallback is True
        assert result.finish_reason == "error"

    asyncio.run(_run())


def test_orchestrator_flushes_before_tool_call():
    async def _run():
        sender = FakeSender()
        orchestrator = StreamOrchestrator(sender=sender, interruption_hint="Interrupted, ask me to continue.")
        events = [
            StreamEvent.text_delta("Let me check that.\n"),
            StreamEvent.tool_call({"name": "lookup", "arguments": {"q": "x"}}),
        ]

        result = await orchestrator.run(_collect(events))

        assert sender.sent == ["Let me check that."]
        assert result.tool_call == {"name": "lookup", "arguments": {"q": "x"}}
        assert result.finish_reason == "tool_call"

    asyncio.run(_run())


def test_orchestrator_treats_length_done_as_interruption():
    async def _run():
        sender = FakeSender()
        orchestrator = StreamOrchestrator(sender=sender, interruption_hint="Interrupted, ask me to continue.")
        events = [
            StreamEvent.text_delta("Almost done."),
            StreamEvent.done(finish_reason="length"),
        ]

        result = await orchestrator.run(_collect(events))

        assert sender.sent == ["Almost done."]
        assert sender.hints == ["Interrupted, ask me to continue."]
        assert result.partial is True
        assert result.finish_reason == "length"

    asyncio.run(_run())


def test_orchestrator_stall_flushes_pending_text_before_done():
    async def _run():
        sender = FakeSender()
        orchestrator = StreamOrchestrator(
            sender=sender,
            interruption_hint="Interrupted, ask me to continue.",
            stall_timeout_seconds=0.05,
        )

        gate = asyncio.Event()

        async def events():
            yield StreamEvent.text_delta("This is buffered text without punctuation")
            await asyncio.sleep(0.2)
            await gate.wait()
            yield StreamEvent.done()

        task = asyncio.create_task(orchestrator.run(events()))
        await asyncio.wait_for(sender.sent_event.wait(), timeout=0.2)
        gate.set()
        result = await task

        assert sender.sent == ["This is buffered text without punctuation"]
        assert result.finish_reason == "stop"

    asyncio.run(_run())
