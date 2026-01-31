from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    add_starboard_ignored_channel,
    clear_starboard_entry,
    get_starboard_entry,
    get_starboard_ignored_channels,
    get_starboard_settings,
    mark_starboard_entry_deleted,
    remove_starboard_ignored_channel,
    set_starboard_enabled,
    upsert_starboard_entry,
    upsert_starboard_settings,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class Starboard(commands.Cog):
    starboard_group = app_commands.Group(name="starboard", description="Starboard settings")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _parse_trigger(self, trigger: str) -> Optional[discord.PartialEmoji]:
        if not trigger:
            return None
        try:
            return discord.PartialEmoji.from_str(trigger)
        except Exception:
            return None

    def _emoji_matches(self, trigger: str, emoji: discord.PartialEmoji) -> bool:
        if not trigger or trigger.strip().upper() == "ANY":
            return True
        parsed = self._parse_trigger(trigger)
        if parsed and parsed.id:
            return emoji.id == parsed.id
        if parsed and parsed.name:
            return (emoji.name or "") == parsed.name
        return str(emoji) == trigger

    def _stringify_emoji(self, emoji: discord.PartialEmoji) -> str:
        if emoji.is_custom():
            return str(emoji)
        return emoji.name or str(emoji)

    async def _fetch_channel(self, channel_id: int) -> Optional[discord.abc.GuildChannel]:
        channel = self.bot.get_channel(channel_id)
        if channel:
            return channel
        try:
            return await self.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def _fetch_message(
        self,
        channel: discord.abc.GuildChannel,
        message_id: int
    ) -> Optional[discord.Message]:
        try:
            return await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    def _get_reaction_count(
        self,
        message: discord.Message,
        emoji_to_track: discord.PartialEmoji
    ) -> Optional[discord.Reaction]:
        for reaction in message.reactions:
            if isinstance(reaction.emoji, str):
                if emoji_to_track.id is None and reaction.emoji == (emoji_to_track.name or ""):
                    return reaction
            elif isinstance(reaction.emoji, discord.Emoji):
                if emoji_to_track.id and reaction.emoji.id == emoji_to_track.id:
                    return reaction
        return None

    async def _effective_count(
        self,
        message: discord.Message,
        reaction: Optional[discord.Reaction],
        allow_self_star: bool,
    ) -> int:
        if not reaction:
            return 0
        count = reaction.count or 0
        if allow_self_star:
            return max(0, count)

        try:
            users = [user async for user in reaction.users()]
        except (discord.Forbidden, discord.HTTPException):
            return max(0, count)

        if message.author and any(user.id == message.author.id for user in users):
            return max(0, count - 1)
        return max(0, count)

    def _truncate(self, text: str, limit: int = 4096) -> str:
        if text is None:
            return ""
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _build_header(
        self,
        emoji_display: str,
        count: int,
        channel: discord.abc.GuildChannel,
        author: discord.abc.User,
    ) -> str:
        return f"{emoji_display} **{count}** | {channel.mention} | {author.mention}"

    def _build_embed(self, message: discord.Message) -> tuple[discord.Embed, Optional[str]]:
        embed = discord.Embed(
            color=discord.Color.from_rgb(255, 172, 51),
            timestamp=message.created_at,
        )
        author = message.author
        if author:
            avatar_url = author.display_avatar.url if author.display_avatar else None
            embed.set_author(name=author.display_name, icon_url=avatar_url)

        content = self._truncate(message.content or "")
        if content:
            embed.description = content

        embed.add_field(name="Source", value=f"[Jump to message]({message.jump_url})", inline=False)

        video_url: Optional[str] = None
        for attachment in message.attachments:
            content_type = attachment.content_type or ""
            if content_type.startswith("image/"):
                embed.set_image(url=attachment.url)
                break
            if content_type.startswith("video/"):
                video_url = attachment.url
                break

        return embed, video_url

    async def _update_starboard_message(
        self,
        starboard_message: discord.Message,
        header: str,
    ) -> None:
        existing = starboard_message.content or ""
        lines = existing.split("\n")
        tail = "\n".join(lines[1:]) if len(lines) > 1 else ""
        new_content = header + (f"\n{tail}" if tail else "")
        if new_content != existing:
            await starboard_message.edit(content=new_content)

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return

        settings = await get_starboard_settings(payload.guild_id)
        if not settings:
            return
        if not settings.get("enabled"):
            return
        starboard_channel_id = settings.get("channel_id")
        if not starboard_channel_id:
            return

        if payload.channel_id == starboard_channel_id:
            return

        ignored_channels = await get_starboard_ignored_channels(payload.guild_id)
        if payload.channel_id in ignored_channels:
            return

        trigger = settings.get("emoji_trigger") or "⭐"
        payload_emoji = payload.emoji
        if trigger.strip().upper() != "ANY" and not self._emoji_matches(trigger, payload_emoji):
            return

        entry = await get_starboard_entry(payload.guild_id, payload.message_id)
        if entry and entry.get("is_deleted"):
            return

        if entry and entry.get("emoji_used") and trigger.strip().upper() == "ANY":
            if entry.get("emoji_used") != self._stringify_emoji(payload_emoji):
                return

        channel = await self._fetch_channel(payload.channel_id)
        if not channel:
            return

        message = await self._fetch_message(channel, payload.message_id)
        if not message:
            return
        if message.author and message.author.bot:
            return

        if trigger.strip().upper() == "ANY":
            emoji_to_track = payload_emoji
            emoji_display = self._stringify_emoji(payload_emoji)
        else:
            parsed = self._parse_trigger(trigger)
            emoji_to_track = parsed or payload_emoji
            emoji_display = trigger

        reaction = self._get_reaction_count(message, emoji_to_track)
        effective_count = await self._effective_count(
            message,
            reaction,
            bool(settings.get("allow_self_star")),
        )

        threshold = max(1, int(settings.get("threshold") or 1))
        starboard_channel = await self._fetch_channel(starboard_channel_id)
        if not starboard_channel:
            return

        if entry:
            try:
                sb_message = await starboard_channel.fetch_message(entry["starboard_message_id"])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await clear_starboard_entry(payload.guild_id, payload.message_id)
                if effective_count < threshold:
                    return
                sb_message = None

            if sb_message:
                header = self._build_header(emoji_display, effective_count, channel, message.author)
                await self._update_starboard_message(sb_message, header)
            elif effective_count >= threshold:
                embed, video_url = self._build_embed(message)
                header = self._build_header(emoji_display, effective_count, channel, message.author)
                content = header + (f"\n{video_url}" if video_url else "")
                sent = await starboard_channel.send(
                    content,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                await upsert_starboard_entry(
                    payload.guild_id,
                    payload.message_id,
                    sent.id,
                    payload.channel_id,
                    emoji_used=emoji_display,
                )
            return

        if effective_count < threshold:
            return

        embed, video_url = self._build_embed(message)
        header = self._build_header(emoji_display, effective_count, channel, message.author)
        content = header + (f"\n{video_url}" if video_url else "")
        sent = await starboard_channel.send(
            content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await upsert_starboard_entry(
            payload.guild_id,
            payload.message_id,
            sent.id,
            payload.channel_id,
            emoji_used=emoji_display,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        entry = await get_starboard_entry(payload.guild_id, payload.message_id)
        if not entry or entry.get("is_deleted"):
            return

        settings = await get_starboard_settings(payload.guild_id)
        if not settings:
            return
        starboard_channel_id = settings.get("channel_id")
        if not starboard_channel_id:
            return

        starboard_channel = await self._fetch_channel(starboard_channel_id)
        if not starboard_channel:
            return

        try:
            sb_message = await starboard_channel.fetch_message(entry["starboard_message_id"])
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            await mark_starboard_entry_deleted(payload.guild_id, payload.message_id)
            return

        embed = sb_message.embeds[0] if sb_message.embeds else None
        if embed:
            new_embed = embed.copy()
            footer_text = new_embed.footer.text or ""
            suffix = "Original message deleted."
            if suffix not in footer_text:
                new_footer = f"{footer_text} • {suffix}".strip(" •")
                new_embed.set_footer(text=new_footer)
            await sb_message.edit(embed=new_embed)

        await mark_starboard_entry_deleted(payload.guild_id, payload.message_id)

    # =========================
    # Commands
    # =========================

    @starboard_group.command(name="setup", description="Configure starboard for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="Starboard destination channel",
        threshold="Minimum reactions to post",
        emoji="Emoji to track (default ⭐)",
        allow_self_star="Allow the author to star their own message",
    )
    async def starboard_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        threshold: int = 3,
        emoji: str = "⭐",
        allow_self_star: Optional[bool] = False,
    ):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        await upsert_starboard_settings(
            interaction.guild.id,
            channel.id,
            emoji,
            threshold,
            bool(allow_self_star),
            enabled=True,
        )
        await interaction.response.send_message(
            f"Starboard set to {channel.mention} with threshold {max(1, threshold)}.",
            ephemeral=True,
        )

    @starboard_group.command(name="toggle", description="Enable or disable starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(state="on/off (leave empty to view)")
    async def starboard_toggle(self, interaction: discord.Interaction, state: Optional[str] = None):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        if not state:
            settings = await get_starboard_settings(interaction.guild.id)
            enabled = bool(settings.get("enabled")) if settings else False
            await interaction.response.send_message(
                f"Starboard is currently **{'ENABLED' if enabled else 'DISABLED'}**.",
                ephemeral=True,
            )
            return
        state_value = state.lower().strip()
        if state_value in {"on", "enable", "true", "yes"}:
            await set_starboard_enabled(interaction.guild.id, True)
            await interaction.response.send_message("Starboard enabled.", ephemeral=True)
        elif state_value in {"off", "disable", "false", "no"}:
            await set_starboard_enabled(interaction.guild.id, False)
            await interaction.response.send_message("Starboard disabled.", ephemeral=True)
        else:
            await interaction.response.send_message("Usage: `/starboard toggle on|off`", ephemeral=True)

    @starboard_group.command(name="ignore", description="Ignore a channel for starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def starboard_ignore(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        await add_starboard_ignored_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            f"Starboard will ignore {channel.mention}.",
            ephemeral=True,
        )

    @starboard_group.command(name="unignore", description="Remove a channel from the ignore list.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def starboard_unignore(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        removed = await remove_starboard_ignored_channel(interaction.guild.id, channel.id)
        if removed:
            await interaction.response.send_message(
                f"Starboard will watch {channel.mention} again.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{channel.mention} was not ignored.",
                ephemeral=True,
            )

    @starboard_group.command(name="ignored", description="List ignored channels.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def starboard_ignored(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return
        ignored = await get_starboard_ignored_channels(interaction.guild.id)
        if not ignored:
            await interaction.response.send_message("No ignored channels.", ephemeral=True)
            return
        mentions = []
        for channel_id in ignored:
            channel = interaction.guild.get_channel(channel_id)
            mentions.append(channel.mention if channel else f"(deleted channel {channel_id})")
        await interaction.response.send_message("\n".join(mentions), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))
