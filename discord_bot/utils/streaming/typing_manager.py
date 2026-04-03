from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any, Optional


class TypingKeepalive:
    def __init__(self, channel: Any, *, interval_seconds: float = 7.0) -> None:
        self.channel = channel
        self.interval_seconds = max(1.0, float(interval_seconds))
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def __aenter__(self) -> "TypingKeepalive":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                async with self.channel.typing():
                    await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue
