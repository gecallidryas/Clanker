from __future__ import annotations

from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands

from utils.db_handler import get_mod_log_channel_id
from utils.logger import get_logger

logger = get_logger(__name__)


class ModLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(
        self,
        guild: discord.Guild,
        embed: discord.Embed,
        *,
        content: Optional[str] = None,
        files: Optional[list[discord.File]] = None,
    ) -> None:
        channel_id = await get_mod_log_channel_id(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            await channel.send(
                content=content,
                embed=embed,
                files=files or [],
                allowed_mentions=discord.AllowedMentions.none(),
            )
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

    def _truncate(self, text: str, limit: int = 1024) -> str:
        text = text or ""
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _build_message_delete_embed(self, message: discord.Message) -> discord.Embed:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Author",
            value=f"{message.author} ({message.author.id})" if message.author else "Unknown",
            inline=False,
        )
        embed.add_field(
            name="Channel",
            value=getattr(message.channel, "mention", f"ID {message.channel.id}"),
            inline=True,
        )
        embed.add_field(name="Message ID", value=str(message.id), inline=True)
        if message.created_at:
            embed.add_field(
                name="Created",
                value=discord.utils.format_dt(message.created_at, "R"),
                inline=True,
            )

        content = self._truncate(message.content or "(no text content)")
        embed.add_field(name="Content", value=content or "(empty)", inline=False)

        if message.attachments:
            attachment_lines = []
            for attachment in message.attachments[:5]:
                url = attachment.proxy_url or attachment.url or "no url"
                attachment_lines.append(f"{attachment.filename} ({attachment.size} bytes) - {url}")
            embed.add_field(
                name="Attachments",
                value="\n".join(attachment_lines),
                inline=False,
            )
        return embed

    async def _collect_deleted_message_files(self, message: discord.Message) -> list[discord.File]:
        files: list[discord.File] = []
        for attachment in message.attachments[:3]:
            try:
                files.append(await attachment.to_file(use_cached=True))
            except Exception:
                continue
        return files

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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="✅ Member Joined",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(
            name="Account Created",
            value=discord.utils.format_dt(member.created_at, "R"),
            inline=True,
        )
        await self._send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            title="📤 Member Left",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Member", value=f"{member} (`{member.id}`)", inline=False)
        if member.joined_at:
            embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "R"), inline=True)
        await self._send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        if not message.author:
            return
        embed = self._build_message_delete_embed(message)
        files = await self._collect_deleted_message_files(message)
        await self._send_log(message.guild, embed, files=files)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        if payload.cached_message is not None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        embed = discord.Embed(
            title="🗑️ Message Deleted (uncached)",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Channel", value=channel.mention if channel else f"ID {payload.channel_id}", inline=False)
        embed.add_field(name="Message ID", value=str(payload.message_id), inline=False)
        embed.set_footer(text="Content unavailable (message not cached).")
        await self._send_log(guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModLogger(bot))
