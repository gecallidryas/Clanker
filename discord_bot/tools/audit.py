from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Optional

import aiosqlite

from tools.contracts import ToolDescriptor
from utils.db_handler import global_db
from utils.logger import get_logger

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def summarize_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 2:
        return {"type": type(value).__name__}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return {"type": "string", "length": len(value)}
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    if isinstance(value, dict):
        keys = sorted(str(key) for key in value.keys())
        return {
            "type": "object",
            "keys": keys,
            "shape": {str(key): summarize_value(val, depth=depth + 1) for key, val in list(value.items())[:10]},
        }
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        return {
            "type": type(value).__name__,
            "length": len(items),
            "items": [summarize_value(item, depth=depth + 1) for item in items[:5]],
        }
    return {"type": type(value).__name__}


def summarize_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    safe_arguments = arguments if isinstance(arguments, dict) else {}
    return {
        "arg_keys": sorted(str(key) for key in safe_arguments.keys()),
        "arg_shape": {str(key): summarize_value(value) for key, value in safe_arguments.items()},
    }


def summarize_tool_result(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", {}) if result is not None else {}
    return {
        "ok": bool(getattr(result, "ok", False)),
        "summary_length": len(str(getattr(result, "summary", "") or "")),
        "data": summarize_value(data),
        "user_message_present": bool(getattr(result, "user_message", None)),
        "skip_model": bool(getattr(result, "skip_model", False)),
    }


def make_tool_timer() -> float:
    return perf_counter()


def elapsed_ms(timer_started: float) -> int:
    return max(0, int((perf_counter() - timer_started) * 1000))


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


async def cleanup_expired_debug_capture(*, guild_id: Optional[int] = None) -> None:
    now_iso = utcnow().isoformat()
    normalized_guild_id = int(guild_id or 0)
    async with global_db() as db:
        if guild_id is None:
            await db.execute(
                "DELETE FROM tool_debug_capture WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now_iso,),
            )
            await db.execute(
                "DELETE FROM tool_debug_capture_settings WHERE expires_at <= ?",
                (now_iso,),
            )
        else:
            await db.execute(
                "DELETE FROM tool_debug_capture WHERE guild_id = ? AND expires_at IS NOT NULL AND expires_at <= ?",
                (normalized_guild_id, now_iso),
            )
            await db.execute(
                "DELETE FROM tool_debug_capture_settings WHERE guild_id = ? AND expires_at <= ?",
                (normalized_guild_id, now_iso),
            )
        await db.commit()


async def set_debug_capture_window(
    *,
    guild_id: Optional[int],
    enabled_by: Optional[int],
    ttl_seconds: int,
    note: Optional[str] = None,
) -> None:
    normalized_guild_id = int(guild_id or 0)
    expires_at = utcnow() + timedelta(seconds=max(0, int(ttl_seconds)))
    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO tool_debug_capture_settings (guild_id, enabled_by, note, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET
                enabled_by = excluded.enabled_by,
                note = excluded.note,
                expires_at = excluded.expires_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (normalized_guild_id, enabled_by, note, expires_at.isoformat()),
        )
        await db.commit()


async def disable_debug_capture_window(*, guild_id: Optional[int]) -> None:
    normalized_guild_id = int(guild_id or 0)
    async with global_db() as db:
        await db.execute(
            "DELETE FROM tool_debug_capture WHERE guild_id = ?",
            (normalized_guild_id,),
        )
        await db.execute(
            "DELETE FROM tool_debug_capture_settings WHERE guild_id = ?",
            (normalized_guild_id,),
        )
        await db.commit()


async def is_debug_capture_enabled(*, guild_id: Optional[int]) -> bool:
    normalized_guild_id = int(guild_id or 0)
    now_iso = utcnow().isoformat()
    await cleanup_expired_debug_capture(guild_id=normalized_guild_id)
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT guild_id
            FROM tool_debug_capture_settings
            WHERE guild_id = ? AND expires_at > ?
            """,
            (normalized_guild_id, now_iso),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def record_tool_execution(
    *,
    descriptor: Optional[ToolDescriptor],
    context: Any,
    arguments: dict[str, Any],
    result: Optional[Any],
    invocation_mode: str,
    decision_outcome: str,
    execution_outcome: str,
    reason_codes: Optional[list[str]] = None,
    error_category: Optional[str] = None,
    latency_ms: Optional[int] = None,
    raw_payload: Optional[dict[str, Any]] = None,
    raw_result: Optional[dict[str, Any]] = None,
    tool_name: Optional[str] = None,
) -> None:
    guild_id = int(getattr(getattr(context, "guild", None), "id", 0) or 0)
    channel_id = getattr(getattr(context, "channel", None), "id", None)
    user_id = getattr(getattr(context, "user", None), "id", None)
    args_summary = summarize_tool_arguments(arguments)
    result_summary = summarize_tool_result(result) if result is not None else {}
    debug_capture_id = None

    try:
        if await is_debug_capture_enabled(guild_id=guild_id):
            async with global_db() as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT expires_at FROM tool_debug_capture_settings WHERE guild_id = ?",
                    (guild_id,),
                ) as cursor:
                    capture_setting = await cursor.fetchone()
                expires_at = capture_setting["expires_at"] if capture_setting else None
                cursor = await db.execute(
                    """
                    INSERT INTO tool_debug_capture
                        (guild_id, tool_id, tool_name, raw_args_json, raw_result_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """,
                    (
                        guild_id,
                        descriptor.tool_id if descriptor else None,
                        descriptor.public_name if descriptor else tool_name,
                        _json_dumps(raw_payload or arguments),
                        _json_dumps(raw_result or result_summary),
                        expires_at,
                    ),
                )
                debug_capture_id = cursor.lastrowid
                await db.commit()
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning("Failed to persist tool debug capture: %s", exc)

    try:
        async with global_db() as db:
            await db.execute(
                """
                INSERT INTO tool_execution_log (
                    guild_id,
                    channel_id,
                    user_id,
                    provider,
                    model,
                    tool_name,
                    tool_source_type,
                    invocation_mode,
                    decision_outcome,
                    execution_outcome,
                    latency_ms,
                    timestamp,
                    error_category,
                    request_id,
                    turn_id,
                    tool_id,
                    category,
                    reason_codes_json,
                    args_summary_json,
                    result_summary_json,
                    debug_capture_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    int(channel_id) if channel_id is not None else None,
                    int(user_id) if user_id is not None else None,
                    getattr(context, "provider_name", None),
                    getattr(context, "model_name", None),
                    descriptor.public_name if descriptor else tool_name,
                    descriptor.source_type.value if descriptor else None,
                    invocation_mode,
                    decision_outcome,
                    execution_outcome,
                    latency_ms,
                    error_category,
                    getattr(context, "request_id", None),
                    getattr(context, "turn_id", None),
                    descriptor.tool_id if descriptor else None,
                    descriptor.category if descriptor else None,
                    _json_dumps(reason_codes or []),
                    _json_dumps(args_summary),
                    _json_dumps(result_summary),
                    debug_capture_id,
                ),
            )
            await db.commit()
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning("Failed to persist tool execution log: %s", exc)
