import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.webhook_identity import (
    ChannelWebhookIdentityManager,
    PersonaWebhookContext,
    PersonaWebhookIdentity,
)


class FakeWebhook:
    def __init__(self, name: str):
        self.name = name
        self.calls = []

    async def send(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs


class FakeChannel:
    def __init__(self):
        self.id = 42
        self.created = []
        self._existing = []

    async def webhooks(self):
        return list(self._existing)

    async def create_webhook(self, *, name: str):
        webhook = FakeWebhook(name)
        self.created.append(webhook)
        self._existing.append(webhook)
        return webhook


class FakeSourceMessage:
    def __init__(self, channel):
        self.channel = channel


def test_persona_webhook_context_sends_with_username_and_avatar():
    async def _run():
        manager = ChannelWebhookIdentityManager()
        channel = FakeChannel()
        context = PersonaWebhookContext(
            manager=manager,
            identity=PersonaWebhookIdentity(username="Lilya", avatar_bytes=b"avatar"),
        )

        await context.send(FakeSourceMessage(channel), "hello")

        sent = channel.created[0].calls[0]
        assert sent["content"] == "hello"
        assert sent["username"] == "Lilya"
        assert sent["avatar"] == b"avatar"
        assert sent["wait"] is True

    asyncio.run(_run())


def test_channel_webhook_manager_reuses_cached_webhook():
    async def _run():
        manager = ChannelWebhookIdentityManager()
        channel = FakeChannel()

        first = await manager.get_or_create(channel)
        second = await manager.get_or_create(channel)

        assert first is second
        assert len(channel.created) == 1

    asyncio.run(_run())
