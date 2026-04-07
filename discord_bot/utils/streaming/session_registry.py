from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager


class ChannelStreamBusyError(RuntimeError):
    """Raised when a channel already has an active AI stream."""


class ChannelStreamRegistry:
    def __init__(self) -> None:
        self._active: dict[tuple[int, int], str] = {}
        self._lock = asyncio.Lock()

    def _key(self, channel_id: int, user_id: int) -> tuple[int, int]:
        return (channel_id, user_id)

    async def acquire(self, channel_id: int, user_id: int) -> str:
        key = self._key(channel_id, user_id)
        async with self._lock:
            if key in self._active:
                raise ChannelStreamBusyError(
                    f"Channel {channel_id} already has an active stream for user {user_id}."
                )
            token = uuid.uuid4().hex
            self._active[key] = token
            return token

    async def release(self, channel_id: int, user_id: int, token: str) -> None:
        key = self._key(channel_id, user_id)
        async with self._lock:
            if self._active.get(key) == token:
                self._active.pop(key, None)

    def is_active(self, channel_id: int, user_id: int) -> bool:
        return self._key(channel_id, user_id) in self._active

    @asynccontextmanager
    async def claim(self, channel_id: int, user_id: int):
        token = await self.acquire(channel_id, user_id)
        try:
            yield token
        finally:
            await self.release(channel_id, user_id, token)
