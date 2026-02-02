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
import json
import re
from pathlib import Path
import aiosqlite
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone, timedelta, date
from contextlib import asynccontextmanager

from utils.logger import get_logger

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_db_path(value: Optional[str]) -> str:
    if not value:
        return str(BASE_DIR / "database.db")
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


def _resolve_data_dir(value: Optional[str]) -> Path:
    if not value:
        return BASE_DIR / "data"
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


DATA_DIR = _resolve_data_dir(os.getenv("DATABASE_DIR"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Global database (bot stats + registry)
GLOBAL_DATABASE_PATH = _resolve_db_path(os.getenv("GLOBAL_DATABASE_PATH") or str(DATA_DIR / "global.db"))

logger = get_logger(__name__)

_initialized_guilds: Set[int] = set()
_global_initialized = False


def get_guild_db_path(guild_id: int) -> str:
    return str(DATA_DIR / f"guild_{guild_id}.db")


@asynccontextmanager
async def guild_db(guild_id: int):
    await _ensure_guild_db(guild_id)
    async with aiosqlite.connect(get_guild_db_path(guild_id)) as db:
        yield db


@asynccontextmanager
async def global_db():
    await _ensure_global_db()
    async with aiosqlite.connect(GLOBAL_DATABASE_PATH) as db:
        yield db


async def _ensure_global_db() -> None:
    global _global_initialized
    if _global_initialized:
        return
    async with aiosqlite.connect(GLOBAL_DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                messages_processed INTEGER DEFAULT 0,
                commands_executed INTEGER DEFAULT 0,
                images_analyzed INTEGER DEFAULT 0,
                start_time TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_registry (
                guild_id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO bot_stats (id, start_time) VALUES (1, ?)
        """, (datetime.now(),))
        await db.commit()
    _global_initialized = True


async def _register_guild(guild_id: int) -> None:
    await _ensure_global_db()
    async with aiosqlite.connect(GLOBAL_DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO guild_registry (guild_id) VALUES (?)",
            (guild_id,),
        )
        await db.commit()


async def _ensure_guild_db(guild_id: int) -> None:
    if guild_id in _initialized_guilds:
        return
    await _ensure_global_db()
    await _register_guild(guild_id)

    async with aiosqlite.connect(get_guild_db_path(guild_id)) as db:
        await _init_guild_schema(db)
        await db.commit()
    _initialized_guilds.add(guild_id)


async def init_db() -> None:
    """
    Initialize the global database (bot stats + guild registry).
    Guild databases are created lazily on first use.
    """
    await _ensure_global_db()


async def init_guild_db(guild_id: int) -> None:
    """Initialize a specific guild database."""
    await _ensure_guild_db(guild_id)


async def get_registered_guild_ids() -> List[int]:
    """Return all guild IDs that have registered a database."""
    await _ensure_global_db()
    async with aiosqlite.connect(GLOBAL_DATABASE_PATH) as db:
        async with db.execute("SELECT guild_id FROM guild_registry") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def _init_guild_schema(db: aiosqlite.Connection) -> None:
    """
    Initialize the per-guild database schema and run migrations.
    """
    # Users table (global registry within this guild DB)
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
            evil_mode INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Guild-specific API configuration
    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            gemini_api_key TEXT,
            gemini_api_key_2 TEXT,
            gemini_api_key_3 TEXT,
            gemini_api_key_4 TEXT,
            gemini_api_key_5 TEXT,
            gemini_translate_key TEXT,
            gemini_translate_key_2 TEXT,
            gemini_translate_key_3 TEXT,
            gemini_translate_key_4 TEXT,
            gemini_translate_key_5 TEXT,
            gemini_summarize_key TEXT,
            gemini_summarize_key_2 TEXT,
            gemini_summarize_key_3 TEXT,
            gemini_summarize_key_4 TEXT,
            gemini_summarize_key_5 TEXT,
            gemini_profile_key TEXT,
            openrouter_api_key TEXT,
            openrouter_api_key_2 TEXT,
            openrouter_api_key_3 TEXT,
            openrouter_api_key_4 TEXT,
            openrouter_api_key_5 TEXT,
            gemini_model TEXT DEFAULT 'gemini-2.5-flash-lite',
            gemini_translate_model TEXT,
            gemini_summarize_model TEXT,
            gemini_key_type TEXT DEFAULT 'paid',
            openrouter_model TEXT DEFAULT 'cognitivecomputations/dolphin-mistral-24b-venice-edition:free',
            openrouter_fallback_models TEXT,
            evil_mode_enabled INTEGER DEFAULT 0,
            autorole_id INTEGER,
            autorole_enabled INTEGER DEFAULT 1,
            welcome_channel_id INTEGER,
            welcome_enabled INTEGER DEFAULT 1,
            welcome_message_template TEXT,
            dm_welcome_message TEXT,
            dm_welcome_enabled INTEGER DEFAULT 0,
            spam_timeout_enabled INTEGER DEFAULT 0,
            spam_max_messages INTEGER DEFAULT 8,
            spam_window_seconds INTEGER DEFAULT 10,
            spam_timeout_minutes INTEGER DEFAULT 5,
            mod_log_channel_id INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_admin_auth (
            guild_id INTEGER PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            password_version INTEGER DEFAULT 1
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_auth_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            password_version INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, user_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_config_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Staff roles (agentic permissions)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS staff_roles (
            guild_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            permission_level INTEGER NOT NULL,
            PRIMARY KEY (guild_id, role_id)
        )
    """)
    
    # ============================================
    # Phase 6: New Tables
    # ============================================
    
    # User affection tracking by mode (exclude mode_default)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_affection_by_mode (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            affection_points INTEGER DEFAULT 0,
            total_interactions INTEGER DEFAULT 0,
            last_interaction TIMESTAMP,
            affection_level TEXT DEFAULT 'stranger',
            PRIMARY KEY (guild_id, user_id, mode)
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

    # Hug/pat interaction cooldowns (UTC-based)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS interaction_cooldowns (
            guild_id INTEGER,
            user_id INTEGER,
            interaction_type TEXT,
            last_used TIMESTAMP,
            daily_count INTEGER DEFAULT 0,
            daily_reset DATE,
            PRIMARY KEY (guild_id, user_id, interaction_type)
        )
    """)

    # Guild-specific avatar overrides and rate limits
    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_avatar_config (
            guild_id INTEGER PRIMARY KEY,
            custom_avatar_path TEXT,
            last_updated TIMESTAMP,
            hourly_count INTEGER DEFAULT 0,
            hourly_reset TIMESTAMP
        )
    """)

    # Custom personas (per guild)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS custom_personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            mode_key TEXT NOT NULL,
            bio TEXT,
            avatar_path TEXT,
            banner_path TEXT,
            normal_prompt TEXT NOT NULL,
            evil_prompt TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            UNIQUE (mode_key),
            UNIQUE (guild_id, name)
        )
    """)

    # Migrate legacy uniqueness (name-only) to guild-scoped uniqueness if needed.
    try:
        async with db.execute("PRAGMA index_list(custom_personas)") as cursor:
            indexes = await cursor.fetchall()
        legacy_name_unique = False
        for index in indexes:
            index_name = index[1]
            is_unique = bool(index[2])
            if not is_unique:
                continue
            async with db.execute(f"PRAGMA index_info({index_name})") as icursor:
                cols = [row[2] for row in await icursor.fetchall()]
            if cols == ["name"]:
                legacy_name_unique = True
                break

        if legacy_name_unique:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS custom_personas_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    mode_key TEXT NOT NULL,
                    bio TEXT,
                    avatar_path TEXT,
                    banner_path TEXT,
                    normal_prompt TEXT NOT NULL,
                    evil_prompt TEXT,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    UNIQUE (mode_key),
                    UNIQUE (guild_id, name)
                )
            """)
            await db.execute(
                """
                INSERT INTO custom_personas_new
                    (id, guild_id, name, mode_key, bio, avatar_path, banner_path,
                     normal_prompt, evil_prompt, created_by, created_at, updated_at, is_active)
                SELECT
                    id, guild_id, name, mode_key, bio, avatar_path, banner_path,
                    normal_prompt, evil_prompt, created_by, created_at, updated_at, is_active
                FROM custom_personas
                """
            )
            await db.execute("DROP TABLE custom_personas")
            await db.execute("ALTER TABLE custom_personas_new RENAME TO custom_personas")
    except Exception:
        pass

    # Add birthday column if missing (migration)
    try:
        await db.execute("ALTER TABLE users ADD COLUMN birthday TEXT")
    except Exception:
        pass  # Column already exists

    # Add evil_mode column to server_config if missing (migration)
    try:
        await db.execute("ALTER TABLE server_config ADD COLUMN evil_mode INTEGER DEFAULT 0")
    except Exception:
        pass

    # Ensure new guild_config columns exist (migration)
    try:
        async with db.execute("PRAGMA table_info(guild_config)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        for column_name, column_type, default_value in [
            ("gemini_api_key_4", "TEXT", None),
            ("gemini_api_key_5", "TEXT", None),
            ("gemini_translate_key", "TEXT", None),
            ("gemini_translate_key_2", "TEXT", None),
            ("gemini_translate_key_3", "TEXT", None),
            ("gemini_translate_key_4", "TEXT", None),
            ("gemini_translate_key_5", "TEXT", None),
            ("gemini_summarize_key", "TEXT", None),
            ("gemini_summarize_key_2", "TEXT", None),
            ("gemini_summarize_key_3", "TEXT", None),
            ("gemini_summarize_key_4", "TEXT", None),
            ("gemini_summarize_key_5", "TEXT", None),
            ("gemini_profile_key", "TEXT", None),
            ("gemini_translate_model", "TEXT", None),
            ("gemini_summarize_model", "TEXT", None),
            ("gemini_key_type", "TEXT", "paid"),
            ("openrouter_api_key_2", "TEXT", None),
            ("openrouter_api_key_3", "TEXT", None),
            ("openrouter_api_key_4", "TEXT", None),
            ("openrouter_api_key_5", "TEXT", None),
            ("autorole_id", "INTEGER", None),
            ("autorole_enabled", "INTEGER", 1),
            ("welcome_channel_id", "INTEGER", None),
            ("welcome_enabled", "INTEGER", 1),
            ("welcome_message_template", "TEXT", None),
            ("dm_welcome_message", "TEXT", None),
            ("dm_welcome_enabled", "INTEGER", 0),
            ("spam_timeout_enabled", "INTEGER", 0),
            ("spam_max_messages", "INTEGER", 8),
            ("spam_window_seconds", "INTEGER", 10),
            ("spam_timeout_minutes", "INTEGER", 5),
            ("mod_log_channel_id", "INTEGER", None),
        ]:
            if column_name in columns:
                continue
            if default_value is None:
                await db.execute(f"ALTER TABLE guild_config ADD COLUMN {column_name} {column_type}")
            else:
                await db.execute(
                    f"ALTER TABLE guild_config ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
                )
    except Exception:
        pass

    # Add guild_id column to user_facts if missing (migration)
    try:
        await db.execute("ALTER TABLE user_facts ADD COLUMN guild_id INTEGER DEFAULT 0")
    except Exception:
        pass
    
    # ============================================
    # Phase 7: Enhanced Memory System Tables
    # ============================================
    
    # Add source tracking to user_facts (migration)
    try:
        await db.execute("ALTER TABLE user_facts ADD COLUMN source TEXT DEFAULT 'manual'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE user_facts ADD COLUMN learned_from_user_id INTEGER")
    except Exception:
        pass

    # Add guild_id column to user_aliases if missing (migration)
    try:
        await db.execute("ALTER TABLE user_aliases ADD COLUMN guild_id INTEGER DEFAULT 0")
    except Exception:
        pass

    # Add guild_id column to pending_facts if missing (migration)
    try:
        await db.execute("ALTER TABLE pending_facts ADD COLUMN guild_id INTEGER DEFAULT 0")
    except Exception:
        pass

    # Add last_asked_date to wellbeing_checks if missing (migration)
    try:
        await db.execute("ALTER TABLE wellbeing_checks ADD COLUMN last_asked_date TEXT")
    except Exception:
        pass
    
    # User aliases table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            alias TEXT NOT NULL,
            added_by_user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Pending facts table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS pending_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            about_user_id INTEGER NOT NULL,
            fact TEXT NOT NULL,
            learned_from_user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Gender roles table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS gender_roles (
            guild_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            gender TEXT NOT NULL,
            PRIMARY KEY (guild_id, role_id)
        )
    """)

    # Automod rules
    await db.execute("""
        CREATE TABLE IF NOT EXISTS automod_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            punishment_type TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 0,
            UNIQUE(guild_id, keyword)
        )
    """)

    # Starboard settings
    await db.execute("""
        CREATE TABLE IF NOT EXISTS starboard_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            emoji_trigger TEXT DEFAULT 'â­',
            emoji_triggers TEXT,
            emoji_mode TEXT DEFAULT 'list',
            threshold INTEGER DEFAULT 3,
            allow_self_star INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1
        )
    """)

    # Add starboard emoji list/mode columns if missing (migration)
    try:
        async with db.execute("PRAGMA table_info(starboard_settings)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "emoji_triggers" not in columns:
            await db.execute("ALTER TABLE starboard_settings ADD COLUMN emoji_triggers TEXT")
        if "emoji_mode" not in columns:
            await db.execute("ALTER TABLE starboard_settings ADD COLUMN emoji_mode TEXT DEFAULT 'list'")
    except Exception:
        pass

    # Starboard entries
    await db.execute("""
        CREATE TABLE IF NOT EXISTS starboard_entries (
            original_message_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            starboard_message_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            emoji_used TEXT,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP
        )
    """)

    # Starboard ignored channels
    await db.execute("""
        CREATE TABLE IF NOT EXISTS starboard_ignored_channels (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)

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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
        mode: One of "mode_default", "mode_femboy", "mode_tsundere", "mode_oneesan", or custom_*
        
    TODO:
        - [ ] Validate mode string
        - [ ] Emit event for mode change
    """
    valid_modes = ["mode_default", "mode_femboy", "mode_tsundere", "mode_oneesan"]
    if mode not in valid_modes and not mode.startswith("custom_"):
        raise ValueError(f"Invalid mode. Must be one of: {valid_modes} or custom_*")
    
    async with guild_db(guild_id) as db:
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
    mode = await get_server_mode(guild_id)
    if mode == "mode_default":
        return False

    async with guild_db(guild_id) as db:
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
    mode = await get_server_mode(guild_id)
    if mode == "mode_default":
        enabled = False

    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, bump_channel_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                bump_channel_id = ?,
                updated_at = ?
        """, (guild_id, channel_id, datetime.now(), channel_id, datetime.now()))
        await db.commit()



async def _ensure_bump_columns(guild_id: int) -> None:
    """Ensure bump_enabled and last_bump_time columns exist (migration)."""
    async with guild_db(guild_id) as db:
        async with db.execute("PRAGMA table_info(server_config)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        
        if "bump_enabled" not in columns:
            await db.execute("ALTER TABLE server_config ADD COLUMN bump_enabled INTEGER DEFAULT 0")
        if "last_bump_time" not in columns:
            await db.execute("ALTER TABLE server_config ADD COLUMN last_bump_time TIMESTAMP")
        await db.commit()


async def get_bump_config(guild_id: int) -> dict:
    """Get full bump configuration for a server."""
    await _ensure_bump_columns(guild_id)
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT bump_channel_id, bump_enabled, last_bump_time FROM server_config WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "channel_id": row[0],
                    "enabled": bool(row[1]) if row[1] is not None else False,
                    "last_bump_time": datetime.fromisoformat(row[2]) if row[2] else None
                }
            return {"channel_id": None, "enabled": False, "last_bump_time": None}


async def set_bump_enabled(guild_id: int, enabled: bool) -> None:
    """Enable or disable bump reminders for a server."""
    await _ensure_bump_columns(guild_id)
    async with guild_db(guild_id) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, bump_enabled, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                bump_enabled = ?,
                updated_at = ?
        """, (guild_id, int(enabled), datetime.now(), int(enabled), datetime.now()))
        await db.commit()


async def set_last_bump_time(guild_id: int, bump_time: datetime = None) -> None:
    """Set the last bump time for a server."""
    await _ensure_bump_columns(guild_id)
    bump_time = bump_time or datetime.now()
    async with guild_db(guild_id) as db:
        await db.execute("""
            INSERT INTO server_config (guild_id, last_bump_time, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                last_bump_time = ?,
                updated_at = ?
        """, (guild_id, bump_time.isoformat(), datetime.now(), bump_time.isoformat(), datetime.now()))
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

AFFECTION_TRACKED_MODES = (
    "mode_femboy",
    "mode_tsundere",
    "mode_oneesan",
)


def _calculate_level(points: int) -> str:
    """Calculate affection level from points."""
    level = "stranger"
    for threshold, name in AFFECTION_LEVELS:
        if points >= threshold:
            level = name
    return level


def _validate_affection_mode(mode: str) -> None:
    if mode not in AFFECTION_TRACKED_MODES:
        raise ValueError(f"Invalid affection mode: {mode}")


async def get_affection_by_mode(guild_id: int, user_id: int, mode: str) -> Dict[str, Any]:
    """Get user's affection data for a specific mode."""
    _validate_affection_mode(mode)
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
            (guild_id, user_id, mode),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "guild_id": guild_id,
                "user_id": user_id,
                "mode": mode,
                "affection_points": 0,
                "total_interactions": 0,
                "affection_level": "stranger",
            }


async def get_all_mode_affection(guild_id: int, user_id: int) -> Dict[str, Dict[str, Any]]:
    """Get user's affection data for all tracked modes."""
    result: Dict[str, Dict[str, Any]] = {}
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                result[row["mode"]] = dict(row)

    for mode in AFFECTION_TRACKED_MODES:
        if mode not in result:
            result[mode] = {
                "guild_id": guild_id,
                "user_id": user_id,
                "mode": mode,
                "affection_points": 0,
                "total_interactions": 0,
                "affection_level": "stranger",
            }
    return result


async def add_affection_to_mode(
    guild_id: int,
    user_id: int,
    mode: str,
    points: int = 1,
) -> Dict[str, Any]:
    """Add affection points for a specific mode."""
    _validate_affection_mode(mode)
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT affection_points, total_interactions FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
            (guild_id, user_id, mode),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            new_points = row[0] + points
            new_interactions = row[1] + 1
        else:
            new_points = points
            new_interactions = 1

        new_level = _calculate_level(new_points)

        await db.execute(
            """
            INSERT INTO user_affection_by_mode (guild_id, user_id, mode, affection_points, total_interactions, last_interaction, affection_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, mode) DO UPDATE SET
                affection_points = ?,
                total_interactions = ?,
                last_interaction = ?,
                affection_level = ?
            """,
            (
                guild_id,
                user_id,
                mode,
                new_points,
                new_interactions,
                datetime.now(),
                new_level,
                new_points,
                new_interactions,
                datetime.now(),
                new_level,
            ),
        )
        await db.commit()

        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "mode": mode,
            "affection_points": new_points,
            "total_interactions": new_interactions,
            "affection_level": new_level,
        }


async def set_affection_value_by_mode(
    guild_id: int,
    user_id: int,
    mode: str,
    points: int,
) -> Dict[str, Any]:
    """Set affection for a specific mode (admin use)."""
    _validate_affection_mode(mode)
    new_level = _calculate_level(points)
    async with guild_db(guild_id) as db:
        await db.execute(
            """
            INSERT INTO user_affection_by_mode (guild_id, user_id, mode, affection_points, total_interactions, last_interaction, affection_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, mode) DO UPDATE SET
                affection_points = ?,
                affection_level = ?,
                last_interaction = ?
            """,
            (
                guild_id,
                user_id,
                mode,
                points,
                0,
                datetime.now(),
                new_level,
                points,
                new_level,
                datetime.now(),
            ),
        )
        await db.commit()

    return {
        "guild_id": guild_id,
        "user_id": user_id,
        "mode": mode,
        "affection_points": points,
        "affection_level": new_level,
    }


async def reset_affection_by_mode(guild_id: int, user_id: int, mode: str) -> int:
    """Reset affection for a specific mode (admin use)."""
    _validate_affection_mode(mode)
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
            (guild_id, user_id, mode),
        )
        await db.commit()
        return cursor.rowcount


# ============================================
# Mood System Operations
# ============================================

async def get_mood(guild_id: int) -> Dict[str, Any]:
    """Get bot mood for a server."""
    async with guild_db(guild_id) as db:
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
    
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    
    async with guild_db(guild_id) as db:
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

async def add_reminder(user_id: int, guild_id: int, channel_id: int, 
                       message: str, remind_at: datetime) -> int:
    """Add a reminder and return its ID."""
    if guild_id is None:
        raise ValueError("guild_id is required for reminders.")
    async with guild_db(guild_id) as db:
        cursor = await db.execute("""
            INSERT INTO reminders (user_id, guild_id, channel_id, message, remind_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, guild_id, channel_id, message, remind_at))
        await db.commit()
        return cursor.lastrowid


async def get_user_reminders(user_id: int, guild_id: int) -> List[Dict[str, Any]]:
    """Get all active reminders for a user."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM reminders 
            WHERE user_id = ? AND completed = FALSE
            ORDER BY remind_at ASC
        """, (user_id,)) as cursor:
            return [dict(row) async for row in cursor]


async def get_due_reminders() -> List[Dict[str, Any]]:
    """Get all reminders that are due now."""
    due: List[Dict[str, Any]] = []
    for guild_id in await get_registered_guild_ids():
        async with guild_db(guild_id) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM reminders 
                WHERE remind_at <= ? AND completed = FALSE
            """, (datetime.now(),)) as cursor:
                due.extend([dict(row) async for row in cursor])
    return due


async def complete_reminder(reminder_id: int, guild_id: int) -> None:
    """Mark a reminder as completed."""
    async with guild_db(guild_id) as db:
        await db.execute(
            "UPDATE reminders SET completed = TRUE WHERE id = ?",
            (reminder_id,)
        )
        await db.commit()


async def delete_reminder(reminder_id: int, user_id: int, guild_id: int) -> bool:
    """Delete a reminder (must belong to user)."""
    async with guild_db(guild_id) as db:
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
    
    async with global_db() as db:
        await db.execute(f"""
            UPDATE bot_stats SET {stat_name} = {stat_name} + ? WHERE id = 1
        """, (amount,))
        await db.commit()


async def get_stats() -> Dict[str, Any]:
    """Get all bot statistics."""
    async with global_db() as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT alias FROM user_aliases WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_strict_alias(guild_id: int, user_id: int) -> Optional[str]:
    """
    Get a strict alias for a user (self-set).

    Strict alias format: "strict:<name>".
    """
    async with guild_db(guild_id) as db:
        async with db.execute(
            """SELECT alias FROM user_aliases
               WHERE guild_id = ? AND user_id = ? AND added_by_user_id = ?
                 AND alias LIKE ? COLLATE NOCASE
               ORDER BY id ASC LIMIT 1""",
            (guild_id, user_id, user_id, "strict:%")
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            alias = row[0]

    _, _, name = alias.partition(":")
    name = name.strip()
    return name or None


async def find_user_by_alias(guild_id: int, alias: str) -> Optional[int]:
    """Find a user ID by their alias (case-insensitive)."""
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT user_id FROM user_aliases WHERE guild_id = ? AND alias = ? COLLATE NOCASE",
            (guild_id, alias)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def delete_alias(guild_id: int, user_id: int, alias: str) -> bool:
    """Delete an alias for a user."""
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT last_asked_date FROM wellbeing_checks WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_last_wellbeing_date(guild_id: int, user_id: int, date_str: str) -> None:
    """Set the last wellbeing check date for a user (YYYY-MM-DD)."""
    async with guild_db(guild_id) as db:
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
    gender = gender.strip()
    if not gender:
        raise ValueError("Gender cannot be empty.")
    if len(gender) > 32:
        raise ValueError("Gender must be 32 characters or fewer.")
    gender = gender.lower()
    if gender == "clear":
        raise ValueError("Use the clear option to remove a gender role mapping.")

    async with guild_db(guild_id) as db:
        await db.execute("""
            INSERT INTO gender_roles (guild_id, role_id, gender)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, role_id) DO UPDATE SET
                gender = ?
        """, (guild_id, role_id, gender, gender))
        await db.commit()


async def delete_gender_role(guild_id: int, role_id: int) -> bool:
    """Delete a gender role mapping for a server."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM gender_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_gender_roles(guild_id: int) -> Dict[int, str]:
    """Get gender role mappings for a server."""
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT role_id, gender FROM gender_roles WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


# ============================================
# Automod Rules
# ============================================

async def add_automod_rule(
    guild_id: int,
    keyword: str,
    punishment_type: str,
    duration_minutes: int = 0
) -> None:
    """Add or update an automod rule for a guild."""
    keyword = keyword.strip().lower()
    punishment_type = punishment_type.strip().lower()
    async with guild_db(guild_id) as db:
        await db.execute(
            """INSERT INTO automod_rules (guild_id, keyword, punishment_type, duration_minutes)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(guild_id, keyword) DO UPDATE SET
                   punishment_type = excluded.punishment_type,
                   duration_minutes = excluded.duration_minutes""",
            (guild_id, keyword, punishment_type, duration_minutes),
        )
        await db.commit()


async def remove_automod_rule(guild_id: int, keyword: str) -> bool:
    """Remove an automod rule by keyword."""
    keyword = keyword.strip().lower()
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM automod_rules WHERE guild_id = ? AND keyword = ?",
            (guild_id, keyword),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_automod_rules(guild_id: int) -> List[Dict[str, Any]]:
    """Fetch all automod rules for a guild."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, keyword, punishment_type, duration_minutes FROM automod_rules WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ============================================
# Starboard Settings + Entries
# ============================================

def _parse_starboard_triggers(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [token for token in re.split(r"[\\s,]+", text) if token]


async def get_starboard_settings(guild_id: int) -> Optional[Dict[str, Any]]:
    """Get starboard settings for a guild, if configured."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM starboard_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            settings = dict(row)
            settings["emoji_triggers"] = _parse_starboard_triggers(settings.get("emoji_triggers"))
            emoji_mode = (settings.get("emoji_mode") or "").strip().lower()
            legacy_trigger = (settings.get("emoji_trigger") or "").strip()
            if not emoji_mode:
                if legacy_trigger.upper() == "ANY":
                    emoji_mode = "any"
                else:
                    emoji_mode = "list"
            if emoji_mode != "any" and not settings["emoji_triggers"] and legacy_trigger:
                settings["emoji_triggers"] = [legacy_trigger]
            settings["emoji_mode"] = emoji_mode
            return settings


async def upsert_starboard_settings(
    guild_id: int,
    channel_id: Optional[int],
    emoji_triggers: Optional[List[str]],
    threshold: int,
    allow_self_star: bool,
    enabled: bool = True,
    emoji_mode: str = "list",
) -> None:
    """Create or update starboard settings."""
    emoji_mode = (emoji_mode or "list").strip().lower()
    emoji_triggers = [str(item).strip() for item in (emoji_triggers or []) if str(item).strip()]
    if emoji_mode == "any":
        emoji_triggers = []
    else:
        emoji_mode = "list"
    threshold = max(1, int(threshold))

    if emoji_mode == "any":
        emoji_trigger = "ANY"
    else:
        emoji_trigger = emoji_triggers[0] if emoji_triggers else "â­"

    emoji_triggers_json = json.dumps(emoji_triggers, ensure_ascii=False)

    async with guild_db(guild_id) as db:
        await db.execute(
            """INSERT INTO starboard_settings
               (guild_id, channel_id, emoji_trigger, emoji_triggers, emoji_mode, threshold, allow_self_star, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET
                   channel_id = excluded.channel_id,
                   emoji_trigger = excluded.emoji_trigger,
                   emoji_triggers = excluded.emoji_triggers,
                   emoji_mode = excluded.emoji_mode,
                   threshold = excluded.threshold,
                   allow_self_star = excluded.allow_self_star,
                   enabled = excluded.enabled""",
            (
                guild_id,
                channel_id,
                emoji_trigger,
                emoji_triggers_json,
                emoji_mode,
                threshold,
                int(allow_self_star),
                int(enabled),
            ),
        )
        await db.commit()


async def set_starboard_enabled(guild_id: int, enabled: bool) -> None:
    """Enable or disable starboard for a guild."""
    async with guild_db(guild_id) as db:
        await db.execute(
            """INSERT INTO starboard_settings (guild_id, enabled)
               VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET enabled = excluded.enabled""",
            (guild_id, int(enabled)),
        )
        await db.commit()


async def add_starboard_ignored_channel(guild_id: int, channel_id: int) -> None:
    """Ignore a channel for starboard."""
    async with guild_db(guild_id) as db:
        await db.execute(
            "INSERT OR IGNORE INTO starboard_ignored_channels (guild_id, channel_id) VALUES (?, ?)",
            (guild_id, channel_id),
        )
        await db.commit()


async def remove_starboard_ignored_channel(guild_id: int, channel_id: int) -> bool:
    """Remove a channel from the starboard ignore list."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM starboard_ignored_channels WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_starboard_ignored_channels(guild_id: int) -> Set[int]:
    """Get ignored channel IDs for starboard."""
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT channel_id FROM starboard_ignored_channels WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0] for row in rows}


async def get_starboard_entry(guild_id: int, original_message_id: int) -> Optional[Dict[str, Any]]:
    """Get a starboard entry by original message ID."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT original_message_id, starboard_message_id, channel_id, emoji_used, is_deleted, deleted_at
               FROM starboard_entries WHERE guild_id = ? AND original_message_id = ?""",
            (guild_id, original_message_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def upsert_starboard_entry(
    guild_id: int,
    original_message_id: int,
    starboard_message_id: int,
    channel_id: int,
    emoji_used: Optional[str] = None,
) -> None:
    """Create or update a starboard entry."""
    async with guild_db(guild_id) as db:
        await db.execute(
            """INSERT INTO starboard_entries
               (original_message_id, guild_id, starboard_message_id, channel_id, emoji_used)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(original_message_id) DO UPDATE SET
                   starboard_message_id = excluded.starboard_message_id,
                   channel_id = excluded.channel_id,
                   emoji_used = COALESCE(excluded.emoji_used, starboard_entries.emoji_used)""",
            (original_message_id, guild_id, starboard_message_id, channel_id, emoji_used),
        )
        await db.commit()


async def mark_starboard_entry_deleted(guild_id: int, original_message_id: int) -> bool:
    """Mark a starboard entry as deleted (original message removed)."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            """UPDATE starboard_entries
               SET is_deleted = 1, deleted_at = ?
               WHERE guild_id = ? AND original_message_id = ?""",
            (datetime.now(), guild_id, original_message_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def clear_starboard_entry(guild_id: int, original_message_id: int) -> bool:
    """Delete a starboard entry record."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM starboard_entries WHERE guild_id = ? AND original_message_id = ?",
            (guild_id, original_message_id),
        )
        await db.commit()
        return cursor.rowcount > 0


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
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            """INSERT INTO user_facts (guild_id, user_id, fact, source, learned_from_user_id) 
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, fact, source, learned_from_user_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_facts_detailed(guild_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Get all facts about a user with full details."""
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
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
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            """INSERT INTO pending_facts 
               (guild_id, about_user_id, fact, learned_from_user_id, channel_id, message_id, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (guild_id, about_user_id, fact, learned_from_user_id, channel_id, message_id, expires_at)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_fact(guild_id: int, pending_id: int) -> Optional[Dict[str, Any]]:
    """Get a pending fact by ID."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pending_facts WHERE id = ?",
            (pending_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def confirm_pending_fact(guild_id: int, pending_id: int) -> bool:
    """Confirm a pending fact and move it to user_facts."""
    pending = await get_pending_fact(guild_id, pending_id)
    if not pending:
        return False
    
    # Check if expired
    if datetime.fromisoformat(pending["expires_at"]) < datetime.now():
        await delete_pending_fact(guild_id, pending_id)
        return False
    
    # Move to user_facts
    await add_fact_with_source(
        pending["guild_id"],
        pending["about_user_id"],
        pending["fact"],
        source="learned",
        learned_from_user_id=pending["learned_from_user_id"]
    )
    await delete_pending_fact(guild_id, pending_id)
    return True


async def delete_pending_fact(guild_id: int, pending_id: int) -> bool:
    """Delete a pending fact."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM pending_facts WHERE id = ?",
            (pending_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def cleanup_expired_pending_facts(guild_id: int) -> int:
    """Delete all expired pending facts."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM pending_facts WHERE expires_at < ?",
            (datetime.now(),)
        )
        await db.commit()
        return cursor.rowcount


# ============================================
# Interaction Cooldowns (Hug/Pat)
# ============================================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


async def check_interaction_limit(guild_id: int, user_id: int, interaction_type: str) -> tuple[bool, str]:
    """Returns (can_interact, reason_if_blocked). reason_if_blocked is "hourly" or "daily"."""
    now = _utcnow()
    today = now.date()

    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT last_used, daily_count, daily_reset
               FROM interaction_cooldowns
               WHERE guild_id = ? AND user_id = ? AND interaction_type = ?""",
            (guild_id, user_id, interaction_type),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            daily_count = int(row["daily_count"] or 0)
            daily_reset = _parse_date(row["daily_reset"])
            if daily_reset != today:
                daily_count = 0
                daily_reset = today
                await db.execute(
                    """UPDATE interaction_cooldowns
                       SET daily_count = ?, daily_reset = ?
                       WHERE guild_id = ? AND user_id = ? AND interaction_type = ?""",
                    (daily_count, today.isoformat(), guild_id, user_id, interaction_type),
                )
                await db.commit()

            last_used = _parse_timestamp(row["last_used"])
            if last_used and (now - last_used) < timedelta(hours=1):
                return False, "hourly"
            if daily_count >= 3:
                return False, "daily"
            return True, "ok"

        await db.execute(
            """INSERT INTO interaction_cooldowns
               (guild_id, user_id, interaction_type, last_used, daily_count, daily_reset)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (guild_id, user_id, interaction_type, None, 0, today.isoformat()),
        )
        await db.commit()
        return True, "ok"


async def record_interaction(guild_id: int, user_id: int, interaction_type: str) -> None:
    """Update last_used, daily_count, daily_reset (UTC)."""
    now = _utcnow()
    today = now.date()

    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT daily_count, daily_reset
               FROM interaction_cooldowns
               WHERE guild_id = ? AND user_id = ? AND interaction_type = ?""",
            (guild_id, user_id, interaction_type),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            daily_count = int(row["daily_count"] or 0)
            daily_reset = _parse_date(row["daily_reset"])
            if daily_reset != today:
                daily_count = 0
            daily_count += 1

            await db.execute(
                """UPDATE interaction_cooldowns
                   SET last_used = ?, daily_count = ?, daily_reset = ?
                   WHERE guild_id = ? AND user_id = ? AND interaction_type = ?""",
                (
                    now.isoformat(),
                    daily_count,
                    today.isoformat(),
                    guild_id,
                    user_id,
                    interaction_type,
                ),
            )
        else:
            await db.execute(
                """INSERT INTO interaction_cooldowns
                   (guild_id, user_id, interaction_type, last_used, daily_count, daily_reset)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (guild_id, user_id, interaction_type, now.isoformat(), 1, today.isoformat()),
            )
        await db.commit()


# ============================================
# Guild Avatar Configuration
# ============================================

async def get_guild_avatar_path(guild_id: int) -> Optional[str]:
    """Get the custom avatar path for a guild, if any."""
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT custom_avatar_path FROM guild_avatar_config WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_guild_avatar_path(guild_id: int, path: Optional[str]) -> None:
    """Set or clear the custom avatar path for a guild."""
    async with guild_db(guild_id) as db:
        await db.execute(
            """INSERT INTO guild_avatar_config (guild_id, custom_avatar_path)
               VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET custom_avatar_path = ?""",
            (guild_id, path, path),
        )
        await db.commit()


async def can_update_guild_avatar(guild_id: int) -> tuple[bool, str]:
    """Return (can_update, reason). reason is 'hourly' when blocked."""
    now = _utcnow()

    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT hourly_count, hourly_reset FROM guild_avatar_config WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            hourly_count = int(row["hourly_count"] or 0)
            hourly_reset = _parse_timestamp(row["hourly_reset"])
            if hourly_reset is None or (now - hourly_reset) >= timedelta(hours=1):
                hourly_count = 0
                hourly_reset = now
                await db.execute(
                    """UPDATE guild_avatar_config
                       SET hourly_count = ?, hourly_reset = ?
                       WHERE guild_id = ?""",
                    (hourly_count, hourly_reset.isoformat(), guild_id),
                )
                await db.commit()
            if hourly_count >= 2:
                return False, "hourly"
            return True, "ok"

        await db.execute(
            """INSERT INTO guild_avatar_config (guild_id, hourly_count, hourly_reset)
               VALUES (?, ?, ?)""",
            (guild_id, 0, now.isoformat()),
        )
        await db.commit()
        return True, "ok"


async def record_guild_avatar_update(guild_id: int) -> None:
    """Record a successful avatar update and increment the hourly count."""
    now = _utcnow()

    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT hourly_count, hourly_reset FROM guild_avatar_config WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            hourly_count = int(row["hourly_count"] or 0)
            hourly_reset = _parse_timestamp(row["hourly_reset"])
            if hourly_reset is None or (now - hourly_reset) >= timedelta(hours=1):
                hourly_count = 0
                hourly_reset = now
            hourly_count += 1
            await db.execute(
                """UPDATE guild_avatar_config
                   SET last_updated = ?, hourly_count = ?, hourly_reset = ?
                   WHERE guild_id = ?""",
                (now.isoformat(), hourly_count, hourly_reset.isoformat(), guild_id),
            )
        else:
            await db.execute(
                """INSERT INTO guild_avatar_config
                   (guild_id, last_updated, hourly_count, hourly_reset)
                   VALUES (?, ?, ?, ?)""",
                (guild_id, now.isoformat(), 1, now.isoformat()),
            )
        await db.commit()


# ============================================
# Custom Personas
# ============================================

def sanitize_persona_name(name: str) -> str:
    """Normalize persona names for mode keys and file paths."""
    if not name:
        return ""
    value = name.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def build_custom_mode_key(guild_id: int, name: str) -> str:
    """Build the custom mode key for a guild persona."""
    slug = sanitize_persona_name(name)
    return f"custom_{guild_id}_{slug}" if slug else ""


async def create_custom_persona(
    guild_id: int,
    name: str,
    mode_key: str,
    bio: Optional[str],
    avatar_path: Optional[str],
    banner_path: Optional[str],
    normal_prompt: str,
    evil_prompt: Optional[str],
    created_by: int,
) -> int:
    """Create a custom persona and return its row id."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            """
            INSERT INTO custom_personas
                (guild_id, name, mode_key, bio, avatar_path, banner_path,
                 normal_prompt, evil_prompt, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                name,
                mode_key,
                bio,
                avatar_path,
                banner_path,
                normal_prompt,
                evil_prompt,
                created_by,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid or 0)


async def get_custom_persona_by_mode_key(guild_id: int, mode_key: str) -> Optional[Dict[str, Any]]:
    """Fetch a custom persona by its mode key."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM custom_personas
            WHERE guild_id = ? AND mode_key = ? AND is_active = 1
            """,
            (guild_id, mode_key),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_custom_persona_by_name(guild_id: int, name: str) -> Optional[Dict[str, Any]]:
    """Fetch a custom persona by name (case-insensitive)."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM custom_personas
            WHERE guild_id = ? AND lower(name) = lower(?) AND is_active = 1
            """,
            (guild_id, name),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_guild_custom_personas(guild_id: int) -> List[Dict[str, Any]]:
    """Return all active custom personas for a guild."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM custom_personas
            WHERE guild_id = ? AND is_active = 1
            ORDER BY created_at DESC
            """,
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_custom_persona(
    guild_id: int,
    mode_key: str,
    **updates: Any,
) -> bool:
    """Update a custom persona. Returns True if a row was updated."""
    if not updates:
        return False

    allowed = {
        "name",
        "bio",
        "avatar_path",
        "banner_path",
        "normal_prompt",
        "evil_prompt",
        "updated_at",
        "is_active",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False

    filtered["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{key} = ?" for key in filtered.keys()])
    values = list(filtered.values())

    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            f"""
            UPDATE custom_personas
            SET {set_clause}
            WHERE guild_id = ? AND mode_key = ?
            """,
            (*values, guild_id, mode_key),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_custom_persona(guild_id: int, mode_key: str) -> bool:
    """Delete a custom persona by mode key."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM custom_personas WHERE guild_id = ? AND mode_key = ?",
            (guild_id, mode_key),
        )
        await db.commit()
        return cursor.rowcount > 0


# ============================================
# Admin Operations
# ============================================

async def reset_user_data(
    guild_id: int,
    user_id: int,
    reset_type: str = "all",
    mode: str = None,
) -> Dict[str, int]:
    """Reset user data. reset_type: 'all', 'facts', 'affection', 'aliases'"""
    deleted = {"facts": 0, "affection": 0, "aliases": 0}
    
    async with guild_db(guild_id) as db:
        if reset_type in ("all", "facts"):
            cursor = await db.execute(
                "DELETE FROM user_facts WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            )
            deleted["facts"] = cursor.rowcount
        
        if reset_type in ("all", "affection"):
            if reset_type == "affection":
                if not mode:
                    raise ValueError("mode is required when reset_type=affection")
                _validate_affection_mode(mode)
                cursor = await db.execute(
                    "DELETE FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
                    (guild_id, user_id, mode),
                )
                deleted["affection"] = cursor.rowcount
            else:
                cursor = await db.execute(
                    "DELETE FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
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


async def get_user_full_profile(guild_id: int, user_id: int) -> Dict[str, Any]:
    """Get complete user profile for admin viewing."""
    user = await get_user(guild_id, user_id) or {"user_id": user_id}
    affection_by_mode = await get_all_mode_affection(guild_id, user_id)
    facts = await get_facts_detailed(guild_id, user_id)
    aliases = await get_aliases(guild_id, user_id)
    
    return {
        **user,
        "affection_by_mode": affection_by_mode,
        "facts": facts,
        "aliases": aliases
    }


# ============================================
# Agentic Staff Role Operations
# ============================================

async def add_staff_role(guild_id: int, role_id: int, permission_level: int) -> None:
    """Add or update a staff role with a permission level."""
    async with guild_db(guild_id) as db:
        await db.execute(
            """
            INSERT INTO staff_roles (guild_id, role_id, permission_level)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, role_id) DO UPDATE SET
                permission_level = ?
            """,
            (guild_id, role_id, permission_level, permission_level),
        )
        await db.commit()


async def remove_staff_role(guild_id: int, role_id: int) -> bool:
    """Remove a staff role. Returns True if deleted."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM staff_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_staff_roles(guild_id: int) -> List[tuple[int, int]]:
    """Get all staff roles and permission levels."""
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT role_id, permission_level FROM staff_roles WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]


async def get_mod_log_channel_id(guild_id: int) -> Optional[int]:
    """Get the mod-log channel ID for a guild."""
    config = await get_guild_config(guild_id)
    channel_id = config.get("mod_log_channel_id")
    return channel_id if channel_id else None


async def set_mod_log_channel_id(guild_id: int, channel_id: Optional[int]) -> None:
    """Set or clear the mod-log channel ID for a guild."""
    await update_guild_config(guild_id, {"mod_log_channel_id": channel_id})


async def get_autorole_config(guild_id: int) -> Dict[str, Any]:
    """Get autorole configuration for a guild."""
    config = await get_guild_config(guild_id)
    enabled = config.get("autorole_enabled")
    return {
        "autorole_id": config.get("autorole_id"),
        "autorole_enabled": True if enabled is None else bool(enabled),
    }


async def set_autorole_id(guild_id: int, role_id: Optional[int]) -> None:
    """Set or clear autorole ID."""
    await update_guild_config(guild_id, {"autorole_id": role_id})


async def set_autorole_enabled(guild_id: int, enabled: bool) -> None:
    """Enable or disable autorole."""
    await update_guild_config(guild_id, {"autorole_enabled": int(enabled)})


async def get_welcome_config(guild_id: int) -> Dict[str, Any]:
    """Get welcome configuration for a guild."""
    config = await get_guild_config(guild_id)
    enabled = config.get("welcome_enabled")
    return {
        "welcome_channel_id": config.get("welcome_channel_id"),
        "welcome_enabled": True if enabled is None else bool(enabled),
        "welcome_message_template": config.get("welcome_message_template"),
    }


async def set_welcome_channel_id(guild_id: int, channel_id: Optional[int]) -> None:
    """Set or clear the welcome channel ID."""
    await update_guild_config(guild_id, {"welcome_channel_id": channel_id})


async def set_welcome_enabled(guild_id: int, enabled: bool) -> None:
    """Enable or disable welcome messages."""
    await update_guild_config(guild_id, {"welcome_enabled": int(enabled)})


async def set_welcome_message_template(guild_id: int, template: Optional[str]) -> None:
    """Set or clear the welcome message template for a guild."""
    await update_guild_config(guild_id, {"welcome_message_template": template})


async def get_dm_welcome_message(guild_id: int) -> Optional[str]:
    """Get the DM welcome message for a guild."""
    config = await get_guild_config(guild_id)
    return config.get("dm_welcome_message")


async def set_dm_welcome_message(guild_id: int, message: Optional[str]) -> None:
    """Set or clear the DM welcome message for a guild."""
    await update_guild_config(guild_id, {"dm_welcome_message": message})


async def get_dm_welcome_enabled(guild_id: int) -> bool:
    """Return whether DM welcomes are enabled for a guild."""
    config = await get_guild_config(guild_id)
    enabled = config.get("dm_welcome_enabled")
    return bool(enabled) if enabled is not None else False


async def set_dm_welcome_enabled(guild_id: int, enabled: bool) -> None:
    """Enable or disable DM welcome messages for a guild."""
    await update_guild_config(guild_id, {"dm_welcome_enabled": int(enabled)})


async def get_spam_config(guild_id: int) -> Dict[str, Any]:
    """Get automod spam/timeout configuration for a guild."""
    config = await get_guild_config(guild_id)
    return {
        "spam_timeout_enabled": bool(config.get("spam_timeout_enabled") or 0),
        "spam_max_messages": int(config.get("spam_max_messages") or 0),
        "spam_window_seconds": int(config.get("spam_window_seconds") or 0),
        "spam_timeout_minutes": int(config.get("spam_timeout_minutes") or 0),
    }


async def set_spam_config(guild_id: int, updates: Dict[str, Any]) -> None:
    """Update spam automod configuration fields."""
    if not updates:
        return
    await update_guild_config(guild_id, updates)


# ============================================
# Guild API Config Operations
# ============================================

GUILD_CONFIG_FIELDS: Set[str] = {
    "gemini_api_key",
    "gemini_api_key_2",
    "gemini_api_key_3",
    "gemini_api_key_4",
    "gemini_api_key_5",
    "gemini_translate_key",
    "gemini_translate_key_2",
    "gemini_translate_key_3",
    "gemini_translate_key_4",
    "gemini_translate_key_5",
    "gemini_summarize_key",
    "gemini_summarize_key_2",
    "gemini_summarize_key_3",
    "gemini_summarize_key_4",
    "gemini_summarize_key_5",
    "gemini_profile_key",
    "openrouter_api_key",
    "openrouter_api_key_2",
    "openrouter_api_key_3",
    "openrouter_api_key_4",
    "openrouter_api_key_5",
    "gemini_model",
    "gemini_translate_model",
    "gemini_summarize_model",
    "gemini_key_type",
    "openrouter_model",
    "openrouter_fallback_models",
    "evil_mode_enabled",
    "autorole_id",
    "autorole_enabled",
    "welcome_channel_id",
    "welcome_enabled",
    "welcome_message_template",
    "dm_welcome_message",
    "dm_welcome_enabled",
    "spam_timeout_enabled",
    "spam_max_messages",
    "spam_window_seconds",
    "spam_timeout_minutes",
    "mod_log_channel_id",
}


async def get_guild_config(guild_id: int) -> Dict[str, Any]:
    """Fetch guild API configuration (creates default row if missing)."""
    async with guild_db(guild_id) as db:
        await db.execute(
            "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)",
            (guild_id,),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def update_guild_config(guild_id: int, updates: Dict[str, Any]) -> None:
    """Update guild configuration fields and touch updated_at."""
    if not updates:
        return
    filtered = {k: v for k, v in updates.items() if k in GUILD_CONFIG_FIELDS}
    if not filtered:
        return

    now = datetime.now()
    columns = ["guild_id", *filtered.keys(), "updated_at"]
    placeholders = ", ".join(["?"] * len(columns))
    insert_values = [guild_id, *filtered.values(), now]

    set_clause = ", ".join(
        [f"{col} = excluded.{col}" for col in filtered.keys()] + ["updated_at = excluded.updated_at"]
    )

    async with guild_db(guild_id) as db:
        await db.execute(
            f"INSERT INTO guild_config ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {set_clause}",
            insert_values,
        )
        await db.commit()


async def clear_guild_keys(guild_id: int) -> None:
    """Clear all stored API keys for a guild."""
    await update_guild_config(
        guild_id,
        {
            "gemini_api_key": None,
            "gemini_api_key_2": None,
            "gemini_api_key_3": None,
            "gemini_api_key_4": None,
            "gemini_api_key_5": None,
            "gemini_translate_key": None,
            "gemini_translate_key_2": None,
            "gemini_translate_key_3": None,
            "gemini_translate_key_4": None,
            "gemini_translate_key_5": None,
            "gemini_summarize_key": None,
            "gemini_summarize_key_2": None,
            "gemini_summarize_key_3": None,
            "gemini_summarize_key_4": None,
            "gemini_summarize_key_5": None,
            "gemini_profile_key": None,
            "openrouter_api_key": None,
            "openrouter_api_key_2": None,
            "openrouter_api_key_3": None,
            "openrouter_api_key_4": None,
            "openrouter_api_key_5": None,
        },
    )


async def add_guild_config_audit(
    guild_id: int,
    user_id: int,
    action: str,
    field: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> None:
    """Record a config change event for auditing."""
    async with guild_db(guild_id) as db:
        await db.execute(
            """
            INSERT INTO guild_config_audit
                (guild_id, user_id, action, field, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, action, field, old_value, new_value),
        )
        await db.commit()


async def cleanup_guild_audit(guild_id: int, max_age_days: int = 90) -> int:
    """Prune audit entries older than max_age_days."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM guild_config_audit WHERE created_at < datetime('now', ?)",
            (f"-{max_age_days} days",),
        )
        await db.commit()
        return cursor.rowcount

