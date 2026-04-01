from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class ShortTermMessage:
    role: str
    content: str
    timestamp: datetime


@dataclass
class ShortTermMemoryEntry:
    user_id: int
    channel_id: int
    server_id: int
    messages: List[ShortTermMessage] = field(default_factory=list)
    summary: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)


_CONVERSATION_TTL_HOURS = int(os.getenv("SHORT_TERM_MEMORY_TTL_HOURS", "12"))
_SUMMARY_TTL_HOURS = int(os.getenv("SHORT_TERM_MEMORY_SUMMARY_TTL_HOURS", "24"))
_MAX_MESSAGES = int(os.getenv("SHORT_TERM_MEMORY_MAX_MESSAGES_PER_CHANNEL", "10"))
_MAX_SUMMARY_LENGTH = int(os.getenv("SHORT_TERM_MEMORY_MAX_SUMMARY_LENGTH", "1500"))

_cache: Dict[tuple[int, int], ShortTermMemoryEntry] = {}
_guild_summary_cache: Dict[int, ShortTermMemoryEntry] = {}


def _is_expired(entry: ShortTermMemoryEntry) -> bool:
    ttl_hours = _SUMMARY_TTL_HOURS if entry.summary else _CONVERSATION_TTL_HOURS
    return datetime.now() - entry.last_updated > timedelta(hours=ttl_hours)


def store_short_term_memory(
    user_id: int,
    channel_id: int,
    server_id: int,
    messages: List[ShortTermMessage],
) -> None:
    key = (user_id, channel_id)
    existing = _cache.get(key)
    summary = existing.summary if existing else None
    _cache[key] = ShortTermMemoryEntry(
        user_id=user_id,
        channel_id=channel_id,
        server_id=server_id,
        messages=messages[-_MAX_MESSAGES:],
        summary=summary,
        last_updated=datetime.now(),
    )


def update_short_term_memory_summary(user_id: int, channel_id: int, summary: str) -> None:
    key = (user_id, channel_id)
    entry = _cache.get(key)
    if not entry:
        return
    entry.summary = (summary or "").strip()[:_MAX_SUMMARY_LENGTH]
    entry.last_updated = datetime.now()


def get_short_term_memory_for_channel(user_id: int, channel_id: int) -> Optional[ShortTermMemoryEntry]:
    key = (user_id, channel_id)
    entry = _cache.get(key)
    if not entry:
        return None
    if _is_expired(entry):
        _cache.pop(key, None)
        return None
    return entry


def get_short_term_memories_for_user(
    user_id: int,
    exclude_channel_id: Optional[int] = None,
) -> List[ShortTermMemoryEntry]:
    results: List[ShortTermMemoryEntry] = []
    for (uid, channel_id), entry in list(_cache.items()):
        if uid != user_id:
            continue
        if exclude_channel_id is not None and channel_id == exclude_channel_id:
            continue
        if _is_expired(entry):
            _cache.pop((uid, channel_id), None)
            continue
        results.append(entry)
    results.sort(key=lambda item: item.last_updated, reverse=True)
    return results


def store_guild_recency_summary(server_id: int, summary: str) -> None:
    _guild_summary_cache[server_id] = ShortTermMemoryEntry(
        user_id=0,
        channel_id=0,
        server_id=server_id,
        messages=[],
        summary=(summary or "").strip()[:_MAX_SUMMARY_LENGTH] or None,
        last_updated=datetime.now(),
    )


def get_guild_recency_summary(server_id: int) -> Optional[str]:
    entry = _guild_summary_cache.get(server_id)
    if not entry:
        return None
    if _is_expired(entry):
        _guild_summary_cache.pop(server_id, None)
        return None
    return entry.summary


def clear_guild_recency_summary(server_id: int) -> bool:
    return _guild_summary_cache.pop(server_id, None) is not None


def clear_short_term_memory_for_channel(channel_id: int) -> int:
    removed = 0
    for key, entry in list(_cache.items()):
        if entry.channel_id == channel_id:
            _cache.pop(key, None)
            removed += 1
    return removed


def clear_short_term_memory_for_user(user_id: int) -> int:
    removed = 0
    for key in list(_cache.keys()):
        if key[0] == user_id:
            _cache.pop(key, None)
            removed += 1
    return removed


def clear_expired_entries() -> int:
    removed = 0
    for key, entry in list(_cache.items()):
        if _is_expired(entry):
            _cache.pop(key, None)
            removed += 1
    for key, entry in list(_guild_summary_cache.items()):
        if _is_expired(entry):
            _guild_summary_cache.pop(key, None)
            removed += 1
    return removed


def get_short_term_memory_cache_stats() -> dict[str, int]:
    return {"size": len(_cache), "guild_summaries": len(_guild_summary_cache)}
