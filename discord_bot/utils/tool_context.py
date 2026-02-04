from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import discord
from discord.ext import commands


@dataclass(slots=True)
class ToolContext:
    bot: commands.Bot
    guild: discord.Guild
    channel: discord.abc.Messageable
    user: discord.Member
    message: Optional[discord.Message]
    guild_config: dict[str, Any]
    locale: str = "en"
