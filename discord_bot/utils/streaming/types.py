from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class TurnRequest:
    guild_id: int
    channel_id: int
    user_id: int
    prompt: str
    source_message: Any
    system_instruction: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    guild_config: dict[str, Any] = field(default_factory=dict)
    provider_preference: Optional[str] = None
    enabled_tools: list[dict[str, Any]] = field(default_factory=list)
    media_context: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ProviderFeatures:
    openai_compatible: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_video: bool = False
    text_only: bool = True


@dataclass(slots=True)
class DiscordSendPolicy:
    chunk_limit: int = 1900
    warmup_edit_window_seconds: float = 2.0
    interruption_hint: str = "Interrupted, ask me to continue."
    truncation_notice: str = "Reply truncated, ask me to continue."


@dataclass(slots=True)
class ThoughtLogSettings:
    level: str = "off"
    channel_id: Optional[int] = None
    allow_mod_log_reuse: bool = False
    mod_log_channel_id: Optional[int] = None
    include_prompt: bool = False
    sanitize_mentions: bool = True
    sanitize_urls: bool = True


@dataclass(slots=True)
class StreamEvent:
    type: str
    text: Optional[str] = None
    data: Any = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def text_delta(cls, text: str) -> "StreamEvent":
        return cls(type="text_delta", text=text)

    @classmethod
    def reasoning_delta(cls, text: str) -> "StreamEvent":
        return cls(type="reasoning_delta", text=text)

    @classmethod
    def tool_call(cls, data: dict[str, Any]) -> "StreamEvent":
        return cls(type="tool_call", data=data)

    @classmethod
    def provider_error(cls, error: str) -> "StreamEvent":
        return cls(type="provider_error", error=error)

    @classmethod
    def moderation_stop(cls, reason: str = "moderation_stop") -> "StreamEvent":
        return cls(type="moderation_stop", finish_reason=reason)

    @classmethod
    def done(cls, finish_reason: str = "stop") -> "StreamEvent":
        return cls(type="done", finish_reason=finish_reason)


@dataclass(slots=True)
class StreamResult:
    visible_text: str = ""
    raw_text: str = ""
    reasoning_text: str = ""
    finish_reason: str = "stop"
    partial: bool = False
    should_fallback: bool = False
    tool_call: Optional[dict[str, Any]] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
