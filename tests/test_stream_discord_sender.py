import asyncio
import sys
import types
from pathlib import Path
from unittest import mock

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

from utils.rate_limiter import StreamSendBudget
from utils.streaming.discord_sender import DiscordReplySession
from utils.streaming.types import DiscordSendPolicy


class FakeSentMessage:
    _next_id = 1000

    def __init__(self, content: str):
        FakeSentMessage._next_id += 1
        self.id = FakeSentMessage._next_id
        self.content = content
        self.author = type("Author", (), {"id": 999, "display_name": "Femmy"})()
        self.edits = []

    async def edit(self, *, content: str):
        self.content = content
        self.edits.append(content)
        return self


class FakeChannel:
    def __init__(self):
        self.sent_messages = []

    async def send(self, content: str, **kwargs):
        msg = FakeSentMessage(content)
        self.sent_messages.append(msg)
        return msg


class FakeSourceMessage:
    def __init__(self):
        self.channel = FakeChannel()
        self.replies = []

    async def reply(self, content: str, mention_author: bool = False, **kwargs):
        msg = FakeSentMessage(content)
        self.replies.append((content, mention_author, msg))
        return msg


class FakeWebhookContext:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls = []

    async def send(self, source_message, content: str):
        if self.should_fail:
            raise RuntimeError("webhook send failed")
        payload = {
            "content": content,
            "username": "Lilya",
            "avatar": b"avatar-bytes",
        }
        self.calls.append(payload)
        return FakeSentMessage(content)


def test_discord_reply_session_uses_reply_then_followups():
    async def _run():
        source = FakeSourceMessage()
        session = DiscordReplySession(
            source_message=source,
            send_policy=DiscordSendPolicy(),
            budget=StreamSendBudget(max_messages=5, max_total_chars=500, min_flush_chars=5, min_flush_interval=0.0),
        )
        await session.send_text("First chunk.")
        await session.send_text("Second chunk.")

        assert len(source.replies) == 1
        assert source.replies[0][0] == "First chunk."
        assert source.replies[0][1] is False
        assert [msg.content for msg in source.channel.sent_messages] == ["Second chunk."]

    asyncio.run(_run())


def test_discord_reply_session_appends_interruption_hint_to_visible_output():
    async def _run():
        source = FakeSourceMessage()
        session = DiscordReplySession(
            source_message=source,
            send_policy=DiscordSendPolicy(warmup_edit_window_seconds=30.0),
            budget=StreamSendBudget(max_messages=5, max_total_chars=500, min_flush_chars=5, min_flush_interval=0.0),
        )
        await session.send_text("Partial answer")
        await session.append_interruption_hint("Interrupted, ask me to continue.")

        sent_message = source.replies[0][2]
        assert sent_message.content.endswith("Interrupted, ask me to continue.")
        assert sent_message.edits

    asyncio.run(_run())


def test_discord_reply_session_respects_min_flush_interval():
    async def _run():
        source = FakeSourceMessage()
        session = DiscordReplySession(
            source_message=source,
            send_policy=DiscordSendPolicy(),
            budget=StreamSendBudget(
                max_messages=5,
                max_total_chars=500,
                min_flush_chars=5,
                min_flush_interval=0.5,
            ),
        )

        sleep_calls = []

        async def fake_sleep(delay):
            sleep_calls.append(delay)

        with mock.patch("utils.streaming.discord_sender.asyncio.sleep", new=fake_sleep):
            await session.send_text("First chunk.")
            await session.send_text("Second chunk.")

        assert sleep_calls
        assert sleep_calls[0] > 0

    asyncio.run(_run())


def test_discord_reply_session_uses_webhook_context_before_bot_reply():
    async def _run():
        source = FakeSourceMessage()
        webhook_context = FakeWebhookContext()
        session = DiscordReplySession(
            source_message=source,
            send_policy=DiscordSendPolicy(),
            budget=StreamSendBudget(max_messages=5, max_total_chars=500, min_flush_chars=5, min_flush_interval=0.0),
            webhook_context=webhook_context,
        )

        await session.send_text("Persona chunk.")

        assert source.replies == []
        assert [call["username"] for call in webhook_context.calls] == ["Lilya"]
        assert webhook_context.calls[0]["avatar"] == b"avatar-bytes"

    asyncio.run(_run())


def test_discord_reply_session_falls_back_to_bot_reply_when_webhook_fails():
    async def _run():
        source = FakeSourceMessage()
        session = DiscordReplySession(
            source_message=source,
            send_policy=DiscordSendPolicy(),
            budget=StreamSendBudget(max_messages=5, max_total_chars=500, min_flush_chars=5, min_flush_interval=0.0),
            webhook_context=FakeWebhookContext(should_fail=True),
        )

        await session.send_text("Fallback chunk.")

        assert len(source.replies) == 1
        assert source.replies[0][0] == "Fallback chunk."

    asyncio.run(_run())
