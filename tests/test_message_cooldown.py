from datetime import datetime, timedelta
from types import SimpleNamespace
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.message_cooldown import (
    COOLDOWN_PER_CHANNEL,
    COOLDOWN_PER_USER,
    COOLDOWN_SERVER_WIDE,
    COOLDOWN_STRICT_SERVER_WIDE,
    check_reply_cooldown,
    set_reply_cooldown,
)


def _member(can_manage: bool):
    return SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=can_manage))


def test_per_user_cooldown_blocks_recent_reply():
    now = datetime.now()
    cooldowns = {("user", 123): now - timedelta(seconds=2)}
    blocked, remaining = check_reply_cooldown(
        cooldowns,
        cooldown_type=COOLDOWN_PER_USER,
        cooldown_seconds=10,
        guild_id=1,
        channel_id=2,
        user_id=123,
        now=now,
    )
    assert blocked is True
    assert remaining > 0


def test_per_channel_cooldown_keying():
    now = datetime.now()
    cooldowns = {("channel", 77): now - timedelta(seconds=1)}
    blocked, _ = check_reply_cooldown(
        cooldowns,
        cooldown_type=COOLDOWN_PER_CHANNEL,
        cooldown_seconds=10,
        guild_id=1,
        channel_id=77,
        user_id=999,
        now=now,
    )
    assert blocked is True


def test_server_wide_cooldown_keying():
    now = datetime.now()
    cooldowns = {("server", 55): now - timedelta(seconds=1)}
    blocked, _ = check_reply_cooldown(
        cooldowns,
        cooldown_type=COOLDOWN_SERVER_WIDE,
        cooldown_seconds=10,
        guild_id=55,
        channel_id=2,
        user_id=3,
        now=now,
    )
    assert blocked is True


def test_manage_guild_exempt_except_strict():
    now = datetime.now()
    cooldowns = {("user", 123): now - timedelta(seconds=1), ("server", 1): now - timedelta(seconds=1)}

    blocked_regular, _ = check_reply_cooldown(
        cooldowns,
        cooldown_type=COOLDOWN_PER_USER,
        cooldown_seconds=10,
        guild_id=1,
        channel_id=2,
        user_id=123,
        member=_member(True),
        now=now,
    )
    assert blocked_regular is False

    blocked_strict, _ = check_reply_cooldown(
        cooldowns,
        cooldown_type=COOLDOWN_STRICT_SERVER_WIDE,
        cooldown_seconds=10,
        guild_id=1,
        channel_id=2,
        user_id=123,
        member=_member(True),
        now=now,
    )
    assert blocked_strict is True


def test_set_reply_cooldown_stores_expected_key():
    cooldowns = {}
    key = set_reply_cooldown(
        cooldowns,
        cooldown_type=COOLDOWN_PER_CHANNEL,
        guild_id=1,
        channel_id=20,
        user_id=30,
    )
    assert key == ("channel", 20)
    assert key in cooldowns
