from __future__ import annotations

from datetime import datetime
from typing import Any

import pytz

from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

BOT_TIMEZONE_NAME = "America/Denver"


def _format_utc_offset(dt: datetime) -> str:
    raw = dt.strftime("%z")
    return f"{raw[:3]}:{raw[3:]}" if raw else ""


def build_bot_time_snapshot(now: datetime | None = None) -> dict[str, str]:
    tz = pytz.timezone(BOT_TIMEZONE_NAME)
    if now is None:
        current = datetime.now(tz)
    elif now.tzinfo is None:
        current = tz.localize(now)
    else:
        current = now.astimezone(tz)
    return {
        "timezone": BOT_TIMEZONE_NAME,
        "iso_datetime": current.isoformat(),
        "local_date": current.strftime("%Y-%m-%d"),
        "local_time": current.strftime("%H:%M:%S"),
        "weekday": current.strftime("%A"),
        "timezone_abbrev": current.tzname() or BOT_TIMEZONE_NAME,
        "utc_offset": _format_utc_offset(current),
    }


async def _handle_get_current_time(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    snapshot = build_bot_time_snapshot()
    return ToolResult(
        ok=True,
        summary=(
            f"Current bot local time in {snapshot['timezone']}: "
            f"{snapshot['local_date']} {snapshot['local_time']} "
            f"{snapshot['timezone_abbrev']} ({snapshot['weekday']})"
        ),
        data=snapshot,
    )


tool_get_current_time = ToolDefinition(
    name="get_current_time",
    description="Get the bot's authoritative current local date and time in America/Denver.",
    args_schema={},
    handler=_handle_get_current_time,
)
