from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager


class ChannelStreamBusyError(RuntimeError):
    """Raised when a channel already has an active AI stream."""


class ChannelStreamRegistry:
    def __init__(self) -> None:
        self._active: dict[int, str] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, channel_id: int) -> str:
        async with self._lock:
            if channel_id in self._active:
                raise ChannelStreamBusyError(f"Channel {channel_id} already has an active stream.")
            token = uuid.uuid4().hex
            self._active[channel_id] = token
            return token

    async def release(self, channel_id: int, token: str) -> None:
        async with self._lock:
            if self._active.get(channel_id) == token:
                self._active.pop(channel_id, None)

    def is_active(self, channel_id: int) -> bool:
        return channel_id in self._active

    @asynccontextmanager
    async def claim(self, channel_id: int):
        token = await self.acquire(channel_id)
        try:
            yield token
        finally:
            await self.release(channel_id, token)
