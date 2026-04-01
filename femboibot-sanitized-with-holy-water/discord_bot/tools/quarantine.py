from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite

from tools.categories import normalize_tool_category
from tools.contracts import ToolDescriptor
from utils.db_handler import global_db


DEFAULT_QUARANTINE_CATEGORY = "*"
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_QUARANTINE_MINUTES = 30
COUNTED_ERROR_CATEGORIES = {"exception", "invalid_result", "timeout", "backend_error", "transport_error"}


@dataclass(slots=True, frozen=True)
class QuarantinePolicy:
    category: str
    failure_threshold: int
    quarantine_minutes: int
    updated_by: Optional[int] = None
    note: Optional[str] = None


@dataclass(slots=True, frozen=True)
class QuarantineState:
    guild_id: int
    tool_id: str
    category: str
    failure_count: int
    quarantined_until: Optional[str]
    quarantine_reason: Optional[str]
    last_failure_at: Optional[str]

    @property
    def active(self) -> bool:
        if not self.quarantined_until:
            return False
        return self.quarantined_until > datetime.now(timezone.utc).isoformat()


async def _ensure_default_policy() -> None:
    async with global_db() as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO tool_quarantine_policy
                (category, failure_threshold, quarantine_minutes, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                DEFAULT_QUARANTINE_CATEGORY,
                DEFAULT_FAILURE_THRESHOLD,
                DEFAULT_QUARANTINE_MINUTES,
                "default",
            ),
        )
        await db.commit()


def _row_to_policy(row) -> QuarantinePolicy:
    return QuarantinePolicy(
        category=row["category"],
        failure_threshold=int(row["failure_threshold"]),
        quarantine_minutes=int(row["quarantine_minutes"]),
        updated_by=row["updated_by"],
        note=row["note"],
    )


def _row_to_state(row) -> QuarantineState:
    return QuarantineState(
        guild_id=int(row["guild_id"]),
        tool_id=row["tool_id"],
        category=row["category"],
        failure_count=int(row["failure_count"]),
        quarantined_until=row["quarantined_until"],
        quarantine_reason=row["quarantine_reason"],
        last_failure_at=row["last_failure_at"],
    )


async def set_quarantine_policy(
    *,
    category: Optional[str],
    failure_threshold: int,
    quarantine_minutes: int,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
) -> QuarantinePolicy:
    await _ensure_default_policy()
    normalized_category = DEFAULT_QUARANTINE_CATEGORY if not category else normalize_tool_category(category)
    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO tool_quarantine_policy
                (category, failure_threshold, quarantine_minutes, updated_by, note)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category)
            DO UPDATE SET
                failure_threshold = excluded.failure_threshold,
                quarantine_minutes = excluded.quarantine_minutes,
                updated_by = excluded.updated_by,
                note = excluded.note,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                normalized_category,
                int(failure_threshold),
                int(quarantine_minutes),
                actor_id,
                note,
            ),
        )
        await db.commit()
    return QuarantinePolicy(
        category=normalized_category,
        failure_threshold=int(failure_threshold),
        quarantine_minutes=int(quarantine_minutes),
        updated_by=actor_id,
        note=note,
    )


async def get_effective_quarantine_policy(category: str) -> QuarantinePolicy:
    await _ensure_default_policy()
    normalized_category = normalize_tool_category(category)
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM tool_quarantine_policy
            WHERE category IN (?, ?)
            ORDER BY CASE category WHEN ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (normalized_category, DEFAULT_QUARANTINE_CATEGORY, normalized_category),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return QuarantinePolicy(
            category=DEFAULT_QUARANTINE_CATEGORY,
            failure_threshold=DEFAULT_FAILURE_THRESHOLD,
            quarantine_minutes=DEFAULT_QUARANTINE_MINUTES,
        )
    return _row_to_policy(row)


async def list_quarantine_policies() -> list[QuarantinePolicy]:
    await _ensure_default_policy()
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tool_quarantine_policy ORDER BY category ASC"
        ) as cursor:
            rows = await cursor.fetchall()
    return [_row_to_policy(row) for row in rows]


async def list_quarantine_states(*, guild_id: int, active_only: bool = False) -> list[QuarantineState]:
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM tool_quarantine_state WHERE guild_id = ?"
        params: list[object] = [int(guild_id)]
        if active_only:
            query += " AND quarantined_until IS NOT NULL AND quarantined_until > ?"
            params.append(datetime.now(timezone.utc).isoformat())
        query += " ORDER BY updated_at DESC, tool_id ASC"
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
    return [_row_to_state(row) for row in rows]


async def get_quarantine_state(*, guild_id: int, tool_id: str) -> Optional[QuarantineState]:
    async with global_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM tool_quarantine_state
            WHERE guild_id = ? AND tool_id = ?
            """,
            (int(guild_id), tool_id),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_state(row)


async def clear_quarantine_state(*, guild_id: int, tool_id: str, actor_id: Optional[int] = None, note: Optional[str] = None) -> None:
    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO tool_quarantine_state
                (guild_id, tool_id, category, failure_count, quarantined_until, quarantine_reason, last_failure_at)
            VALUES (?, ?, ?, 0, NULL, NULL, NULL)
            ON CONFLICT(guild_id, tool_id)
            DO UPDATE SET
                failure_count = 0,
                quarantined_until = NULL,
                quarantine_reason = NULL,
                last_failure_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            """,
            (int(guild_id), tool_id, "uncategorized"),
        )
        await db.commit()


async def update_quarantine_from_execution(
    *,
    descriptor: Optional[ToolDescriptor],
    guild_id: Optional[int],
    execution_outcome: str,
    error_category: Optional[str],
) -> None:
    if descriptor is None or not guild_id:
        return

    if execution_outcome == "success":
        async with global_db() as db:
            await db.execute(
                """
                INSERT INTO tool_quarantine_state
                    (guild_id, tool_id, category, failure_count, quarantined_until, quarantine_reason, last_failure_at)
                VALUES (?, ?, ?, 0, NULL, NULL, NULL)
                ON CONFLICT(guild_id, tool_id)
                DO UPDATE SET
                    failure_count = 0,
                    category = excluded.category,
                    quarantined_until = NULL,
                    quarantine_reason = NULL,
                    last_failure_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (int(guild_id), descriptor.tool_id, descriptor.category),
            )
            await db.commit()
        return

    if execution_outcome != "error" or error_category not in COUNTED_ERROR_CATEGORIES:
        return

    policy = await get_effective_quarantine_policy(descriptor.category)
    current = await get_quarantine_state(guild_id=int(guild_id), tool_id=descriptor.tool_id)
    current_failures = current.failure_count if current else 0
    next_failures = current_failures + 1
    quarantined_until = None
    if next_failures >= policy.failure_threshold:
        quarantined_until = (datetime.now(timezone.utc) + timedelta(minutes=policy.quarantine_minutes)).isoformat()

    async with global_db() as db:
        await db.execute(
            """
            INSERT INTO tool_quarantine_state
                (guild_id, tool_id, category, failure_count, quarantined_until, quarantine_reason, last_failure_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, tool_id)
            DO UPDATE SET
                category = excluded.category,
                failure_count = excluded.failure_count,
                quarantined_until = excluded.quarantined_until,
                quarantine_reason = excluded.quarantine_reason,
                last_failure_at = excluded.last_failure_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                int(guild_id),
                descriptor.tool_id,
                descriptor.category,
                next_failures,
                quarantined_until,
                error_category,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
