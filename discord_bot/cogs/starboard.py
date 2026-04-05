from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.admin_actions import execute_admin_action
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
)
from utils.logger import get_logger

logger = get_logger(__name__)


class Starboard(commands.Cog):
    starboard_group = app_commands.Group(name="starboard", description="Starboard settings")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message_locks: dict[tuple[int, int], asyncio.Lock] = defaultdict(asyncio.Lock)

    def _get_lock(self, guild_id: int, message_id: int) -> asyncio.Lock:
        return self._message_locks[(guild_id, message_id)]

    def _parse_trigger(self, trigger: str) -> Optional[discord.PartialEmoji]:
        if not trigger:
            return None
        try:
            return discord.PartialEmoji.from_str(trigger)
        except Exception:
            return None

    def _split_emoji_input(self, raw: str) -> List[str]:
        text = (raw or "").strip()
        if not text:
            return []

        tokens: List[str] = []
        custom_tokens = re.findall(r"<a?:\w+:\d+>|:\w+:", text)
        if custom_tokens:
            tokens.extend(custom_tokens)
            text = re.sub(r"<a?:\w+:\d+>|:\w+:", " ", text)

        parts = [part for part in re.split(r"[\s,]+", text.strip()) if part]
        tokens.extend(parts)
        return [token for token in tokens if token]

    def _get_trigger_config(self, settings: dict) -> tuple[str, List[str]]:
        emoji_mode = (settings.get("emoji_mode") or "").strip().lower()
        triggers = settings.get("emoji_triggers") or []
        legacy_trigger = (settings.get("emoji_trigger") or "").strip()

        if not emoji_mode:
            emoji_mode = "any" if legacy_trigger.upper() == "ANY" else "list"
        if emoji_mode != "any" and not triggers and legacy_trigger:
            triggers = [legacy_trigger]
        return emoji_mode, triggers

    def _stringify_emoji_obj(self, emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
        if isinstance(emoji, str):
            return emoji
        if isinstance(emoji, discord.PartialEmoji):
            if emoji.is_custom():
                return str(emoji)
            return emoji.name or str(emoji)
        return str(emoji)

    def _normalize_emoji_token(self, token: str) -> str:
        # Normalize unicode presentation selectors so "⭐" and "⭐️" compare equal.
        return (token or "").replace("\ufe0f", "").strip()

    def _reaction_matches_trigger(
        self,
        reaction_emoji: discord.PartialEmoji | discord.Emoji | str,
        trigger: str,
    ) -> bool:
        if not trigger or trigger.strip().upper() == "ANY":
            return True
        custom_match = re.fullmatch(r"<a?:(?P<name>\w+):(?P<id>\d+)>", trigger.strip())
        if custom_match:
            reaction_id = getattr(reaction_emoji, "id", None)
            try:
                return int(reaction_id) == int(custom_match.group("id"))
            except (TypeError, ValueError):
                return False
        parsed = self._parse_trigger(trigger)
        reaction_str = self._stringify_emoji_obj(reaction_emoji)
        normalized_trigger = self._normalize_emoji_token(trigger)
        normalized_reaction_str = self._normalize_emoji_token(reaction_str)

        if parsed and parsed.id:
            reaction_id = getattr(reaction_emoji, "id", None)
            return reaction_id == parsed.id
        if parsed and parsed.name:
            reaction_name = getattr(reaction_emoji, "name", None)
            return self._normalize_emoji_token(reaction_name or reaction_str) == self._normalize_emoji_token(
                parsed.name
            )
        return normalized_reaction_str == normalized_trigger

    async def _effective_count(
        self,
        message: discord.Message,
        reaction: discord.Reaction,
        allow_self_star: bool,
    ) -> int:
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

    async def _fetch_channel(
        self,
        channel_id: int,
    ) -> Optional[discord.abc.GuildChannel]:
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
        message_id: int,
    ) -> Optional[discord.Message]:
        if not hasattr(channel, "fetch_message"):
            return None
        try:
            return await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def _resolve_best_reaction(
        self,
        message: discord.Message,
        emoji_mode: str,
        triggers: List[str],
        allow_self_star: bool,
        payload_emoji: Optional[discord.PartialEmoji],
    ) -> tuple[Optional[str], int]:
        best_emoji: Optional[str] = None
        best_count = 0

        for reaction in message.reactions:
            reaction_emoji = reaction.emoji
            reaction_display = self._stringify_emoji_obj(reaction_emoji)

            if payload_emoji and emoji_mode == "any":
                payload_display = self._stringify_emoji_obj(payload_emoji)
                if reaction_display != payload_display:
                    # Keep scanning for best count, but prefer payload tie-break later.
                    pass

            if emoji_mode != "any":
                if not any(self._reaction_matches_trigger(reaction_emoji, trigger) for trigger in triggers):
                    continue

            count = await self._effective_count(message, reaction, allow_self_star)
            if count > best_count:
                best_count = count
                best_emoji = reaction_display

        if best_emoji is None and payload_emoji is not None and emoji_mode == "any":
            best_emoji = self._stringify_emoji_obj(payload_emoji)
        if best_emoji is None and emoji_mode != "any" and triggers:
            best_emoji = triggers[0]
        return best_emoji, best_count

    async def _create_or_update_starboard_message(
        self,
        starboard_channel: discord.abc.GuildChannel,
        source_channel: discord.abc.GuildChannel,
        source_message: discord.Message,
        entry: Optional[dict],
        emoji_display: str,
        count: int,
    ) -> Optional[int]:
        embed, video_url = self._build_embed(source_message)
        content = self._build_header(emoji_display, count, source_channel, source_message.author)
        if video_url:
            content = f"{content}\n{video_url}"

        if entry:
            try:
                existing = await starboard_channel.fetch_message(entry["starboard_message_id"])
                await existing.edit(content=content, embed=embed)
                return existing.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await clear_starboard_entry(source_message.guild.id, source_message.id)

        sent = await starboard_channel.send(
            content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return sent.id

    async def _reconcile_message(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        payload_emoji: Optional[discord.PartialEmoji] = None,
    ) -> None:
        lock = self._get_lock(guild_id, message_id)
        async with lock:
            settings = await get_starboard_settings(guild_id)
            if not settings or not settings.get("enabled"):
                return

            starboard_channel_id = settings.get("channel_id")
            if not starboard_channel_id:
                return
            if channel_id == starboard_channel_id:
                return

            ignored_channels = await get_starboard_ignored_channels(guild_id)
            if channel_id in ignored_channels:
                return

            source_channel = await self._fetch_channel(channel_id)
            if not source_channel:
                return
            source_message = await self._fetch_message(source_channel, message_id)
            if not source_message:
                return
            if source_message.author and source_message.author.bot:
                return

            entry = await get_starboard_entry(guild_id, message_id)
            if entry and entry.get("is_deleted"):
                return

            emoji_mode, triggers = self._get_trigger_config(settings)
            emoji_display, effective_count = await self._resolve_best_reaction(
                source_message,
                emoji_mode,
                triggers,
                bool(settings.get("allow_self_star")),
                payload_emoji,
            )
            threshold = max(1, int(settings.get("threshold") or 1))

            starboard_channel = await self._fetch_channel(starboard_channel_id)
            if not isinstance(starboard_channel, discord.TextChannel):
                return

            if effective_count < threshold:
                if entry:
                    try:
                        existing = await starboard_channel.fetch_message(entry["starboard_message_id"])
                        await existing.delete()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass
                    await clear_starboard_entry(guild_id, message_id)
                return

            if not emoji_display:
                emoji_display = entry.get("emoji_used") if entry else "⭐"

            starboard_message_id = await self._create_or_update_starboard_message(
                starboard_channel,
                source_channel,
                source_message,
                entry,
                emoji_display,
                effective_count,
            )
            if starboard_message_id is None:
                return

            await upsert_starboard_entry(
                guild_id,
                message_id,
                starboard_message_id,
                channel_id,
                emoji_used=emoji_display,
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        await self._reconcile_message(
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            payload_emoji=payload.emoji,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        await self._reconcile_message(
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            payload_emoji=payload.emoji,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        if payload.guild_id is None:
            return
        await self._reconcile_message(payload.guild_id, payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent):
        if payload.guild_id is None:
            return
        await self._reconcile_message(
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            payload_emoji=payload.emoji,
        )

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
        if not isinstance(starboard_channel, discord.TextChannel):
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
        emoji="Emoji(s) to track (single, multiple, or 'any')",
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

        emoji_input = (emoji or "").strip()
        emoji_mode = "any" if emoji_input.lower() in {"any", "all", "*"} else "list"
        params = {
            "channel_id": channel.id,
            "threshold": max(1, int(threshold)),
            "emoji_mode": emoji_mode,
            "allow_self_star": bool(allow_self_star),
        }
        if emoji_mode != "any":
            params["emoji_triggers"] = self._split_emoji_input(emoji_input)

        result = await execute_admin_action(
            "STARBOARD_SETUP",
            params,
            interaction.guild,
            interaction.user,
            current_channel_id=interaction.channel_id,
        )
        if not result.get("success"):
            await interaction.response.send_message(
                result.get("error", "Starboard setup failed."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(result.get("message", "Starboard configured."), ephemeral=True)

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
