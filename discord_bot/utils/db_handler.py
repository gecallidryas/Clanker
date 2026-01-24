"""
Database Handler for Femmy Discord Bot
=======================================
Async SQLite wrapper for all database operations.

Tables:
    - users: Global user registry (for foreign keys)
    - user_profiles: Guild-scoped user settings (timezone, birthday)
    - user_facts: Stored facts about users (!remember)
    - server_config: Server-specific settings (persona mode, bump channel)

Usage:
    from utils.db_handler import init_db, get_user, add_fact
    
    await init_db()
    user = await get_user(987654321, 123456789)
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
        # Users table (global registry)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                birthday TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Guild-scoped user profiles (timezone/birthday)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                timezone TEXT DEFAULT 'UTC',
                birthday TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User facts table (for !remember command)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
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
        
        # User affection tracking (guild scoped)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_affection_v2 (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                affection_points INTEGER DEFAULT 0,
                total_interactions INTEGER DEFAULT 0,
                last_interaction TIMESTAMP,
                affection_level TEXT DEFAULT 'stranger',
                PRIMARY KEY (guild_id, user_id)
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

        # Wellbeing checks (one per user per day, per guild)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wellbeing_checks (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                last_asked_date TEXT,
                PRIMARY KEY (guild_id, user_id)
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

        # Best-effort migration to guild_id=0 profile (legacy data)
        try:
            await db.execute("""
                INSERT OR IGNORE INTO user_profiles (guild_id, user_id, timezone, birthday, created_at)
                SELECT 0, user_id, timezone, birthday, created_at FROM users
            """)
        except:
            pass

        # Add guild_id column to user_facts if missing (migration)
        try:
            await db.execute("ALTER TABLE user_facts ADD COLUMN guild_id INTEGER DEFAULT 0")
        except:
            pass
        
        # ============================================
        # Phase 7: Enhanced Memory System Tables
        # ============================================
        
        # Add source tracking to user_facts (migration)
        try:
            await db.execute("ALTER TABLE user_facts ADD COLUMN source TEXT DEFAULT 'manual'")
        except:
            pass
        try:
            await db.execute("ALTER TABLE user_facts ADD COLUMN learned_from_user_id INTEGER")
        except:
            pass

        # Add guild_id column to user_aliases if missing (migration)
        try:
            await db.execute("ALTER TABLE user_aliases ADD COLUMN guild_id INTEGER DEFAULT 0")
        except:
            pass

        # Add guild_id column to pending_facts if missing (migration)
        try:
            await db.execute("ALTER TABLE pending_facts ADD COLUMN guild_id INTEGER DEFAULT 0")
        except:
            pass

        # Add last_asked_date to wellbeing_checks if missing (migration)
        try:
            await db.execute("ALTER TABLE wellbeing_checks ADD COLUMN last_asked_date TEXT")
        except:
            pass
        
        # User aliases table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                alias TEXT NOT NULL COLLATE NOCASE,
                added_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, user_id, alias)
            )
        """)

        # Gender roles per server
        await db.execute("""
            CREATE TABLE IF NOT EXISTS gender_roles (
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                gender TEXT NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        
        # Pending facts (for ask-before-saving)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                about_user_id INTEGER NOT NULL,
                fact TEXT NOT NULL,
                learned_from_user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        # Add evil_mode column to server_config (migration)
        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN evil_mode BOOLEAN DEFAULT FALSE")
        except:
            pass  # Column already exists
        
        await db.commit()
        logger.info("Database initialized successfully")


# ============================================
# User Operations
# ============================================

async def get_user(guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a guild-scoped user profile by Discord ID.
    
    Args:
        guild_id: Discord guild/server ID
        user_id: Discord user ID
        
    Returns:
        User dict or None if not found
        
    TODO:
        - [ ] Implement caching for frequently accessed users
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_profiles WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(guild_id: int, user_id: int, timezone: str = "UTC") -> None:
    """
    Create a new guild-scoped user profile.
    
    Args:
        guild_id: Discord guild/server ID
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
        await db.execute(
            """INSERT OR IGNORE INTO user_profiles (guild_id, user_id, timezone)
               VALUES (?, ?, ?)""",
            (guild_id, user_id, timezone)
        )
        await db.commit()


async def set_timezone(guild_id: int, user_id: int, timezone: str) -> None:
    """
    Set or update a user's timezone for a guild.
    
    Args:
        guild_id: Discord guild/server ID
        user_id: Discord user ID
        timezone: Timezone string (e.g., "Asia/Dhaka")
        
    TODO:
        - [ ] Validate timezone using pytz
        - [ ] Create user if doesn't exist
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.execute("""
            INSERT INTO user_profiles (guild_id, user_id, timezone) VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET timezone = ?
        """, (guild_id, user_id, timezone, timezone))
        await db.commit()


async def get_users_with_timezone(guild_id: int) -> List[Dict[str, Any]]:
    """
    Get all users who have set a timezone for a guild.
    Used for meal check scheduling.
    
    Returns:
        List of user dicts with timezone info
        
    TODO:
        - [ ] Add filtering for active users only
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_profiles WHERE guild_id = ? AND timezone != 'UTC'",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ============================================
# Fact Operations (!remember)
# ============================================

async def add_fact(guild_id: int, user_id: int, fact: str) -> int:
    """
    Store a fact about a user.
    
    Args:
        guild_id: Discord guild/server ID
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
            "INSERT INTO user_facts (guild_id, user_id, fact) VALUES (?, ?, ?)",
            (guild_id, user_id, fact)
        )
        await db.commit()
        return cursor.lastrowid


async def get_facts(guild_id: int, user_id: int) -> List[str]:
    """
    Retrieve all facts stored about a user.
    
    Args:
        guild_id: Discord guild/server ID
        user_id: Discord user ID
        
    Returns:
        List of fact strings
        
    TODO:
        - [ ] Add pagination for users with many facts
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT fact FROM user_facts WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def delete_facts(guild_id: int, user_id: int) -> int:
    """
    Delete all facts for a user (!forget command).
    
    Args:
        guild_id: Discord guild/server ID
        user_id: Discord user ID
        
    Returns:
        Number of deleted facts
        
    TODO:
        - [ ] Add confirmation before deletion
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_facts WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        await db.commit()
        return cursor.rowcount


# ============================================
# Server Configuration Operations
# ============================================

async def get_server_mode(guild_id: int) -> str:
    """
    Get the current persona mode for a server.
    
    If BOT_MODE is set in environment, that mode is used globally.
    Otherwise, returns the server-specific mode.
    
    Args:
        guild_id: Discord guild/server ID
        
    Returns:
        Persona mode string (default: "mode_femboy")
    """
    # Check for locked mode from environment
    locked_mode = os.getenv("BOT_MODE", "").lower()
    mode_map = {"femboy": "mode_femboy", "tsundere": "mode_tsundere", "oneesan": "mode_oneesan"}
    if locked_mode in mode_map:
        return mode_map[locked_mode]
    
    # Otherwise use server-specific mode
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


async def get_evil_mode(guild_id: int) -> bool:
    """
    Check if evil (uncensored) mode is enabled for a server.
    
    Args:
        guild_id: Discord guild/server ID
        
    Returns:
        True if evil mode is enabled
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT evil_mode FROM server_config WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row and row[0] else False


async def set_evil_mode(guild_id: int, enabled: bool) -> None:
    """
    Enable or disable evil (uncensored) mode for a server.
    
    Args:
        guild_id: Discord guild/server ID
        enabled: True to enable evil mode
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, evil_mode, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                evil_mode = ?,
                updated_at = ?
        """, (guild_id, enabled, datetime.now(), enabled, datetime.now()))
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


async def get_affection(guild_id: int, user_id: int) -> Dict[str, Any]:
    """Get user's affection data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_affection_v2 WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "guild_id": guild_id,
                "user_id": user_id,
                "affection_points": 0,
                "total_interactions": 0,
                "affection_level": "stranger"
            }


async def add_affection(guild_id: int, user_id: int, points: int = 1) -> Dict[str, Any]:
    """Add affection points and return updated data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get current data
        async with db.execute(
            "SELECT affection_points, total_interactions FROM user_affection_v2 WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
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
            INSERT INTO user_affection_v2 (guild_id, user_id, affection_points, total_interactions, last_interaction, affection_level)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                affection_points = ?,
                total_interactions = ?,
                last_interaction = ?,
                affection_level = ?
        """, (guild_id, user_id, new_points, new_interactions, datetime.now(), new_level,
              new_points, new_interactions, datetime.now(), new_level))
        await db.commit()
        
        return {
            "guild_id": guild_id,
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

async def set_birthday(guild_id: int, user_id: int, birthday: str) -> None:
    """Set user birthday (format: MM-DD) for a guild."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.execute("""
            INSERT INTO user_profiles (guild_id, user_id, birthday) VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET birthday = ?
        """, (guild_id, user_id, birthday, birthday))
        await db.commit()


async def get_birthday(guild_id: int, user_id: int) -> Optional[str]:
    """Get user birthday for a guild."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT birthday FROM user_profiles WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def get_upcoming_birthdays(guild_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Get users with birthdays in the next N days for a guild."""
    today = datetime.now()
    upcoming = []
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, birthday FROM user_profiles WHERE guild_id = ? AND birthday IS NOT NULL",
            (guild_id,)
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


# ============================================
# User Aliases Operations
# ============================================

async def add_alias(guild_id: int, user_id: int, alias: str, added_by_user_id: int) -> bool:
    """Add an alias for a user. Returns True if added, False if already exists."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO user_aliases (guild_id, user_id, alias, added_by_user_id) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, alias, added_by_user_id)
            )
            await db.commit()
            return True
        except:
            return False


async def get_aliases(guild_id: int, user_id: int) -> List[str]:
    """Get all aliases for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT alias FROM user_aliases WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def find_user_by_alias(guild_id: int, alias: str) -> Optional[int]:
    """Find a user ID by their alias (case-insensitive)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM user_aliases WHERE guild_id = ? AND alias = ? COLLATE NOCASE",
            (guild_id, alias)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def delete_alias(guild_id: int, user_id: int, alias: str) -> bool:
    """Delete an alias for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_aliases WHERE guild_id = ? AND user_id = ? AND alias = ? COLLATE NOCASE",
            (guild_id, user_id, alias)
        )
        await db.commit()
        return cursor.rowcount > 0


# ============================================
# Wellbeing Check Operations
# ============================================

async def get_last_wellbeing_date(guild_id: int, user_id: int) -> Optional[str]:
    """Get the last wellbeing check date for a user (YYYY-MM-DD)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT last_asked_date FROM wellbeing_checks WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_last_wellbeing_date(guild_id: int, user_id: int, date_str: str) -> None:
    """Set the last wellbeing check date for a user (YYYY-MM-DD)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO wellbeing_checks (guild_id, user_id, last_asked_date)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id, user_id) DO UPDATE SET
                   last_asked_date = ?""",
            (guild_id, user_id, date_str, date_str)
        )
        await db.commit()


# ============================================
# Gender Role Operations
# ============================================

async def set_gender_role(guild_id: int, role_id: int, gender: str) -> None:
    """Set or update a gender role for a server."""
    gender = gender.strip().lower()
    if gender not in ("male", "female"):
        raise ValueError("Gender must be 'male' or 'female'.")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO gender_roles (guild_id, role_id, gender)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, role_id) DO UPDATE SET
                gender = ?
        """, (guild_id, role_id, gender, gender))
        await db.commit()


async def delete_gender_role(guild_id: int, role_id: int) -> bool:
    """Delete a gender role mapping for a server."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM gender_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_gender_roles(guild_id: int) -> Dict[int, str]:
    """Get gender role mappings for a server."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT role_id, gender FROM gender_roles WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


# ============================================
# Enhanced Fact Operations (with source tracking)
# ============================================

async def add_fact_with_source(
    guild_id: int,
    user_id: int,
    fact: str,
    source: str = "manual",
    learned_from_user_id: Optional[int] = None
) -> int:
    """Store a fact about a user with source tracking."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO user_facts (guild_id, user_id, fact, source, learned_from_user_id) 
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, fact, source, learned_from_user_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_facts_detailed(guild_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Get all facts about a user with full details."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, fact, source, learned_from_user_id, created_at 
               FROM user_facts WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC""",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def delete_fact_by_id(guild_id: int, fact_id: int) -> bool:
    """Delete a specific fact by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_facts WHERE guild_id = ? AND id = ?",
            (guild_id, fact_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# ============================================
# Pending Facts Operations (ask-before-save)
# ============================================

async def create_pending_fact(
    guild_id: int,
    about_user_id: int,
    fact: str,
    learned_from_user_id: int,
    channel_id: int,
    message_id: Optional[int] = None,
    expires_minutes: int = 5
) -> int:
    """Create a pending fact awaiting confirmation."""
    expires_at = datetime.now() + __import__('datetime').timedelta(minutes=expires_minutes)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO pending_facts 
               (guild_id, about_user_id, fact, learned_from_user_id, channel_id, message_id, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (guild_id, about_user_id, fact, learned_from_user_id, channel_id, message_id, expires_at)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_fact(pending_id: int) -> Optional[Dict[str, Any]]:
    """Get a pending fact by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pending_facts WHERE id = ?",
            (pending_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def confirm_pending_fact(pending_id: int) -> bool:
    """Confirm a pending fact and move it to user_facts."""
    pending = await get_pending_fact(pending_id)
    if not pending:
        return False
    
    # Check if expired
    if datetime.fromisoformat(pending["expires_at"]) < datetime.now():
        await delete_pending_fact(pending_id)
        return False
    
    # Move to user_facts
    await add_fact_with_source(
        pending["guild_id"],
        pending["about_user_id"],
        pending["fact"],
        source="learned",
        learned_from_user_id=pending["learned_from_user_id"]
    )
    await delete_pending_fact(pending_id)
    return True


async def delete_pending_fact(pending_id: int) -> bool:
    """Delete a pending fact."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM pending_facts WHERE id = ?",
            (pending_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def cleanup_expired_pending_facts() -> int:
    """Delete all expired pending facts."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM pending_facts WHERE expires_at < ?",
            (datetime.now(),)
        )
        await db.commit()
        return cursor.rowcount


# ============================================
# Admin Operations
# ============================================

async def reset_user_data(guild_id: int, user_id: int, reset_type: str = "all") -> Dict[str, int]:
    """Reset user data. reset_type: 'all', 'facts', 'affection', 'aliases'"""
    deleted = {"facts": 0, "affection": 0, "aliases": 0}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if reset_type in ("all", "facts"):
            cursor = await db.execute(
                "DELETE FROM user_facts WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            deleted["facts"] = cursor.rowcount
        
        if reset_type in ("all", "affection"):
            cursor = await db.execute(
                "DELETE FROM user_affection_v2 WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            deleted["affection"] = cursor.rowcount
        
        if reset_type in ("all", "aliases"):
            cursor = await db.execute(
                "DELETE FROM user_aliases WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            deleted["aliases"] = cursor.rowcount
        
        await db.commit()
    
    return deleted


async def set_affection_value(guild_id: int, user_id: int, points: int) -> Dict[str, Any]:
    """Set a user's affection points to a specific value."""
    new_level = _calculate_level(points)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO user_affection_v2 (guild_id, user_id, affection_points, affection_level, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                affection_points = ?,
                affection_level = ?,
                last_interaction = ?
        """, (guild_id, user_id, points, new_level, datetime.now(),
              points, new_level, datetime.now()))
        await db.commit()
    
    return {
        "guild_id": guild_id,
        "user_id": user_id,
        "affection_points": points,
        "affection_level": new_level
    }


async def get_user_full_profile(guild_id: int, user_id: int) -> Dict[str, Any]:
    """Get complete user profile for admin viewing."""
    user = await get_user(guild_id, user_id) or {"user_id": user_id}
    affection = await get_affection(guild_id, user_id)
    facts = await get_facts_detailed(guild_id, user_id)
    aliases = await get_aliases(guild_id, user_id)
    
    return {
        **user,
        "affection": affection,
        "facts": facts,
        "aliases": aliases
    }
