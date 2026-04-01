from __future__ import annotations

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    get_stats,
    get_guild_stats,
    get_top_guilds_by_stat,
    increment_stat,
    increment_guild_stat,
)
from utils.i18n import get_locale_from_guild, get_locale_from_interaction, t


class Usage(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.start_time = datetime.now()

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        if ctx.guild:
            await increment_guild_stat(ctx.guild.id, "commands_executed")

    @commands.Cog.listener()
    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: Optional[app_commands.Command] = None,
    ):
        if interaction.guild:
            await increment_stat("commands_executed", guild_id=interaction.guild.id)

    @app_commands.command(name="usage", description="Display usage dashboard.")
    async def usage_dashboard(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                t("common.server_only", get_locale_from_interaction(interaction)),
                ephemeral=True,
            )
            return

        locale = get_locale_from_interaction(interaction)
        global_stats = await get_stats()
        guild_stats = await get_guild_stats(interaction.guild.id)
        top_guilds = await get_top_guilds_by_stat("messages_processed", limit=5)

        embed = discord.Embed(
            title=t("usage.dashboard.title", locale),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name=t("usage.dashboard.global", locale),
            value=(
                f"{t('usage.dashboard.messages', locale)}: {global_stats.get('messages_processed', 0):,}\n"
                f"{t('usage.dashboard.commands', locale)}: {global_stats.get('commands_executed', 0):,}\n"
                f"{t('usage.dashboard.images', locale)}: {global_stats.get('images_analyzed', 0):,}"
            ),
            inline=False,
        )
        embed.add_field(
            name=t("usage.dashboard.guild", locale),
            value=(
                f"{t('usage.dashboard.messages', locale)}: {guild_stats.get('messages_processed', 0):,}\n"
                f"{t('usage.dashboard.commands', locale)}: {guild_stats.get('commands_executed', 0):,}\n"
                f"{t('usage.dashboard.images', locale)}: {guild_stats.get('images_analyzed', 0):,}"
            ),
            inline=False,
        )

        if top_guilds:
            lines = []
            for row in top_guilds:
                guild = self.bot.get_guild(int(row.get("guild_id")))
                name = guild.name if guild else f"Guild {row.get('guild_id')}"
                lines.append(f"- {name}: {row.get('messages_processed', 0):,}")
            embed.add_field(
                name=t("usage.dashboard.top_guilds", locale),
                value="\n".join(lines),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="usage")
    async def usage_dashboard_prefix(self, ctx: commands.Context):
        if not ctx.guild:
            await ctx.send(t("common.server_only", "en"))
            return
        locale = get_locale_from_guild(ctx.guild)
        global_stats = await get_stats()
        guild_stats = await get_guild_stats(ctx.guild.id)
        top_guilds = await get_top_guilds_by_stat("messages_processed", limit=5)

        embed = discord.Embed(
            title=t("usage.dashboard.title", locale),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name=t("usage.dashboard.global", locale),
            value=(
                f"{t('usage.dashboard.messages', locale)}: {global_stats.get('messages_processed', 0):,}\n"
                f"{t('usage.dashboard.commands', locale)}: {global_stats.get('commands_executed', 0):,}\n"
                f"{t('usage.dashboard.images', locale)}: {global_stats.get('images_analyzed', 0):,}"
            ),
            inline=False,
        )
        embed.add_field(
            name=t("usage.dashboard.guild", locale),
            value=(
                f"{t('usage.dashboard.messages', locale)}: {guild_stats.get('messages_processed', 0):,}\n"
                f"{t('usage.dashboard.commands', locale)}: {guild_stats.get('commands_executed', 0):,}\n"
                f"{t('usage.dashboard.images', locale)}: {guild_stats.get('images_analyzed', 0):,}"
            ),
            inline=False,
        )
        if top_guilds:
            lines = []
            for row in top_guilds:
                guild = self.bot.get_guild(int(row.get("guild_id")))
                name = guild.name if guild else f"Guild {row.get('guild_id')}"
                lines.append(f"- {name}: {row.get('messages_processed', 0):,}")
            embed.add_field(name=t("usage.dashboard.top_guilds", locale), value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Usage(bot))
