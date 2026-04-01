"""
Guild admin password and session management.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
import aiosqlite

from utils.db_handler import guild_db


SESSION_DURATION_MINUTES = 15


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


async def get_guild_auth_record(guild_id: int) -> Optional[Dict[str, Any]]:
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guild_admin_auth WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def has_password(guild_id: int) -> bool:
    record = await get_guild_auth_record(guild_id)
    return bool(record and record.get("password_hash"))


async def set_password(guild_id: int, password: str, user_id: int) -> None:
    password_hash = _hash_password(password)
    async with guild_db(guild_id) as db:
        await db.execute(
            """
            INSERT INTO guild_admin_auth (guild_id, password_hash, created_by, password_version)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET
                password_hash = excluded.password_hash,
                created_by = excluded.created_by,
                created_at = CURRENT_TIMESTAMP,
                password_version = password_version + 1
            """,
            (guild_id, password_hash, user_id),
        )
        await db.commit()


async def verify_password(guild_id: int, password: str) -> bool:
    record = await get_guild_auth_record(guild_id)
    if not record:
        return False
    return _verify_password(password, record["password_hash"])


async def create_session(guild_id: int, user_id: int) -> None:
    record = await get_guild_auth_record(guild_id)
    if not record:
        return
    expires_at = datetime.utcnow() + timedelta(minutes=SESSION_DURATION_MINUTES)
    async with guild_db(guild_id) as db:
        await db.execute(
            """
            INSERT INTO guild_auth_sessions (guild_id, user_id, password_version, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                password_version = excluded.password_version,
                expires_at = excluded.expires_at
            """,
            (guild_id, user_id, record["password_version"], expires_at.isoformat()),
        )
        await db.execute(
            "UPDATE guild_admin_auth SET last_used_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            (guild_id,),
        )
        await db.commit()


async def verify_and_create_session(guild_id: int, user_id: int, password: str) -> bool:
    if not await verify_password(guild_id, password):
        return False
    await create_session(guild_id, user_id)
    return True


async def is_authenticated(guild_id: int, user_id: int) -> bool:
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT s.expires_at, s.password_version, a.password_version AS current_version
            FROM guild_auth_sessions s
            JOIN guild_admin_auth a ON s.guild_id = a.guild_id
            WHERE s.guild_id = ? AND s.user_id = ?
            """,
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            if row["password_version"] != row["current_version"]:
                return False
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.utcnow():
                await db.execute(
                    "DELETE FROM guild_auth_sessions WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                await db.commit()
                return False
            return True


async def clear_session(guild_id: int, user_id: int) -> None:
    async with guild_db(guild_id) as db:
        await db.execute(
            "DELETE FROM guild_auth_sessions WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await db.commit()


async def cleanup_expired_sessions(guild_id: int) -> int:
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM guild_auth_sessions WHERE expires_at < ?",
            (datetime.utcnow().isoformat(),),
        )
        await db.commit()
        return cursor.rowcount
