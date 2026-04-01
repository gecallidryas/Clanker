from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


class FakeMessage:
    def __init__(self) -> None:
        self.edits: list[dict[str, Any]] = []

    async def edit(self, **kwargs: Any) -> None:
        self.edits.append(kwargs)


class FakeResponse:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.edits: list[dict[str, Any]] = []
        self.modal: Any = None
        self.deferred = False

    async def send_message(self, *args: Any, **kwargs: Any) -> None:
        payload = dict(kwargs)
        if args:
            payload["content"] = args[0]
        self.messages.append(payload)

    async def edit_message(self, **kwargs: Any) -> None:
        self.edits.append(kwargs)

    async def send_modal(self, modal: Any) -> None:
        self.modal = modal

    async def defer(self, **kwargs: Any) -> None:
        self.deferred = True
        self.messages.append({"deferred": True, **kwargs})


class FakeFollowup:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send(self, *args: Any, **kwargs: Any) -> None:
        payload = dict(kwargs)
        if args:
            payload["content"] = args[0]
        self.messages.append(payload)


@dataclass
class FakeGuild:
    id: int = 1
    name: str = "Test Guild"
    channels: dict[int, Any] = field(default_factory=dict)
    roles: dict[int, Any] = field(default_factory=dict)

    def get_channel(self, channel_id: int) -> Any:
        return self.channels.get(channel_id)

    def get_role(self, role_id: int) -> Any:
        return self.roles.get(role_id)


@dataclass
class FakeUser:
    id: int
    guild_permissions: Any = field(
        default_factory=lambda: SimpleNamespace(manage_guild=True, administrator=True)
    )

    def __str__(self) -> str:
        return f"FakeUser({self.id})"


class FakeInteraction:
    def __init__(
        self,
        *,
        user_id: int = 1,
        guild: FakeGuild | None = None,
        locale: str = "en-US",
    ) -> None:
        self.user = FakeUser(user_id)
        self.guild = guild or FakeGuild()
        self.guild_id = self.guild.id if self.guild else None
        self.locale = locale
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.message = FakeMessage()
        self.channel_id = 999
