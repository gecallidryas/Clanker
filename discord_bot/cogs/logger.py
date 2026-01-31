from __future__ import annotations

from datetime import timedelta

import discord
from discord.ext import commands

from utils.db_handler import get_mod_log_channel_id
from utils.logger import get_logger

logger = get_logger(__name__)


class ModLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel_id = await get_mod_log_channel_id(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            logger.warning("Missing permissions to send mod log in %s", guild.name)
        except Exception as exc:
            logger.warning("Failed to send mod log in %s: %s", guild.name, exc)

    async def _resolve_timeout_actor(self, member: discord.Member) -> tuple[str, str]:
        try:
            async for entry in member.guild.audit_logs(
                limit=5,
                action=discord.AuditLogAction.member_update,
            ):
                if entry.target.id != member.id:
                    continue
                if entry.created_at and (discord.utils.utcnow() - entry.created_at) > timedelta(minutes=5):
                    continue
                moderator = entry.user.mention if entry.user else "Unknown"
                reason = entry.reason or "No reason provided"
                return moderator, reason
        except Exception:
            pass
        return "Unknown", "No reason provided"

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.timed_out_until == after.timed_out_until:
            return

        if after.timed_out_until is not None:
            diff = after.timed_out_until - discord.utils.utcnow()
            minutes = max(1, round(diff.total_seconds() / 60))
            moderator, reason = await self._resolve_timeout_actor(after)
            embed = discord.Embed(
                title="🚫 Member Timed Out",
                color=discord.Color.orange(),
            )
            embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)", inline=False)
            embed.add_field(name="Duration", value=f"~{minutes} minutes", inline=True)
            embed.add_field(
                name="Expires",
                value=discord.utils.format_dt(after.timed_out_until, "R"),
                inline=True,
            )
            embed.add_field(name="Moderator", value=moderator, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            await self._send_log(after.guild, embed)
        else:
            embed = discord.Embed(
                title="🔊 Timeout Removed",
                description=f"**User:** {after.mention} is free to speak again.",
                color=discord.Color.green(),
            )
            await self._send_log(after.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModLogger(bot))
