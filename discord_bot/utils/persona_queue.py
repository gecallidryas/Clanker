from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


@dataclass(slots=True)
class PersonaInvocationJob:
    mode_key: str
    source_message: Any = None
    guild_config: dict[str, Any] = field(default_factory=dict)
    content_for_prompt: str = ""
    context_snapshot: str = ""
    media_refs: list[dict[str, Any]] | None = None


class PersonaQueueManager:
    def __init__(self) -> None:
        self._queues: dict[int, deque[PersonaInvocationJob]] = defaultdict(deque)
        self._active_channels: set[int] = set()
        self._tasks: dict[int, asyncio.Task] = {}

    async def enqueue(self, channel_id: int, job: PersonaInvocationJob) -> None:
        self._queues[channel_id].append(job)

    async def drain(
        self,
        channel_id: int,
        runner: Callable[[PersonaInvocationJob], Awaitable[None]],
    ) -> None:
        if channel_id in self._active_channels:
            return
        self._active_channels.add(channel_id)
        try:
            queue = self._queues[channel_id]
            while queue:
                job = queue.popleft()
                await runner(job)
        finally:
            self._active_channels.discard(channel_id)
            self._tasks.pop(channel_id, None)
            if not self._queues[channel_id]:
                self._queues.pop(channel_id, None)

    def schedule_drain(
        self,
        channel_id: int,
        runner: Callable[[PersonaInvocationJob], Awaitable[None]],
    ) -> Optional[asyncio.Task]:
        if channel_id in self._active_channels or not self._queues.get(channel_id):
            return None
        task = asyncio.create_task(self.drain(channel_id, runner))
        self._tasks[channel_id] = task
        return task
