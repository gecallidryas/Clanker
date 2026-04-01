from __future__ import annotations

import asyncio
from typing import Any, AsyncIterable, Callable, Optional

from .buffer import SemanticBuffer
from .types import StreamEvent, StreamResult


class StreamOrchestrator:
    INTERRUPTION_FINISH_REASONS = {
        "length",
        "max_tokens",
        "content_filter",
        "cancelled",
        "error",
        "timeout",
        "incomplete",
    }

    def __init__(
        self,
        *,
        sender: Any,
        interruption_hint: str,
        text_transform: Optional[Callable[[str], str]] = None,
        buffer: Optional[SemanticBuffer] = None,
        stall_timeout_seconds: Optional[float] = None,
    ) -> None:
        self.sender = sender
        self.interruption_hint = interruption_hint
        self.text_transform = text_transform
        self.buffer = buffer or SemanticBuffer()
        self.stall_timeout_seconds = stall_timeout_seconds
        self._raw_text = ""
        self._reasoning_text = ""
        self._visible_segments: list[str] = []
        self._visible_cursor = 0

    async def run(self, events: AsyncIterable[StreamEvent]) -> StreamResult:
        iterator = events.__aiter__()
        next_event_task: Optional[asyncio.Task] = None
        try:
            while True:
                try:
                    if next_event_task is None:
                        next_event_task = asyncio.create_task(iterator.__anext__())
                    if self.stall_timeout_seconds and self.buffer.has_meaningful_text():
                        event = await asyncio.wait_for(
                            asyncio.shield(next_event_task),
                            timeout=self.stall_timeout_seconds,
                        )
                    else:
                        event = await next_event_task
                    next_event_task = None
                except asyncio.TimeoutError:
                    await self._flush_stalled()
                    continue
                except StopAsyncIteration:
                    break

                if event.type == "text_delta":
                    await self._on_text_delta(event.text or "")
                    continue
                if event.type == "reasoning_delta":
                    self._reasoning_text += event.text or ""
                    continue
                if event.type == "tool_call":
                    await self._flush(force=True)
                    return self._result(finish_reason="tool_call", tool_call=event.data)
                if event.type == "provider_error":
                    return await self._finish_with_interruption("error")
                if event.type == "moderation_stop":
                    return await self._finish_with_interruption(event.finish_reason or "moderation_stop")
                if event.type == "done":
                    if (event.finish_reason or "stop") in self.INTERRUPTION_FINISH_REASONS:
                        return await self._finish_with_interruption(event.finish_reason or "stop")
                    await self._flush(force=True)
                    return self._result(finish_reason=event.finish_reason or "stop")
        except Exception:
            if next_event_task is not None:
                next_event_task.cancel()
            return await self._finish_with_interruption("error")
        finally:
            if next_event_task is not None and not next_event_task.done():
                next_event_task.cancel()

        await self._flush(force=True)
        return self._result(finish_reason="stop")

    async def _on_text_delta(self, text: str) -> None:
        if not text:
            return
        self._raw_text += text
        visible_increment = self._extract_visible_increment()
        if visible_increment:
            self.buffer.add_text(visible_increment)
        await self._flush(force=False)

    def _extract_visible_increment(self) -> str:
        hidden_index = self._find_hidden_marker(self._raw_text)
        visible_limit = len(self._raw_text) if hidden_index < 0 else hidden_index
        if visible_limit <= self._visible_cursor:
            return ""
        increment = self._raw_text[self._visible_cursor : visible_limit]
        self._visible_cursor = visible_limit
        return increment

    def _find_hidden_marker(self, text: str) -> int:
        markers = ("```tool", "```admin_action")
        indexes = [text.find(marker) for marker in markers if text.find(marker) >= 0]
        return min(indexes) if indexes else -1

    async def _flush(self, *, force: bool) -> None:
        while True:
            flushed = self.buffer.pop_flushable(force=force)
            if not flushed:
                return
            transformed = self.text_transform(flushed) if self.text_transform else flushed
            if not transformed:
                if not force:
                    return
                continue
            await self.sender.send_text(transformed)
            self._visible_segments.append(transformed)
            if force:
                continue

    async def _flush_stalled(self) -> None:
        stalled = self.buffer.pop_stalled()
        if not stalled:
            return
        transformed = self.text_transform(stalled) if self.text_transform else stalled
        if not transformed:
            return
        await self.sender.send_text(transformed)
        self._visible_segments.append(transformed)

    async def _finish_with_interruption(self, finish_reason: str) -> StreamResult:
        await self._flush(force=True)
        if self._has_meaningful_visible_output():
            await self.sender.append_interruption_hint(self.interruption_hint)
            return self._result(finish_reason=finish_reason, partial=True, should_fallback=False)
        return self._result(finish_reason=finish_reason, partial=False, should_fallback=True)

    def _has_meaningful_visible_output(self) -> bool:
        return any(any(char.isalnum() for char in segment) for segment in self._visible_segments)

    def _result(
        self,
        *,
        finish_reason: str,
        partial: bool = False,
        should_fallback: bool = False,
        tool_call: Optional[dict[str, Any]] = None,
    ) -> StreamResult:
        return StreamResult(
            visible_text="".join(self._visible_segments),
            raw_text=self._raw_text,
            reasoning_text=self._reasoning_text,
            finish_reason=finish_reason,
            partial=partial,
            should_fallback=should_fallback,
            tool_call=tool_call,
        )
