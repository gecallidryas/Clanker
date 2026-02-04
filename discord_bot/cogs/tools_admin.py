from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import get_guild_config
from utils.tool_flags import DEFAULT_FLAG_VALUES, get_tool_flag
from utils.tool_registry import get_available_tools, list_tools, register_builtin_tools
from utils.i18n import t


class ToolsAdmin(commands.Cog):
    tools_group = app_commands.Group(name="tools", description="Tool status and configuration")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        register_builtin_tools()

    @tools_group.command(name="status", description="Show tool availability for this server.")
    async def tools_status(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        config = await get_guild_config(interaction.guild.id)
        tools = list_tools()
        enabled_tools = get_available_tools(config)
        enabled_names = {tool.name for tool in enabled_tools}

        locale = str(interaction.locale) if interaction.locale else "en"
        embed = discord.Embed(title=t("tools.status.title", locale), color=discord.Color.blue())
        embed.add_field(
            name=t("tools.status.enabled", locale),
            value=", ".join(sorted(enabled_names)) if enabled_names else "None",
            inline=False,
        )

        flag_lines = []
        for tool in tools:
            flag = tool.feature_flag or get_tool_flag(tool.name)
            if not flag:
                continue
            value = config.get(flag)
            if value is None:
                value = DEFAULT_FLAG_VALUES.get(flag, 1)
            status = "ON" if bool(int(value)) else "OFF"
            if flag == "rag_enabled":
                if str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() not in {"1", "true", "yes", "on"}:
                    status = "OFF (env)"
            flag_lines.append(f"{flag}: {status}")
        if flag_lines:
            embed.add_field(
                name=t("tools.status.flags", locale),
                value="\n".join(sorted(set(flag_lines))),
                inline=False,
            )

        disabled = [tool.name for tool in tools if tool.name not in enabled_names]
        if disabled:
            embed.add_field(
                name=t("tools.status.disabled", locale),
                value=", ".join(sorted(disabled)),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ToolsAdmin(bot))
