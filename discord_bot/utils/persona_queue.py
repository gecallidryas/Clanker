from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


class PersonaQueueAbortedError(RuntimeError):
    """Raised for queued persona jobs that are dropped after a prior failure or shutdown."""


@dataclass(slots=True)
class PersonaInvocationJob:
    mode_key: str
    source_message: Any = None
    guild_config: dict[str, Any] = field(default_factory=dict)
    content_for_prompt: str = ""
    context_snapshot: str = ""
    media_refs: list[dict[str, Any]] | None = None
    completion_future: asyncio.Future[None] | None = None


class PersonaQueueManager:
    def __init__(self) -> None:
        self._queues: dict[int, deque[PersonaInvocationJob]] = defaultdict(deque)
        self._active_channels: set[int] = set()
        self._tasks: dict[int, asyncio.Task] = {}

    async def enqueue(self, channel_id: int, job: PersonaInvocationJob) -> None:
        self._queues[channel_id].append(job)

    def _set_job_completion_exception(self, job: PersonaInvocationJob, exc: BaseException) -> None:
        if job.completion_future is not None and not job.completion_future.done():
            job.completion_future.set_exception(exc)

    def _abort_queued_jobs(self, queue: deque[PersonaInvocationJob], reason: str) -> None:
        while queue:
            job = queue.popleft()
            self._set_job_completion_exception(job, PersonaQueueAbortedError(reason))

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
                try:
                    await runner(job)
                except BaseException as exc:
                    self._set_job_completion_exception(job, exc)
                    self._abort_queued_jobs(
                        queue,
                        f"Persona queue aborted in channel {channel_id} after a prior job failed.",
                    )
                    raise
                else:
                    if job.completion_future is not None and not job.completion_future.done():
                        job.completion_future.set_result(None)
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

    def cancel_all(self) -> None:
        for task in list(self._tasks.values()):
            if not task.done():
                task.cancel()
        for channel_id, queue in list(self._queues.items()):
            self._abort_queued_jobs(
                queue,
                f"Persona queue cancelled for channel {channel_id}.",
            )
        self._queues.clear()
        self._tasks.clear()
        self._active_channels.clear()
