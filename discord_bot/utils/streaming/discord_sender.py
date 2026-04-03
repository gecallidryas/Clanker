from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from utils.rate_limiter import StreamSendBudget

from .chunker import split_stream_text
from .types import DiscordSendPolicy


class DiscordReplySession:
    def __init__(
        self,
        *,
        source_message: Any,
        send_policy: Optional[DiscordSendPolicy] = None,
        budget: Optional[StreamSendBudget] = None,
        webhook_context: Optional[Any] = None,
    ) -> None:
        self.source_message = source_message
        self.send_policy = send_policy or DiscordSendPolicy()
        self.budget = budget or StreamSendBudget()
        self.webhook_context = webhook_context
        self.first_message = None
        self.last_message = None
        self.visible_text_parts: list[str] = []
        self._last_send_at: Optional[float] = None
        self._truncation_notice_sent = False
        self._webhook_failed = False

    @property
    def has_visible_output(self) -> bool:
        return bool(self.visible_text_parts)

    @property
    def visible_text(self) -> str:
        return "".join(self.visible_text_parts)

    async def send_text(self, text: str) -> None:
        for chunk in split_stream_text(text, limit=self.send_policy.chunk_limit):
            if not chunk:
                continue
            if not self.budget.can_send(len(chunk)):
                await self._send_truncation_notice()
                return
            if self._last_send_at is not None and self.budget.min_flush_interval > 0:
                elapsed = time.monotonic() - self._last_send_at
                remaining = self.budget.min_flush_interval - elapsed
                if remaining > 0:
                    await asyncio.sleep(remaining)
            message = await self._send_chunk(chunk)
            self.last_message = message
            self.visible_text_parts.append(chunk)
            self.budget.record_send(len(chunk))
            self._last_send_at = time.monotonic()

    async def append_interruption_hint(self, text: str) -> None:
        if not text or self.last_message is None:
            return
        separator = "" if self.last_message.content.endswith((" ", "\n")) else " "
        new_content = f"{self.last_message.content}{separator}{text}"
        if (
            len(new_content) <= self.send_policy.chunk_limit
            and self._last_send_at is not None
            and (time.monotonic() - self._last_send_at) <= self.send_policy.warmup_edit_window_seconds
        ):
            await self.last_message.edit(content=new_content)
            if self.visible_text_parts:
                self.visible_text_parts[-1] = new_content
            return
        await self.send_text(text)

    async def _send_truncation_notice(self) -> None:
        if self._truncation_notice_sent:
            return
        self._truncation_notice_sent = True
        if self.last_message and not self.has_visible_output:
            await self.append_interruption_hint(self.send_policy.truncation_notice)
            return
        self.last_message = await self._send_chunk(self.send_policy.truncation_notice)
        self.visible_text_parts.append(self.send_policy.truncation_notice)

    async def _send_chunk(self, chunk: str):
        if self.webhook_context is not None and not self._webhook_failed:
            try:
                message = await self.webhook_context.send(self.source_message, chunk)
                if self.first_message is None:
                    self.first_message = message
                return message
            except Exception:
                self._webhook_failed = True

        if self.first_message is None:
            message = await self.source_message.reply(chunk, mention_author=False)
            self.first_message = message
            return message
        return await self.source_message.channel.send(chunk)
