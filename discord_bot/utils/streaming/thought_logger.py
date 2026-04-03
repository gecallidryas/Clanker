from __future__ import annotations

import re
from typing import Any, Optional

from .types import ThoughtLogSettings

_URL_RE = re.compile(r"https?://\S+")


class ThoughtLogger:
    def __init__(self, *, guild: Any, settings: ThoughtLogSettings) -> None:
        self.guild = guild
        self.settings = settings

    async def log_summary(self, metadata: str, summary: str) -> bool:
        if (self.settings.level or "off").lower() == "off":
            return False
        channel = self._resolve_channel()
        if channel is None:
            return False
        payload = self._sanitize(summary)
        content = f"[AI Thought Log]\n{metadata}\n{payload}".strip()
        await channel.send(content, allowed_mentions=None)
        return True

    def _resolve_channel(self) -> Optional[Any]:
        if self.settings.channel_id:
            channel = self.guild.get_channel(self.settings.channel_id)
            if channel is not None:
                return channel
        if self.settings.allow_mod_log_reuse and self.settings.mod_log_channel_id:
            return self.guild.get_channel(self.settings.mod_log_channel_id)
        return None

    def _sanitize(self, text: str) -> str:
        cleaned = text or ""
        if self.settings.sanitize_mentions:
            cleaned = cleaned.replace("@", "@\u200b")
        if self.settings.sanitize_urls:
            cleaned = _URL_RE.sub("[url]", cleaned)
        return cleaned
