from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pytz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils import time_tools


class _FakeContext:
    pass


def test_build_bot_time_snapshot_formats_denver_timestamp():
    tz = pytz.timezone("America/Denver")
    fixed = tz.localize(datetime(2026, 1, 15, 8, 30, 45))

    snapshot = time_tools.build_bot_time_snapshot(fixed)

    assert snapshot["timezone"] == "America/Denver"
    assert snapshot["local_date"] == "2026-01-15"
    assert snapshot["local_time"] == "08:30:45"
    assert snapshot["weekday"] == "Thursday"
    assert snapshot["timezone_abbrev"] == "MST"


def test_get_current_time_tool_returns_read_only_payload():
    result = asyncio.run(time_tools._handle_get_current_time(_FakeContext(), {}))

    assert result.ok is True
    assert result.data["timezone"] == "America/Denver"
    assert "local_date" in result.data
    assert "local_time" in result.data
