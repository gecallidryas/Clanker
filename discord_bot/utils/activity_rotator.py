from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import discord

from utils.api_manager import generate_gemini_with_key
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_INTERVAL_SECONDS = 3600
DEFAULT_MODEL = "gemini-2.5-flash-lite"

DEFAULT_ACTIVITIES: list[tuple[discord.ActivityType, str]] = [
    (discord.ActivityType.playing, "🎮 War Thunder"),
    (discord.ActivityType.playing, "🎮 Minecraft"),
    (discord.ActivityType.playing, "🎮 Stardew Valley"),
    (discord.ActivityType.playing, "🎮 Valorant"),
    (discord.ActivityType.playing, "🎮 Fortnite"),
    (discord.ActivityType.playing, "🎮 Apex Legends"),
    (discord.ActivityType.playing, "🎮 Rocket League"),
    (discord.ActivityType.playing, "🎮 Genshin Impact"),
    (discord.ActivityType.playing, "🎮 Honkai: Star Rail"),
    (discord.ActivityType.playing, "🎮 Overwatch 2"),
    (discord.ActivityType.playing, "🎮 League of Legends"),
    (discord.ActivityType.playing, "🎮 Hades"),
    (discord.ActivityType.playing, "🎮 Dead Cells"),
    (discord.ActivityType.playing, "🎮 Baldur's Gate 3"),
    (discord.ActivityType.playing, "🎮 Helldivers 2"),
    (discord.ActivityType.playing, "🎮 Deep Rock Galactic"),
    (discord.ActivityType.playing, "🎮 Sea of Thieves"),
    (discord.ActivityType.playing, "🎮 Terraria"),
    (discord.ActivityType.playing, "🎮 Random co-op"),
    (discord.ActivityType.watching, "▶️ YouTube"),
    (discord.ActivityType.watching, "▶️ creator highlights"),
    (discord.ActivityType.watching, "🎬 anime clips"),
    (discord.ActivityType.watching, "📺 Twitch streams"),
    (discord.ActivityType.listening, "🎵 Spotify"),
    (discord.ActivityType.listening, "🎵 lo-fi beats"),
    (discord.ActivityType.listening, "🎵 game OSTs"),
]


def is_activity_rotator_enabled() -> bool:
    raw = os.getenv("ACTIVITY_RANDOMIZER_ENABLED")
    if raw is None:
        return True
    raw = raw.strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _parse_interval() -> int:
    raw = (os.getenv("ACTIVITY_RANDOMIZER_INTERVAL_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_INTERVAL_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_INTERVAL_SECONDS
    return max(300, value)


def _sanitize_activity_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        return ""
    if len(name) > 128:
        name = name[:128].rstrip()
    return name


def _parse_gemini_lines(text: str) -> list[tuple[discord.ActivityType, str]]:
    activities: list[tuple[discord.ActivityType, str]] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip().strip("-•").strip()
        if not line:
            continue
        if "|" in line:
            type_token, name = [part.strip() for part in line.split("|", 1)]
        elif ":" in line:
            type_token, name = [part.strip() for part in line.split(":", 1)]
        else:
            type_token, name = "PLAYING", line
        type_token = type_token.upper()
        activity_type = {
            "PLAYING": discord.ActivityType.playing,
            "LISTENING": discord.ActivityType.listening,
            "WATCHING": discord.ActivityType.watching,
        }.get(type_token, discord.ActivityType.playing)
        name = _sanitize_activity_name(name)
        if name:
            activities.append((activity_type, name))
    return activities


def _build_prompt() -> str:
    return (
        "Create 20 short Discord activity lines for a bot. "
        "Use ONLY these formats per line: "
        "PLAYING | <text>, LISTENING | <text>, WATCHING | <text>. "
        "Include simple logo emojis like ▶️, 🎵, 🎮, 📺 where appropriate. "
        "Mix YouTube, Spotify, Twitch, and popular/varied games. "
        "Keep each line under 60 characters after the separator."
    )


@dataclass
class ActivityRotator:
    bot: discord.Client
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        self.interval_seconds = _parse_interval()
        self._pool: list[tuple[discord.ActivityType, str]] = []
        self._last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._last_choice: Optional[tuple[discord.ActivityType, str]] = None

    async def refresh_pool(self, force: bool = False) -> None:
        async with self._lock:
            now = datetime.now(timezone.utc)
            if not force and self._last_refresh and (now - self._last_refresh) < timedelta(hours=6):
                return

            items = list(DEFAULT_ACTIVITIES)
            gemini_key = (os.getenv("GEMINI_ACTIVITY_KEY") or "").strip()
            if gemini_key:
                model = (os.getenv("GEMINI_ACTIVITY_MODEL") or DEFAULT_MODEL).strip()
                try:
                    text, _ = await generate_gemini_with_key(
                        gemini_key,
                        model,
                        _build_prompt(),
                        request_timeout=20.0,
                    )
                    generated = _parse_gemini_lines(text)
                    if generated:
                        items.extend(generated)
                except Exception as exc:
                    logger.warning("Activity generator failed: %s", exc)

            random.shuffle(items)
            self._pool = items
            self._last_refresh = now

    async def next_activity(self) -> Optional[discord.Activity]:
        needs_refresh = False
        async with self._lock:
            if not self._pool:
                needs_refresh = True

        if needs_refresh:
            await self.refresh_pool(force=True)

        async with self._lock:
            if not self._pool:
                self._pool = list(DEFAULT_ACTIVITIES)
                random.shuffle(self._pool)

            choice = self._pool.pop(0)
            if self._last_choice and choice == self._last_choice and self._pool:
                choice = self._pool.pop(0)
            self._last_choice = choice

        activity_type, name = choice
        return discord.Activity(type=activity_type, name=name)
