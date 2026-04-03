from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from modes import get_mode_profile
from utils.db_handler import get_custom_persona_by_mode_key
from utils.server_avatar import EVIL_MODE_AVATAR_FILES, MODE_AVATAR_FILES

DEFAULT_PERSONA_WEBHOOK_NAME = "Femmy Persona Relay"


@dataclass(slots=True)
class PersonaWebhookIdentity:
    username: str
    avatar_bytes: Optional[bytes] = None


@dataclass(slots=True)
class PersonaWebhookContext:
    manager: "ChannelWebhookIdentityManager"
    identity: PersonaWebhookIdentity

    async def send(self, source_message: Any, content: str):
        return await self.manager.send_as_persona(
            source_message=source_message,
            content=content,
            username=self.identity.username,
            avatar_bytes=self.identity.avatar_bytes,
        )


class ChannelWebhookIdentityManager:
    def __init__(self, *, webhook_name: str = DEFAULT_PERSONA_WEBHOOK_NAME) -> None:
        self.webhook_name = webhook_name
        self._cache: dict[int, Any] = {}

    async def get_or_create(self, channel: Any):
        target_channel = self._resolve_webhook_channel(channel)
        cache_key = int(getattr(target_channel, "id", 0) or id(target_channel))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if hasattr(target_channel, "webhooks"):
            existing = await target_channel.webhooks()
            for webhook in existing:
                if getattr(webhook, "name", None) == self.webhook_name:
                    self._cache[cache_key] = webhook
                    return webhook

        webhook = await target_channel.create_webhook(name=self.webhook_name)
        self._cache[cache_key] = webhook
        return webhook

    async def send_as_persona(
        self,
        *,
        source_message: Any,
        content: str,
        username: str,
        avatar_bytes: Optional[bytes] = None,
    ):
        webhook = await self.get_or_create(source_message.channel)
        send_kwargs = {
            "content": content,
            "username": username,
            "wait": True,
        }
        if avatar_bytes is not None:
            send_kwargs["avatar"] = avatar_bytes
        thread = self._resolve_thread_target(source_message.channel)
        if thread is not None:
            send_kwargs["thread"] = thread
        return await webhook.send(**send_kwargs)

    def _resolve_webhook_channel(self, channel: Any):
        parent = getattr(channel, "parent", None)
        if parent is not None and hasattr(parent, "create_webhook"):
            return parent
        return channel

    def _resolve_thread_target(self, channel: Any):
        return channel if getattr(channel, "parent", None) is not None else None


def _read_avatar_bytes(path: Optional[Path]) -> Optional[bytes]:
    if not path or not path.exists():
        return None
    return path.read_bytes()


async def build_persona_webhook_context(
    guild_id: int,
    mode_key: str,
    *,
    evil_mode: bool = False,
    manager: Optional[ChannelWebhookIdentityManager] = None,
) -> PersonaWebhookContext:
    identity = await resolve_persona_webhook_identity(guild_id, mode_key, evil_mode=evil_mode)
    return PersonaWebhookContext(
        manager=manager or ChannelWebhookIdentityManager(),
        identity=identity,
    )


async def resolve_persona_webhook_identity(
    guild_id: int,
    mode_key: str,
    *,
    evil_mode: bool = False,
) -> PersonaWebhookIdentity:
    if mode_key.startswith("custom_"):
        persona = await get_custom_persona_by_mode_key(guild_id, mode_key)
        if persona:
            avatar_bytes = _read_avatar_bytes(
                Path(persona["avatar_path"]) if persona.get("avatar_path") else None
            )
            return PersonaWebhookIdentity(
                username=str(persona.get("name") or mode_key),
                avatar_bytes=avatar_bytes,
            )

    profile = get_mode_profile(mode_key)
    avatar_path = MODE_AVATAR_FILES.get(mode_key)
    if evil_mode:
        avatar_path = EVIL_MODE_AVATAR_FILES.get(mode_key, avatar_path)
    return PersonaWebhookIdentity(
        username=profile.display_name,
        avatar_bytes=_read_avatar_bytes(avatar_path),
    )
