from __future__ import annotations

from typing import Optional

import discord

from utils.expression_cache import ExpressionRecord, get_expression_service


async def get_emojis(bot, guild: Optional[discord.Guild]) -> list[ExpressionRecord]:
    service = get_expression_service(bot)
    if service is None or guild is None:
        return []
    return await service.get_guild_emojis(guild)


async def get_stickers(bot, guild: Optional[discord.Guild]) -> list[ExpressionRecord]:
    service = get_expression_service(bot)
    if service is None or guild is None:
        return []
    return await service.get_guild_stickers(guild)


async def pick_emoji(
    bot,
    guild: Optional[discord.Guild],
    query: Optional[str] = None,
) -> Optional[ExpressionRecord]:
    service = get_expression_service(bot)
    if service is None or guild is None:
        return None
    return await service.select_guild_emoji(guild, query if query else None)


async def pick_sticker(
    bot,
    guild: Optional[discord.Guild],
    query: Optional[str] = None,
) -> Optional[ExpressionRecord]:
    service = get_expression_service(bot)
    if service is None or guild is None:
        return None
    return await service.select_guild_sticker(guild, query if query else None)
