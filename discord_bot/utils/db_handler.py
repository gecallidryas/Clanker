"""
Database Handler for Femmy Discord Bot
=======================================
Async SQLite wrapper for all database operations.

Tables:
    - users: User profiles with timezone info
    - user_facts: Stored facts about users (!remember)
    - server_config: Server-specific settings (persona mode, bump channel)

Usage:
    from utils.db_handler import init_db, get_user, add_fact
    
    await init_db()
    user = await get_user(123456789)
"""

import os
from pathlib import Path
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime

from utils.logger import get_logger

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_db_path(value: Optional[str]) -> str:
    if not value:
        return str(BASE_DIR / "database.db")
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


# Database file path
DATABASE_PATH = _resolve_db_path(os.getenv("DATABASE_PATH"))

logger = get_logger(__name__)


async def init_db() -> None:
    """
    Initialize the database and create tables if they don't exist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table (with birthday support)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                birthday TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User facts table (for !remember command)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fact TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Server configuration table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                persona_mode TEXT DEFAULT 'mode_femboy',
                bump_channel_id INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ============================================
        # Phase 6: New Tables
        # ============================================
        
        # User affection tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_affection (
                user_id INTEGER PRIMARY KEY,
                affection_points INTEGER DEFAULT 0,
                total_interactions INTEGER DEFAULT 0,
                last_interaction TIMESTAMP,
                affection_level TEXT DEFAULT 'stranger'
            )
        """)
        
        # Bot mood per server
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_mood (
                guild_id INTEGER PRIMARY KEY,
                mood TEXT DEFAULT 'neutral',
                mood_value INTEGER DEFAULT 50,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Reminders
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Bot stats (singleton row)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                messages_processed INTEGER DEFAULT 0,
                commands_executed INTEGER DEFAULT 0,
                images_analyzed INTEGER DEFAULT 0,
                start_time TIMESTAMP
            )
        """)
        
        # Initialize bot_stats if empty
        await db.execute("""
            INSERT OR IGNORE INTO bot_stats (id, start_time) VALUES (1, ?)
        """, (datetime.now(),))
        
        # Add birthday column if missing (migration)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN birthday TEXT")
        except:
            pass  # Column already exists
        
        await db.commit()
        logger.info("Database initialized successfully")


# ============================================
# User Operations
# ============================================

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a user record by their Discord ID.
    
    Args:
        user_id: Discord user ID
        
    Returns:
        User dict or None if not found
        
    TODO:
        - [ ] Implement caching for frequently accessed users
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, timezone: str = "UTC") -> None:
    """
    Create a new user record.
    
    Args:
        user_id: Discord user ID
        timezone: User's timezone (default: UTC)
        
    TODO:
        - [ ] Add validation for timezone string
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, timezone) VALUES (?, ?)",
            (user_id, timezone)
        )
        await db.commit()


async def set_timezone(user_id: int, timezone: str) -> None:
    """
    Set or update a user's timezone.
    
    Args:
        user_id: Discord user ID
        timezone: Timezone string (e.g., "Asia/Dhaka")
        
    TODO:
        - [ ] Validate timezone using pytz
        - [ ] Create user if doesn't exist
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Upsert pattern
        await db.execute("""
            INSERT INTO users (user_id, timezone) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET timezone = ?
        """, (user_id, timezone, timezone))
        await db.commit()


async def get_users_with_timezone() -> List[Dict[str, Any]]:
    """
    Get all users who have set a timezone.
    Used for meal check scheduling.
    
    Returns:
        List of user dicts with timezone info
        
    TODO:
        - [ ] Add filtering for active users only
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE timezone != 'UTC'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ============================================
# Fact Operations (!remember)
# ============================================

async def add_fact(user_id: int, fact: str) -> int:
    """
    Store a fact about a user.
    
    Args:
        user_id: Discord user ID
        fact: The fact to remember
        
    Returns:
        The ID of the inserted fact
        
    TODO:
        - [ ] Limit facts per user (e.g., max 50)
        - [ ] Add duplicate detection
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO user_facts (user_id, fact) VALUES (?, ?)",
            (user_id, fact)
        )
        await db.commit()
        return cursor.lastrowid


async def get_facts(user_id: int) -> List[str]:
    """
    Retrieve all facts stored about a user.
    
    Args:
        user_id: Discord user ID
        
    Returns:
        List of fact strings
        
    TODO:
        - [ ] Add pagination for users with many facts
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT fact FROM user_facts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def delete_facts(user_id: int) -> int:
    """
    Delete all facts for a user (!forget command).
    
    Args:
        user_id: Discord user ID
        
    Returns:
        Number of deleted facts
        
    TODO:
        - [ ] Add confirmation before deletion
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_facts WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        return cursor.rowcount


# ============================================
# Server Configuration Operations
# ============================================

async def get_server_mode(guild_id: int) -> str:
    """
    Get the current persona mode for a server.
    
    Args:
        guild_id: Discord guild/server ID
        
    Returns:
        Persona mode string (default: "mode_femboy")
        
    TODO:
        - [ ] Cache frequently accessed server modes
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT persona_mode FROM server_config WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "mode_femboy"


async def set_server_mode(guild_id: int, mode: str) -> None:
    """
    Set the persona mode for a server.
    
    Args:
        guild_id: Discord guild/server ID
        mode: One of "mode_femboy", "mode_tsundere", "mode_oneesan"
        
    TODO:
        - [ ] Validate mode string
        - [ ] Emit event for mode change
    """
    valid_modes = ["mode_femboy", "mode_tsundere", "mode_oneesan"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, persona_mode, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                persona_mode = ?,
                updated_at = ?
        """, (guild_id, mode, datetime.now(), mode, datetime.now()))
        await db.commit()


async def get_bump_channel(guild_id: int) -> Optional[int]:
    """
    Get the bump channel ID for a server.
    
    Args:
        guild_id: Discord guild/server ID
        
    Returns:
        Channel ID or None
        
    TODO:
        - [ ] Implement this for scheduler.py
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT bump_channel_id FROM server_config WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_bump_channel(guild_id: int, channel_id: int) -> None:
    """
    Set the bump channel for a server.
    
    Args:
        guild_id: Discord guild/server ID
        channel_id: Channel ID for bump messages
        
    TODO:
        - [ ] Validate channel exists and bot has permissions
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, bump_channel_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                bump_channel_id = ?,
                updated_at = ?
        """, (guild_id, channel_id, datetime.now(), channel_id, datetime.now()))
        await db.commit()


# ============================================
# Affection System Operations
# ============================================

AFFECTION_LEVELS = [
    (0, "stranger"),
    (50, "acquaintance"),
    (200, "friend"),
    (500, "close_friend"),
    (1000, "beloved"),
]


def _calculate_level(points: int) -> str:
    """Calculate affection level from points."""
    level = "stranger"
    for threshold, name in AFFECTION_LEVELS:
        if points >= threshold:
            level = name
    return level


async def get_affection(user_id: int) -> Dict[str, Any]:
    """Get user's affection data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_affection WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "user_id": user_id,
                "affection_points": 0,
                "total_interactions": 0,
                "affection_level": "stranger"
            }


async def add_affection(user_id: int, points: int = 1) -> Dict[str, Any]:
    """Add affection points and return updated data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get current data
        async with db.execute(
            "SELECT affection_points, total_interactions FROM user_affection WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if row:
            new_points = row[0] + points
            new_interactions = row[1] + 1
        else:
            new_points = points
            new_interactions = 1
        
        new_level = _calculate_level(new_points)
        
        await db.execute("""
            INSERT INTO user_affection (user_id, affection_points, total_interactions, last_interaction, affection_level)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                affection_points = ?,
                total_interactions = ?,
                last_interaction = ?,
                affection_level = ?
        """, (user_id, new_points, new_interactions, datetime.now(), new_level,
              new_points, new_interactions, datetime.now(), new_level))
        await db.commit()
        
        return {
            "user_id": user_id,
            "affection_points": new_points,
            "total_interactions": new_interactions,
            "affection_level": new_level
        }


# ============================================
# Mood System Operations
# ============================================

async def get_mood(guild_id: int) -> Dict[str, Any]:
    """Get bot mood for a server."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bot_mood WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "guild_id": guild_id,
                "mood": "neutral",
                "mood_value": 50
            }


def _mood_from_value(value: int) -> str:
    """Get mood name from value."""
    if value >= 70:
        return "happy"
    elif value >= 40:
        return "neutral"
    elif value >= 20:
        return "sad"
    else:
        return "neglected"


async def update_mood(guild_id: int, delta: int) -> Dict[str, Any]:
    """Update mood value and return new state."""
    current = await get_mood(guild_id)
    new_value = max(0, min(100, current["mood_value"] + delta))
    new_mood = _mood_from_value(new_value)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO bot_mood (guild_id, mood, mood_value, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                mood = ?,
                mood_value = ?,
                last_updated = ?
        """, (guild_id, new_mood, new_value, datetime.now(),
              new_mood, new_value, datetime.now()))
        await db.commit()
    
    return {"guild_id": guild_id, "mood": new_mood, "mood_value": new_value}


# ============================================
# Birthday Operations
# ============================================

async def set_birthday(user_id: int, birthday: str) -> None:
    """Set user birthday (format: MM-DD)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, birthday) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET birthday = ?
        """, (user_id, birthday, birthday))
        await db.commit()


async def get_birthday(user_id: int) -> Optional[str]:
    """Get user birthday."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT birthday FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def get_upcoming_birthdays(days: int = 30) -> List[Dict[str, Any]]:
    """Get users with birthdays in the next N days."""
    today = datetime.now()
    upcoming = []
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL"
        ) as cursor:
            async for row in cursor:
                try:
                    month, day = map(int, row["birthday"].split("-"))
                    bday_this_year = today.replace(month=month, day=day)
                    if bday_this_year < today:
                        bday_this_year = bday_this_year.replace(year=today.year + 1)
                    
                    days_until = (bday_this_year - today).days
                    if 0 <= days_until <= days:
                        upcoming.append({
                            "user_id": row["user_id"],
                            "birthday": row["birthday"],
                            "days_until": days_until
                        })
                except:
                    continue
    
    return sorted(upcoming, key=lambda x: x["days_until"])


# ============================================
# Reminder Operations
# ============================================

async def add_reminder(user_id: int, guild_id: int | None, channel_id: int, 
                       message: str, remind_at: datetime) -> int:
    """Add a reminder and return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO reminders (user_id, guild_id, channel_id, message, remind_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, guild_id, channel_id, message, remind_at))
        await db.commit()
        return cursor.lastrowid


async def get_user_reminders(user_id: int) -> List[Dict[str, Any]]:
    """Get all active reminders for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM reminders 
            WHERE user_id = ? AND completed = FALSE
            ORDER BY remind_at ASC
        """, (user_id,)) as cursor:
            return [dict(row) async for row in cursor]


async def get_due_reminders() -> List[Dict[str, Any]]:
    """Get all reminders that are due now."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM reminders 
            WHERE remind_at <= ? AND completed = FALSE
        """, (datetime.now(),)) as cursor:
            return [dict(row) async for row in cursor]


async def complete_reminder(reminder_id: int) -> None:
    """Mark a reminder as completed."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE reminders SET completed = TRUE WHERE id = ?",
            (reminder_id,)
        )
        await db.commit()


async def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Delete a reminder (must belong to user)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# ============================================
# Bot Stats Operations
# ============================================

async def increment_stat(stat_name: str, amount: int = 1) -> None:
    """Increment a bot statistic."""
    valid_stats = ["messages_processed", "commands_executed", "images_analyzed"]
    if stat_name not in valid_stats:
        return
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"""
            UPDATE bot_stats SET {stat_name} = {stat_name} + ? WHERE id = 1
        """, (amount,))
        await db.commit()


async def get_stats() -> Dict[str, Any]:
    """Get all bot statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bot_stats WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "messages_processed": 0,
                "commands_executed": 0,
                "images_analyzed": 0,
                "start_time": datetime.now()
            }

