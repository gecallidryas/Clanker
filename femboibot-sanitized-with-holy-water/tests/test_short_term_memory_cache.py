from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.short_term_memory_cache import (
    ShortTermMessage,
    clear_short_term_memory_for_channel,
    clear_short_term_memory_for_user,
    clear_guild_recency_summary,
    get_guild_recency_summary,
    get_short_term_memory_for_channel,
    get_short_term_memories_for_user,
    store_guild_recency_summary,
    store_short_term_memory,
    update_short_term_memory_summary,
)


def test_store_and_get_short_term_memory():
    messages = [ShortTermMessage(role="user", content="hello", timestamp=datetime.now())]
    store_short_term_memory(user_id=1, channel_id=10, server_id=100, messages=messages)
    entry = get_short_term_memory_for_channel(1, 10)
    assert entry is not None
    assert entry.messages[-1].content == "hello"


def test_update_summary_and_fetch_for_user():
    messages = [ShortTermMessage(role="user", content="topic", timestamp=datetime.now())]
    store_short_term_memory(user_id=2, channel_id=20, server_id=100, messages=messages)
    update_short_term_memory_summary(2, 20, "short summary")
    entries = get_short_term_memories_for_user(2)
    assert len(entries) == 1
    assert entries[0].summary == "short summary"


def test_clear_helpers():
    messages = [ShortTermMessage(role="user", content="x", timestamp=datetime.now())]
    store_short_term_memory(user_id=3, channel_id=30, server_id=100, messages=messages)
    store_short_term_memory(user_id=3, channel_id=31, server_id=100, messages=messages)
    removed_channel = clear_short_term_memory_for_channel(30)
    assert removed_channel >= 1
    removed_user = clear_short_term_memory_for_user(3)
    assert removed_user >= 1


def test_guild_recency_summary_helpers():
    store_guild_recency_summary(server_id=999, summary="Guild-wide handoff")
    assert get_guild_recency_summary(999) == "Guild-wide handoff"
    assert clear_guild_recency_summary(999) is True
    assert get_guild_recency_summary(999) is None
