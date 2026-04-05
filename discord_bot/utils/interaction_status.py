from __future__ import annotations

from typing import Optional

import discord

from utils.db_handler import get_custom_persona_by_mode_key, get_server_mode


async def get_mode_display_name(guild_id: Optional[int], mode_key: Optional[str] = None) -> str:
    resolved_mode = mode_key
    if resolved_mode is None:
        resolved_mode = await get_server_mode(guild_id) if guild_id else "mode_default"

    if resolved_mode == "mode_default":
        return "Clanker"
    if resolved_mode == "mode_oneesan":
        return "Yumi"
    if resolved_mode and resolved_mode.startswith("custom_") and guild_id:
        persona = await get_custom_persona_by_mode_key(guild_id, resolved_mode)
        if persona and persona.get("name"):
            return str(persona["name"]).strip()
    return "Femmy"


async def send_mode_thinking(
    interaction: discord.Interaction,
    *,
    ephemeral: bool = False,
    mode_key: Optional[str] = None,
) -> str:
    guild_id = interaction.guild.id if interaction.guild else None
    display_name = await get_mode_display_name(guild_id, mode_key)
    await interaction.response.send_message(
        f"{display_name} is thinking...",
        ephemeral=ephemeral,
    )
    return display_name
